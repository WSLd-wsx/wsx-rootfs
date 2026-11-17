/* SPDX-License-Identifier: MIT */
#pragma once
struct gbm_bo;
namespace KWin {
/* Process-local output allocation ownership, never wire metadata. */
class WsxNativeBuffer {
public:
    virtual ~WsxNativeBuffer() = default;
    virtual gbm_bo *wsxNativeBo() const = 0;
};
}
