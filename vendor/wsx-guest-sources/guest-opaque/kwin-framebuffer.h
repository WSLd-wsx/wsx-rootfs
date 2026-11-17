/* SPDX-License-Identifier: MIT */
#ifndef WSX_KWIN_FRAMEBUFFER_H
#define WSX_KWIN_FRAMEBUFFER_H
#include "gbm-descriptor.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Uses a GEM handle already owned by the KMS DRM file. Does not consume it.
 * Output is published only after descriptor validation and framebuffer creation.
 * The caller retains its normal framebuffer/fence retirement mechanism. */
int wsx_kwin_create_opaque_fb(int drm_fd, uint32_t handle, uint32_t width,
                            uint32_t height, uint32_t fourcc, uint32_t *fb_id);
#ifdef __cplusplus
}
#endif
#endif
