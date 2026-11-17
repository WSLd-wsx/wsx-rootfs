/* SPDX-License-Identifier: MIT */
#ifndef WSX_GBM_DESCRIPTOR_H
#define WSX_GBM_DESCRIPTOR_H
#include <stdint.h>
#include <drm.h>
#include "wsx-opaque-uapi.h"
#ifdef __cplusplus
extern "C" {
#endif
int wsx_gbm_opaque_consumer_supported(int drm_fd);
int wsx_gbm_lookup_opaque_fd(int drm_fd, int prime_fd, uint32_t width,
                            uint32_t height, uint32_t vk_format,
                            struct drm_wsx_opaque_query *out);
/* Read-only paired kernel/Host capability: returns 1, 0 or -errno. */
int wsx_gbm_opaque_supported(int drm_fd);
/* Does not consume either fd; fd zero is valid. Returns zero or -errno.
 * The caller must already have negotiated opaque storage. No pitch or DRM
 * modifier is invented, and no Vulkan handle type is changed here. */
int wsx_gbm_register_opaque_fd(int drm_fd, int prime_fd, uint32_t width,
                              uint32_t height, uint32_t vk_format,
                              struct drm_wsx_opaque_query *out);
#ifdef __cplusplus
}
#endif
#endif
