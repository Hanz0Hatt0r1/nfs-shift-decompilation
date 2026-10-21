# Process 1 — optional D3D9 packet capture integration (2026-10-21)

The Linux runtime can opt into Process 2's D3D9 packet capture adapter when it
builds the adapter table for the recompiled PE32 runtime. Set a non-empty
`SHIFT_D3D9_PACKET_CAPTURE_DIR` to the output directory before starting the
runtime. If the variable is unset or empty, the regular runtime callbacks are
used and no packet-capture adapter is installed.

The capture adapter stays owned by `Runtime` for as long as the P-code module
can call its callbacks. It forwards resource callbacks to the existing runtime
backend and records supported `DrawIndexedPrimitive` packets. Its first-draw
limit is one. The capture adapter enables managed DXT5 and DXT3 snapshots so
the guest can provide raw compressed mip bytes; DXT3 has its own capability
bit in both the P1 producer and P2 capture adapter (P2 PR #2143). Neither bit
enables compressed-texture upload in live Vulkan.

The output is an offline capture input for Process 2's bundle builder. This
integration does not submit the captured guest draw through the runtime's live
Vulkan draw path and does not establish retail frontend, race, or image-parity
success. The guest runtime must first reach a supported indexed draw. The
adapter also fails closed when dynamic buffer history does not prove the bytes
needed for a draw.

The motivating retail evidence is SHIFT.exe SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, frame
14483, event 9694795: a triangle-list draw binds a DXT5 texture, but the prior
capture reports `snapshot_status=capture-failed`. The evidence motivates
managed DXT5 packet support; it does not prove that the Linux P-code runtime
reaches this draw.

## Managed DXT3 runtime evidence

The original SHIFT.exe capture from the system-Wine run is
`shift_d3d9_capture.jsonl`, SHA-256
`db71d32484c35d97c2aa8645d8f439376d7c1caaaca6041aa565f7549870625b`. It
contains event 2691/frame 20 for a managed DXT3 texture (FOURCC `0x33545844`),
1024×512, one level, usage 0, pool 1. Event 37037/frame 281 records a captured
512×512 managed DXT3 payload, pitch 2048, 262144 bytes, SHA-256
`3148e693a19b0d95a2a021dea80ff78c93b42ec366e4a1b6b31b9e14638e5f96`.

P1 frontier v662 reported `unsupported D3D9 managed texture description` after
42,542,707 dispatches. The producer previously accepted managed A8R8G8B8,
A1R5G5B5, and capability-gated DXT5, but not DXT3. The trace does not yet
identify the exact guest call that produced the v662 error, so the captured
retail DXT3 descriptor is concrete evidence for the same unsupported-format
path, not proof that this single descriptor caused that run's failure.

P1 now represents DXT3 with its own adapter capability, uses the same 4×4,
16-byte block layout as DXT5, and carries those bytes through managed
`CreateTexture`, DDS loading, mip sizing, and block-aligned `LockRect`. DXT1,
DXT2, and DXT4 remain unsupported by the managed runtime path. The new
capability defaults to false; P2's capture adapter opts into DXT3 in PR #2143.

With those changes combined, v666 completed the recompiled guest P-code
host-frame loop using the original retail PE: 1,440 requested/rendered host
frames, 44,964,062 dispatches, and 6,625 unique guest functions. The run
reported no blocker and `guest_draw_translation=false`; it therefore crossed
the previous managed-texture stop under this configuration, but did not prove
a retail guest draw, frontend, race, or rendered retail image. This is a
recompiled runtime replay of the retail PE, not a native Windows `SHIFT.exe`
launch. The selected run data and log hash are recorded in
`evidence/retail_frontier_20261021/process1_pcode_frontier_v666_dxt3_trace_summary.json`.

### D3D9 import trace after v666

The v668 360-frame probe selected 19 D3D9 methods, including the four draw
entry points. It recorded 1,108 Clear calls, 1,107 each for SetRenderTarget,
BeginScene, EndScene, and Present, 17 CreateVertexBuffer calls, 16
CreateIndexBuffer calls, one CreateTexture, one CreateDevice, and one each for
SetPixelShader and SetVertexShader. No selected Draw* entry was recorded in
5,573 call-trace entries. The run completed its host-frame loop with 1,734,402
P-code dispatches, 4,728 unique functions, five waiting workers, no validation
errors, and `guest_draw_translation=false`. Its D3D9 bridge submitted 360
clears and presents and retained 747 pending presents. This means this trace
did not reach the P1 `DrawIndexedPrimitive` packet callback; it does not
identify why the guest did not submit a draw.

The raw live log is 9,653,915 bytes and remains outside Git; its SHA-256 is
`9630914c79a0816f453580f0bc884480df3f2f144cf158e4e735a7887a41cf37`. The
durable counts, probe configuration, and scope limits are recorded in
[`process1_d3d9_calltrace_v668_summary.json`](../evidence/retail_frontier_20261021/process1_d3d9_calltrace_v668_summary.json).

### v672 display-list path probe

The v670/v671 retries were made with a runtime binary that did not include
Process 2's DXT3 capture-capability commit `1fef18a8`; setting
`SHIFT_D3D9_PACKET_CAPTURE_DIR` alone did not advertise managed DXT3 support.
The v671 retry therefore stopped at the same managed-texture check. v672 used
the integrated binary containing P1 commits `e6f674a6` and `1a25ef48` plus P2
commit `1fef18a8`; it crossed that check and completed the 360-host-frame
bound. The v672 runtime binary SHA-256 is
`230a92c641305c1f7c84938a4c52d3def17f59914f40886616bd5e5942866b1b`.

The targeted v672 call trace recorded `FUN_00835590` 264 times from
`FUN_00835d80`, returning `EAX=1` each time. In that captured prefix,
`FUN_00835590` called `FUN_0082f3c0` 5,544 times, with every recorded return
equal to 1; the selected trace had no `FUN_00831380` entry before its 8,192
entry-event limit. The supplied Ghidra body for `FUN_0082f3c0` returns one
when the DWORD at `param_1+0x24` is zero. This proves the predicate result for
those calls, but not why that field was zero, whether the associated state
work should have been queued, or what happened after trace truncation.

The bounded run still reports `guest_draw_translation=false`; the snapshot
function was `0x00843ed0`, worker-waiting count was 3, and there were no
validation errors. Clear and Present submission counts remain host bridge
activity. This trace does not establish a retail menu, race, guest Draw*, or
retail image. The raw log remains outside Git (8,332,993 bytes; SHA-256
`c96f00890cf4509b73b93c8f3e855880f2883ab8f9e665fa2efe2fd8f470b90e`). Its
summary records the trace-cap caveat and the v670/v671 binary mismatch in
[`process1_pcode_frontier_v672_display_list_trace_summary.json`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v672_display_list_trace_summary.json).

### v675-v678 queue trace and diagnostic correction

v674 first recorded `FUN_00831380` 288 times from `FUN_00835590` and once
from `FUN_007ee360`, but did not sample its receiver fields. v675 attempted
that read-only sampling and stopped at dispatch 463,068 with a reserved-low-
memory error. The trace code itself had used the normal guest RAM reader for
receiver slots and the return address, so observing a call with low/null
addresses could set the runtime error. P1 now uses diagnostic reads for trace
slots and return addresses and marks addresses below `0x10000` unavailable.
A fixture with `ECX=0`, `ESP=0`, and selected low receiver slots covers this
case.

The focused `shift_runtime_recompiled_pcode_module` CTest passed after the
fix. A P1-only runtime replay then passed the trace-failure point and stopped
later at the known `unsupported D3D9 managed texture description` because
that build did not contain P2's DXT3 capability commit; it is not a new P1
gameplay blocker. The integrated P1/P2 build with the trace fix completed 360
bounded host frames.

v678 selected only `FUN_00831380`, so the call trace did not truncate. It
recorded 664 entries and returns: 663 calls from `FUN_00835590`, each with
`AL=1`, and one call from `FUN_007ee360` with `AL=0`. For the 663 calls from
`FUN_00835590`, the sampled DWORD at receiver `+0x24` was 1, 2, or 3, exactly
221 times each. The first captured receiver field at `+0x1c` was written by
`FUN_0062f53d`; `+0x24` was written by `FUN_004cb900`. Later values 2 and 1
at `+0x24` have last writer `0x00d699b0`. The output slot was sampled only on
entry, and the nested `+0x14` value was not captured; no object type is
inferred from these addresses.

This later complete target-filtered window shows that the v672 prefix was
incomplete: `FUN_00831380` returns items later in the bounded path. It still
does not link those items or the following virtual calls to a guest `Draw*`
call. v678
reports `guest_draw_translation=false` and `retail_rendering_proven=false`.
The raw log remains outside Git (1,561,961 bytes; SHA-256
`bf9ce21ed77e7cec9776feacb51f4f7b13ec58d0b3f5c3822ab19c99b6a6c134`). The
run summary, intermediate trace failure, build distinction, and scope limits
are recorded in
[`process1_pcode_frontier_v675_v678_trace_regression_summary.json`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v675_v678_trace_regression_summary.json).

Separately, Process 1's original-retail evidence PR [#2134](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2134)
records that the user navigated the original retail executable to the main
menu and an active cockpit race under system Wine 11.17. That confirms
frontend and gameplay for original retail PE execution under Wine; it does not
establish native Windows behavior or progress in the recompiled P-code runtime.
The v668 no-Draw result belongs only to the latter path. Until that runtime
reaches a guest draw callback with a captured packet, the P1-to-P2 renderer
handoff remains unproven.

## Checks

- A clean Release build of `shift_runtime` and
  `shift_runtime_recompiled_pcode_module_check` succeeded.
- After the trace fix, an incremental runtime/test build succeeded and the
  focused `shift_runtime_recompiled_pcode_module` CTest passed (1/1), including
  the new null-ECX/ESP trace regression.
- New P1 DXT3 checks cover independent capability rejection, the captured
  512×512 pitch of 2048, block-aligned subrect addressing, and DXT3 DDS byte
  preservation; they pass in the focused CTest.
- Process 2's `shift_vulkan_d3d9_packet_capture_adapter` CTest passed (1/1)
  with the DXT3 capture capability enabled in PR #2143.
- The v666 replay loaded the original retail PE into the recompiled runtime;
  it was not a native Windows `SHIFT.exe` process and does not add frontend,
  race, or live Vulkan draw evidence.
