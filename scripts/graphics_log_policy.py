# SPDX-License-Identifier: GPL-2.0-or-later
"""Gate high-volume WSX graphics traces in disposable patched source trees."""
from pathlib import Path
import re

TRACE = 'WSX_GRAPHICS_TRACE'
TARGETS = {
    'mesa': {
        'src/gallium/drivers/zink/zink_screen.c': ('LINEAR_FEEDBACK', 'LINEAR_GATE', 'LINEAR_QUERY'),
        'src/gallium/drivers/zink/zink_kopper.c': ('KOPPER_LAYOUT',),
        'src/gallium/drivers/zink/zink_context.c': ('LINEAR_RENDERING', 'LINEAR_ATTACHMENT'),
        'src/gallium/drivers/zink/zink_resource.c': ('REBIND_LINEAR', 'SHARED_FD', 'OPAQUE_IMPORT', 'OPAQUE_EXPORT_QUERY', 'OPAQUE_GBM_FD'),
    },
    'venus': {
        'src/virtio/vulkan/vn_wsi.c': ('DIRECT_WSI', 'WSI_LAYOUT'),
        'src/virtio/vulkan/vn_physical_device.c': ('WSI_QUERY', 'NV_LINEAR_GUEST', 'OPAQUE_HOST_QUERY'),
        'src/virtio/vulkan/vn_device_memory.c': ('OPAQUE_IMPORT_SIZE', 'OPAQUE_EXPORT_ORDER'),
        'src/virtio/vulkan/vn_image.c': ('OPAQUE_BIND_ORDER',),
        'src/vulkan/wsi/wsi_common_wayland.c': ('OPAQUE_WSI: epoch=',),
    },
}
PREFIX = ('#include <stdlib.h>\n#include <string.h>\n'
          '#define WSX_TRACE_LOG(fn, ...) do { const char *wsx_trace = getenv("WSX_GRAPHICS_TRACE"); '
          'if (wsx_trace && strcmp(wsx_trace, "1") == 0) fn(__VA_ARGS__); } while (0)\n')


def apply(source, profile):
    """Only wrap exact known success-path diagnostics; reject changed inputs."""
    changed = []
    for relative, markers in TARGETS[profile].items():
        path = Path(source) / relative
        text = path.read_text()
        if 'WSX_TRACE_LOG' in text:
            raise ValueError('Graphics log policy already applied: ' + relative)
        for marker in markers:
            # Match the logging call only, preserving any surrounding conditional.
            expression = re.compile(r'\b(mesa_logi|vn_log|fprintf)\((?:(?!;).)*?"WSX_'
                                    + re.escape(marker), re.S)
            matches = list(expression.finditer(text))
            if len(matches) != 1:
                raise ValueError('Unexpected graphics trace site: ' + relative + ': ' + marker)
            match = matches[0]
            name = match.group(1)
            text = text[:match.start()] + 'WSX_TRACE_LOG(' + name + ', ' + text[match.start() + len(name) + 1:]
        path.write_text(PREFIX + text)
        changed.append(relative)
    return changed
