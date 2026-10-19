# SHIFT retail D3D9/Vulkan frontier — 2026-10-19

## Result

The bounded original-PE probe now reaches and stays in the guest application
loop. The v193 run used `tools/retail_frontier.py run`, the pinned PC 1.02 PE,
the 41,538-function P-code module, and the retained startup supplements. It
executed 96,082 guest function dispatches across 1,559 functions, rendered 120
host Vulkan frames with zero validation errors, and remained active at
`0x006472d0` with four worker threads waiting. The report classifies this as an
advanced `host-frame-loop`; it explicitly does not prove retail rendering.

The guest requested 122 D3D9 clears and 121 `Present` calls. Clear requests
were black (`flags=0x7`, depth 1.0), and Present used null source/destination
rectangles, window override, and dirty region. The current guest shims accept
these calls to continue startup, but neither submits the guest clear nor
transfers a guest frame to Vulkan. The 120 host frames still draw the synthetic
MGEO probe mesh. No retail draw has reached the Vulkan command stream.

## Startup frontier advances

| Probe | Observation |
| --- | --- |
| v184 | D3D9 `SetRenderState` state `0xA8` value `0x0F` |
| v185 | 65,259 dispatches / 1,515 functions; missing P-code `0x00853170` |
| v186 | 65,263 / 1,517; missing P-code `0x00852e00` |
| v187 | 65,271 / 1,521; first `BeginScene` call |
| v188 | 65,276 / 1,526; `SetViewport` |
| v189 | 65,530 / 1,550; missing P-code `0x0082db40` |
| v190 | 65,534 / 1,552; first `Present` call |
| v191–v193 | Host frame loop; guest main thread remains active in the app loop |

Ghidra exports for `0x00853170`, `0x00852e00`, and `0x0082db40` each lowered
1/1 with zero rejections using `revenginstr` revision `cc308e2`. Their compact
exports and build reports are in
[`evidence/revenginstr_pcode_supplements_20261019/`](../evidence/revenginstr_pcode_supplements_20261019/).
Generic `revenginstr` fixes for x87 unnormal binary80 classification and stale
`FPREM` C2 status were merged in [PR #151](https://github.com/Hanz0Hatt0r1/revenginstr/pull/151)
and [PR #152](https://github.com/Hanz0Hatt0r1/revenginstr/pull/152); those fixes
allowed the probe to pass the x87 classifier/remainder loop and reach the
current D3D9 path.

The runtime now creates the observed 1024×4096 A8R8G8B8 render-target texture
as a Vulkan image and the observed 128 KiB D3D9 vertex buffer as a Vulkan
buffer. The guest shim also tracks texture and buffer lifetime, render-target
and depth-surface references, render state, Begin/EndScene, and the observed
viewport. Buffer-lock upload was not observed in the v191–v193 logs, and this
does not yet implement D3D9 draw translation.

## UI loop evidence

The v192 trace recorded 121 evaluations of `0x0050ceb0` from `0x0054be00`. On
every evaluation the gate word was zero and the callback object was null; the
helper flag was zero on all 121 helper checks. The guest stayed at
`0x006472d0`, with the same app-loop call stack seen in earlier probes and four
worker threads waiting. The trace does not identify a new writer. The v117
trace records `0x0062fde0` storing zero through the known constructor path,
but the callback registration and frontend-transition role remain unresolved.
See [`entrypoint_probe_v192_d3d9_frontier.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v192_d3d9_frontier.json)
and [`entrypoint_probe_v117_ui_gate_field_writer_ecx.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v117_ui_gate_field_writer_ecx.json).

The v193 machine-readable automation result is
[`entrypoint_probe_v193_automation.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v193_automation.json).
Raw P-code ELF, retail data, and full runtime logs remain in the ignored
external artifact directory; the tracked report stores the log hash.

## Next work

1. Trace the UI gate's callback owner and initialization path from
   `0x0062fde0`; do not force the gate value without confirming the expected
   state transition.
2. Connect guest D3D9 `Clear` and `Present` to Vulkan swapchain commands, with
   resource and lifetime evidence. The present shim is limited to the observed
   null-argument request and is not a rendered frame.
3. Instrument and implement the first guest draw path, including stream and
   index data, shader bindings, render target, and Vulkan command submission.
4. Measure the separate milestones: first retail Vulkan clear, first retail
   draw, frontend, and offline race.

The target-specific cached native build, the `shift_runtime_recompiled_pcode_module`
CTest, and the retail-frontier Python regressions passed for this update.
