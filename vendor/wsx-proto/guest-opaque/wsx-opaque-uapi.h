/* SPDX-License-Identifier: MIT */
#ifndef WSX_OPAQUE_UAPI_H
#define WSX_OPAQUE_UAPI_H
#include <linux/types.h>
#ifdef __cplusplus
#define WSX_STATIC_ASSERT static_assert
#else
#define WSX_STATIC_ASSERT _Static_assert
#endif
/* Private paired WSX extension, not an upstream virtio/DRM assignment.
 * The explicit wire encoding is little endian; only the paired LE WSL driver
 * below copies these fixed-width layouts to/from the control queue. */
#define WSX_OPAQUE_FEATURE 15
#define WSX_OPAQUE_COMMAND 0x57535810u
#define WSX_OPAQUE_RESPONSE 0x57535811u
#define WSX_OPAQUE_MAGIC 0x4f585357u
#define WSX_OPAQUE_VERSION 1
#define WSX_OPAQUE_HELLO 1
#define WSX_OPAQUE_DESCRIBE 2
#define WSX_OPAQUE_SCANOUT 3
#define WSX_OPAQUE_GETPARAM 0x57535801u
struct wsx_image_contract {

   __u32 version, struct_size, resource_id, reserved;
   __aligned_u64 context_epoch, image_id, image_generation, memory_id;
   __aligned_u64 allocation_size, binding_offset, requirements_size, alignment;
   __u32 memory_type_index, memory_type_bits;
   __u32 format, width, height, depth, tiling, usage, image_flags;
   __u32 samples, mip_levels, array_layers, sharing_mode, handle_type, dedicated, view_count;
   __u32 view_formats[16];
   __u8 device_uuid[16], driver_uuid[16], device_luid[8];
   __u32 device_node_mask, external_features, requires_dedicated, prefers_dedicated;
};
struct wsx_opaque_request {
    __u32 magic, version, op, reserved;
    __u8 instance[16];
    __u32 resource, width, height, format;
    __aligned_u64 offset;
    __u32 crop[4];
    struct wsx_image_contract contract;
};
struct wsx_opaque_reply {
    __u32 magic, version, op;
    __s32 status;
    __u8 instance[16];
    __u32 capabilities, reserved;
    struct wsx_image_contract contract;
};
/* Native-endian ioctl; handle is owned in the calling DRM file namespace.
 * It is never a Win32 handle or a pointer and is not sent to the Host. */
struct drm_wsx_opaque_query {
    __u32 version, handle, width, height, format, reserved;
    __u8 instance[16];
    struct wsx_image_contract contract;
};
/* Local consumer ABI. These ioctls never reinterpret a standard modifier. */
#define WSX_OPAQUE_CONSUMER_GETPARAM 0x57535802u
#define WSX_OPAQUE_CONSUMER_ABI 2u
#define EGL_WSX_OPAQUE_DESCRIPTOR 0x57535820u
struct drm_wsx_opaque_fb {
    __u32 version, handle, format, fb_id;
    __aligned_u64 context_epoch, image_generation;
    __u8 instance[16];
};
#define DRM_VIRTGPU_WSX_OPAQUE_LOOKUP 0x0d
#define DRM_VIRTGPU_WSX_OPAQUE_FB 0x0e
#define DRM_IOCTL_VIRTGPU_WSX_OPAQUE_LOOKUP DRM_IOWR(DRM_COMMAND_BASE + DRM_VIRTGPU_WSX_OPAQUE_LOOKUP, struct drm_wsx_opaque_query)
#define DRM_IOCTL_VIRTGPU_WSX_OPAQUE_FB DRM_IOWR(DRM_COMMAND_BASE + DRM_VIRTGPU_WSX_OPAQUE_FB, struct drm_wsx_opaque_fb)
WSX_STATIC_ASSERT(sizeof(struct drm_wsx_opaque_fb)==48,"opaque framebuffer ABI");
#define DRM_VIRTGPU_WSX_OPAQUE 0x0c
#define DRM_IOCTL_VIRTGPU_WSX_OPAQUE DRM_IOWR(DRM_COMMAND_BASE + DRM_VIRTGPU_WSX_OPAQUE, struct drm_wsx_opaque_query)
WSX_STATIC_ASSERT(sizeof(struct wsx_image_contract)==264,"opaque contract ABI");
WSX_STATIC_ASSERT(sizeof(struct wsx_opaque_request)==336,"opaque request ABI");
WSX_STATIC_ASSERT(sizeof(struct wsx_opaque_reply)==304,"opaque reply ABI");
WSX_STATIC_ASSERT(sizeof(struct drm_wsx_opaque_query)==304,"opaque ioctl ABI");
#endif
