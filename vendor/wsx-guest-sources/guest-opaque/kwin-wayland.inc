/* SPDX-License-Identifier: MIT
 * Included inside KWin's client-buffer implementation namespace. */
class WsxOpaqueManager : public QObject
{
public:
    explicit WsxOpaqueManager(LinuxDmaBufV1ClientBufferIntegration *integration, Display *display)
        : QObject(integration), m_integration(integration)
    {
        m_displayDestroy.owner = this;
        m_displayDestroy.listener.notify = [](wl_listener *listener, void *) {
            auto hook = reinterpret_cast<DisplayDestroyHook *>(listener);
            // wl_display_destroy owns global destruction before QObject children
            // are deleted. Invalidate our pointer and detach the listener first.
            hook->owner->m_global = nullptr;
            wl_list_remove(&listener->link);
            wl_list_init(&listener->link);
        };
        wl_display_add_destroy_listener(*display, &m_displayDestroy.listener);
        m_global = wl_global_create(*display, &wsx_opaque_buffer_manager_v1_interface,
                                    1, this, bind);
        qInfo() << "WSX_OPAQUE_WAYLAND global=" << bool(m_global);
    }
    ~WsxOpaqueManager() override
    {
        wl_list_remove(&m_displayDestroy.listener.link);
        if (m_global) wl_global_destroy(m_global);
    }
private:
    static void destroy(wl_client *, wl_resource *resource) { wl_resource_destroy(resource); }
    static void create(wl_client *client, wl_resource *resource, uint32_t id,
                       int32_t fd, uint32_t width, uint32_t height, uint32_t fourcc)
    {
        FileDescriptor ownedFd(fd);
        auto self = *static_cast<QPointer<WsxOpaqueManager> *>(wl_resource_get_user_data(resource));
        auto reject = [&]() {
            wl_resource_post_error(resource, 0, "WSX opaque descriptor/import rejected");
        };
        if (!self || !self->m_integration->renderBackend() || !width || !height
            || width > INT32_MAX || height > INT32_MAX || !ownedFd.isValid()) {
            reject(); return;
        }
        const uint32_t format = fourcc == DRM_FORMAT_ARGB8888 || fourcc == DRM_FORMAT_XRGB8888 ? 44
            : fourcc == DRM_FORMAT_ABGR8888 || fourcc == DRM_FORMAT_XBGR8888 ? 37 : 0;
        if (!format) { reject(); return; }
        for (const auto &device : GpuManager::s_self->renderDevices()) {
            auto drm = device->drmDevice();
            auto egl = device->eglDisplay();
            drm_wsx_opaque_query descriptor{};
            if (!drm || !egl || !egl->extensions().contains(QByteArrayLiteral("EGL_WSX_opaque_image"))
                || wsx_gbm_opaque_consumer_supported(drm->fileDescriptor()) != 1
                || wsx_gbm_lookup_opaque_fd(drm->fileDescriptor(), fd, width, height, format, &descriptor))
                continue;
            DmaBufAttributes attrs;
            attrs.planeCount = 1; attrs.width = width; attrs.height = height;
            attrs.format = fourcc; attrs.modifier = DRM_FORMAT_MOD_INVALID;
            attrs.device = drm->deviceId(); attrs.pitch[0] = 0; attrs.offset[0] = 0;
            attrs.fd[0] = std::move(ownedFd);
            auto buffer = new LinuxDmaBufV1ClientBuffer(std::move(attrs));
            if (!self->m_integration->renderBackend()->testImportBuffer(buffer, drm->deviceId())) {
                buffer->drop(); reject(); return;
            }
            buffer->setDevice(drm->deviceId());
            auto bufferResource = wl_resource_create(client, &wl_buffer_interface, 1, id);
            if (!bufferResource) {
                buffer->drop(); wl_resource_post_no_memory(resource); return;
            }
            buffer->initialize(bufferResource);
            qInfo() << "WSX_OPAQUE_WAYLAND imported" << width << height
                    << "epoch" << descriptor.contract.context_epoch
                    << "generation" << descriptor.contract.image_generation;
            return;
        }
        reject();
    }
    static void bind(wl_client *client, void *data, uint32_t, uint32_t id)
    {
        auto resource = wl_resource_create(client, &wsx_opaque_buffer_manager_v1_interface, 1, id);
        if (!resource) { wl_client_post_no_memory(client); return; }
        static const struct wsx_opaque_buffer_manager_v1_interface implementation = {destroy, create};
        auto pointer = new QPointer<WsxOpaqueManager>(static_cast<WsxOpaqueManager *>(data));
        wl_resource_set_implementation(resource, &implementation, pointer, [](wl_resource *resource) {
            delete static_cast<QPointer<WsxOpaqueManager> *>(wl_resource_get_user_data(resource));
        });
    }
    struct DisplayDestroyHook {
        wl_listener listener{};
        WsxOpaqueManager *owner = nullptr;
    } m_displayDestroy;
    LinuxDmaBufV1ClientBufferIntegration *m_integration;
    wl_global *m_global = nullptr;
};
