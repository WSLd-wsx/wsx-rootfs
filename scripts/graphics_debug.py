# SPDX-License-Identifier: GPL-2.0-or-later
"""Make verbose graphics diagnostics an explicit Guest-local opt-in."""

OLD = """               # Preserve the first Venus initialization result in the unit
               # journal, before compositor teardown emits secondary errors.
               VN_DEBUG='init,result', MESA_LOG_LEVEL='debug', MESA_LOG='file',
               LIBGL_DEBUG='verbose',
               VK_LOADER_DEBUG='error,warn,info,driver')"""
NEW = """               )"""
ANCHOR = '    env.update(private_mesa)'
OPT_IN = """    env.update(private_mesa)
    trace_config = Path('/etc/wsx/graphics-trace')
    if trace_config.is_file() and trace_config.read_text().strip() == '1':
        env.update(WSX_GRAPHICS_TRACE='1', VN_DEBUG='init,result',
                   MESA_LOG_LEVEL='debug', MESA_LOG='file',
                   LIBGL_DEBUG='verbose', VK_LOADER_DEBUG='error,warn,info,driver')"""


def configure(text):
    if text.count(OLD) != 1 or text.count(ANCHOR) != 1:
        raise ValueError('Unexpected desktop graphics diagnostics configuration')
    return text.replace(OLD, NEW).replace(ANCHOR, OPT_IN)
