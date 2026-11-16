# Graphics diagnostics

Desktop sessions do not enable verbose Venus, Mesa, GL or Vulkan loader logs by
default. To opt in for a new Guest session, create `/etc/wsx/graphics-trace`
containing exactly `1` (surrounding whitespace is allowed). Remove the file or
change its contents to disable the option for a subsequent session. The setting
does not restart a running session. Debug output can be large and may contain
device and resource details; handle it as diagnostic data.

The session switch enables `WSX_GRAPHICS_TRACE=1` in the desktop environment,
along with the previous verbose driver settings. For a single application, set
`WSX_GRAPHICS_TRACE=1` in that process environment instead. The private Mesa and
Venus builds gate selected high-frequency WSX success traces on that variable;
unset or any value other than `1` disables those traces. Error and rejection
messages and graphics capability, allocation and synchronization checks are
unchanged. Existing images and previously compiled private components retain
their original behavior; a new component build and matching source delivery are
required for the compiled trace policy.

## Scope and provenance

The original vendored patches and desktop launchers remain unchanged. Source
builder adaptations apply the logging policy after the pinned patches and record
the resulting source hashes in the build receipt. The reference checkout read
for this change was `wsx-proto` commit
`3199b15dd898d6033e255e6894411b4bb4cab816`; the following hashes identify the
vendored working-tree bytes, independently of that commit:

| Source | SHA-256 |
| --- | --- |
| `vendor/wsx-proto/device-host/production/start-guest.py` | `ad37b095f13d4da78d610bf635adc54c8a2e062cd9ec0d309bfbe74f509bef85` |
| `vendor/wsx-proto/device-host/production/start-cachyos-plasma.py` | `1a1f17086f16220884c09396709742433204cf855ed671f4d94b9a5e10bc4cf1` |
| `vendor/wsx-proto/guest-compat/opaque-gbm-export.patch` | `755cd00fbef9ae5818e329621f095b3101db3f831db49db7b5293fa683a67278` |
| `vendor/wsx-proto/guest-compat/venus-opaque-bind-order.patch` | `28770800c1634a5797576bb0b3fe0e237cfd84dc8cef7e018cd1199f18f61819` |

The full source pins, vendored hash inventory and component recipe inputs remain
in `components/sources.json` and `docs/provenance.json`. Tests of the log policy
and source transformations do not establish a successful graphics component
rebuild, WSL boot, GPU first frame or sustained hardware behavior.
