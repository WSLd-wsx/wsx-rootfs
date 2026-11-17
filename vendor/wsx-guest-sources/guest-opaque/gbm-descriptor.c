/* SPDX-License-Identifier: MIT */
/* Call only for an explicitly negotiated opaque allocation. This does not
 * turn ordinary dma-bufs or implicit DRM modifiers into opaque images. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysmacros.h>
#include <xf86drm.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <drm.h>
#include <virtgpu_drm.h>
#include "gbm-descriptor.h"

int wsx_gbm_opaque_supported(int drm_fd)
{
    int supported = 0;
    struct drm_virtgpu_getparam param = {
        .param = WSX_OPAQUE_GETPARAM, .value = (uintptr_t)&supported,
    };
    if (drm_fd < 0) return -EINVAL;
    if (ioctl(drm_fd, DRM_IOCTL_VIRTGPU_GETPARAM, &param)) return -errno;
    return supported == 1;
}

int wsx_gbm_opaque_consumer_supported(int drm_fd)
{
    int version = 0;
    struct drm_virtgpu_getparam param = {
        .param = WSX_OPAQUE_CONSUMER_GETPARAM, .value = (uintptr_t)&version,
    };
    if (drm_fd < 0) return -EINVAL;
    if (ioctl(drm_fd, DRM_IOCTL_VIRTGPU_GETPARAM, &param)) return -errno;
    return version == WSX_OPAQUE_CONSUMER_ABI;
}

static int wsx_gbm_fd_descriptor(int drm_fd, int prime_fd, uint32_t width,
                              uint32_t height, uint32_t vk_format,
                              struct drm_wsx_opaque_query *out, int lookup)
{
    struct stat original, fresh;
    struct drm_prime_handle prime = {.fd = prime_fd};
    struct drm_gem_close close_handle = {0};
    struct drm_wsx_opaque_query query = {
        .version = 1, .width = width, .height = height, .format = vk_format,
    };
    int supported = 0, result = 0;
    struct drm_virtgpu_getparam param = {
        .param = WSX_OPAQUE_GETPARAM, .value = (uintptr_t)&supported,
    };
    char path[64];
    if (drm_fd < 0 || prime_fd < 0 || !out || !width || !height ||
        (vk_format != 37 && vk_format != 44)) return -EINVAL;
    if (fstat(drm_fd, &original)) return -errno;
    if (!S_ISCHR(original.st_mode)) return -ENODEV;
    /* A new DRM file namespace owns the temporary GEM handle. Importing into
     * the caller's file and GEM_CLOSEing the returned handle could close an
     * existing caller-owned handle: PRIME import is idempotent per DRM file. */
    snprintf(path, sizeof(path), "/proc/self/fd/%d", drm_fd);
    int owned = open(path, O_RDWR | O_CLOEXEC);
    if (owned < 0 && errno == EACCES) {
        /* A seatd-provided primary fd can be used without permission to open
         * the primary node again. libdrm resolves its paired render node. */
        char *render = drmGetRenderDeviceNameFromFd(drm_fd);
        if (!render) return -EACCES;
        owned = open(render, O_RDWR | O_CLOEXEC);
        int error = errno;
        free(render);
        if (owned < 0) return -error;
    }
    if (owned < 0) return -errno;
    if (fstat(owned, &fresh)) { result = -errno; goto done; }
    if (!S_ISCHR(fresh.st_mode)) { result = -EXDEV; goto done; }
    if (fresh.st_rdev != original.st_rdev) {
        struct stat original_device, fresh_device;
        char original_path[96], fresh_path[96];
        snprintf(original_path, sizeof(original_path), "/sys/dev/char/%u:%u/device",
                 major(original.st_rdev), minor(original.st_rdev));
        snprintf(fresh_path, sizeof(fresh_path), "/sys/dev/char/%u:%u/device",
                 major(fresh.st_rdev), minor(fresh.st_rdev));
        if (stat(original_path, &original_device) || stat(fresh_path, &fresh_device) ||
            original_device.st_dev != fresh_device.st_dev ||
            original_device.st_ino != fresh_device.st_ino) {
            result = -EXDEV; goto done;
        }
    }
    if (ioctl(owned, DRM_IOCTL_VIRTGPU_GETPARAM, &param)) { result = -errno; goto done; }
    if (supported != 1) { result = -EOPNOTSUPP; goto done; }
    if (ioctl(owned, DRM_IOCTL_PRIME_FD_TO_HANDLE, &prime)) { result = -errno; goto done; }
    if (!prime.handle) { result = -EPROTO; goto done; }
    query.handle = prime.handle;
    if (ioctl(owned, lookup ? DRM_IOCTL_VIRTGPU_WSX_OPAQUE_LOOKUP : DRM_IOCTL_VIRTGPU_WSX_OPAQUE, &query)) result = -errno;
    else {
        /* The kernel validates and associates the immutable descriptor with
         * the original GEM object before returning. Do not expose our handle. */
        query.handle = 0;
        *out = query;
    }
    close_handle.handle = prime.handle;
    if (ioctl(owned, DRM_IOCTL_GEM_CLOSE, &close_handle) && !result) result = -errno;
done:
    close(owned);
    return result;
}

int wsx_gbm_register_opaque_fd(int drm_fd, int prime_fd, uint32_t width,
                              uint32_t height, uint32_t vk_format,
                              struct drm_wsx_opaque_query *out)
{
    return wsx_gbm_fd_descriptor(drm_fd, prime_fd, width, height, vk_format, out, 0);
}
int wsx_gbm_lookup_opaque_fd(int drm_fd, int prime_fd, uint32_t width,
                            uint32_t height, uint32_t vk_format,
                            struct drm_wsx_opaque_query *out)
{
    int supported = wsx_gbm_opaque_consumer_supported(drm_fd);
    if (supported != 1) return supported < 0 ? supported : -EOPNOTSUPP;
    return wsx_gbm_fd_descriptor(drm_fd, prime_fd, width, height, vk_format, out, 1);
}
