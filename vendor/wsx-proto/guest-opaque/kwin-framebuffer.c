/* SPDX-License-Identifier: MIT */
#include "kwin-framebuffer.h"
#include <drm_fourcc.h>
#include <errno.h>
#include <string.h>
#include <sys/ioctl.h>

int wsx_kwin_create_opaque_fb(int drm_fd, uint32_t handle, uint32_t width,
                            uint32_t height, uint32_t fourcc, uint32_t *fb_id)
{
    uint32_t format;
    if (!fb_id || !handle || !width || !height)
        return -EINVAL;
    switch (fourcc) {
    case DRM_FORMAT_ARGB8888:
    case DRM_FORMAT_XRGB8888: format = 44; break;
    case DRM_FORMAT_ABGR8888:
    case DRM_FORMAT_XBGR8888: format = 37; break;
    default: return -ENOTSUP;
    }
    if (wsx_gbm_opaque_consumer_supported(drm_fd) != 1)
        return -ENOTSUP;
    struct drm_wsx_opaque_query query = {
        .version = WSX_OPAQUE_VERSION, .handle = handle,
        .width = width, .height = height, .format = format,
    };
    if (ioctl(drm_fd, DRM_IOCTL_VIRTGPU_WSX_OPAQUE_LOOKUP, &query))
        return -errno;
    struct drm_wsx_opaque_fb request = {
        .version = WSX_OPAQUE_CONSUMER_ABI, .handle = handle,
        .format = fourcc, .context_epoch = query.contract.context_epoch,
        .image_generation = query.contract.image_generation,
    };
    memcpy(request.instance, query.instance, sizeof(request.instance));
    if (ioctl(drm_fd, DRM_IOCTL_VIRTGPU_WSX_OPAQUE_FB, &request))
        return -errno;
    if (!request.fb_id)
        return -EPROTO;
    *fb_id = request.fb_id;
    return 0;
}
