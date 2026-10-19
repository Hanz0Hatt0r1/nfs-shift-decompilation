# Retail entrypoint frontier follow-up — 2026-10-19

## Evidence

Probe v114 used the retail PE32 image with SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and
completed 1,800 host frames with Vulkan validation enabled and zero errors. It
ran 342,703 guest dispatches across 1,417 unique functions. Its saved main-thread
stack ended at `0x0090488a -> 0x009046aa -> 0x00a69160 -> 0x0040ba50 ->
0x006492d0 -> 0x00647500 -> 0x006472d0`; four worker threads were waiting and
one thread was ready. The complete machine-readable record and log are
[`entrypoint_probe_v114.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v114.json)
and
[`shift-probe-v114-function-history-1800-validation.log`](../evidence/retail_frontier_20261019/shift-probe-v114-function-history-1800-validation.log).

The 64-entry history is identical to v113 and shows calls through
`0x00637840`, `0x00508ea0`, `0x0054be00`, `0x0082db70`, `0x00894b60`, `0x00833670` and a cluster around
`0x00807030`, followed again by `0x006492d0 -> 0x00647500 -> 0x006472d0`.
Static disassembly confirms that `0x006472d0` calls `0x00649760`, which jumps
through the retail `KERNEL32!SwitchToThread` import before updating timer
fields. The history now supplies an exact call sequence to classify, but it does
not prove a hang or frontend progress. Extending the probe to 1,800 frames
increased dispatches to 342,703 without increasing the unique-function count
or changing any of the 64 recent function addresses. The guest is therefore
repeating the observed update path over the longer run, though the evidence does
not identify which state prevents later frontend initialization.

The static Ghidra export also shows why entry-point completion is not the
right success condition: `FUN_0040ba50` is an exit-controlled `do/while` main
loop. Each iteration calls `FUN_006492d0`, which updates the execution timer via
`FUN_006472d0` / `SwitchToThread`, then advances other app state; it returns
only when a virtual exit check becomes nonzero. The live guest remaining in this
loop is consistent with a running application and is not, by itself, evidence
of a hang. The missing result is demonstrated frontend state and retail draw
submission on the Linux renderer.

A hash-pinned Revenginstr P-code pass now covers this gate, the two inspected
callers, and its direct helpers; the 351 exported rows and instruction-level
cross-check are recorded in [the UI state-gate evidence report](REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md).
The two inspected callers, `0x0045c480` and `0x004692e0`, call `0x0050ceb0` on the
`0x00545d90` singleton plus `0x108`. The gate passes its argument plus `0x10`
to `0x0082f3c0`, which checks a word at helper argument plus `0x24`; the
combined state field is singleton plus `0x13c`.

Instruction-level evidence establishes the gate's true and false branches.
The v115 runtime trace now resolves its actual path over 120 host Vulkan frames:
it recorded 121 calls, all from `0x0054be00`, with 484 gate-subtree events and
no trace truncation. On every call, the gate receiver was `0x00be2500`, the
`singleton + 0x13c` word at `0x00be2534` was zero, and the callback object at
gate offset `+0x48` was null. Helper byte `+0x0c` was zero, its return low byte
was zero, and the gate returned `EAX=0`.

At `0x0054be83`, the caller tests EAX and branches to `0x0054bec8`, skipping
`0x0054be85` through `0x0054bec7`. The gate's optional virtual callback was not
invoked. The v114 history alone did not associate its later `0x00833670` entry
with a callsite. The v120 caller-call trace now maps the common tail: return
`0x0054bedc` dispatches `0x00833670`, and return `0x0054beee` dispatches
`0x00835d80`. Static instructions show those helpers call D3D9 EndScene and
Present respectively. This proves the false branch continues through the
frame-service tail, but not why the field stays zero or whether the branch
causes the missing frontend. The runtime trace, callsite mapping, raw log, and
caller instruction slice are linked from the
[evidence report](REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md).

The v117 writer-provenance pass closes the address-level gap: every traced
gate call saw a prior zero dword write from `0x0062fde0`, whose entry ECX was
`0x00be2510`. That function's P-code stores zero at `this + 0x24`, exactly the
same address as gate receiver `+0x34` (`0x00be2534`). The run again rendered
120 validated Vulkan frames with no frontend-ready state or retail D3D9 draw.
This identifies how the tested word is reset, but the member's semantic role
and whether the false branch blocks frontend progress are still unknown. See
the [v117 trace](../evidence/retail_frontier_20261019/entrypoint_probe_v117_ui_gate_field_writer_ecx.json)
and [writer P-code manifest](../evidence/revenginstr_ui_gate_writer_pcode_20261019/manifest.json).

The v119 caller-chain trace resolves the write to the `FUN_004eb550`
constructor path. Revenginstr P-code also shows `FUN_00545d90` lazily
constructing singleton `0x00be23f8`; its `FUN_00545ca0` constructor initializes
the member at `this + 0x108`, matching the runtime gate receiver. The
`FUN_00545dc0` path calls `AptInteger::GetInt` on that member after the gate
succeeds, and the accessor reads `+0x8`; the gate checks the distinct internal
word at `+0x34`. In the observed `0x0054be00` routine, false skips only the
local conditional AptInteger work and then continues through its common tail.
Ghidra has no function definition for this caller entry, so the slice is
instruction-level. The v119 trace observed no later write to the checked word.
Its internal role and effect on frontend progress remain unknown. See the
[v119 trace and Revenginstr exports](../evidence/revenginstr_ui_gate_writer_call_chain_20261019/manifest.json)
and [caller instruction slice](../evidence/retail_frontier_20261019/ui-gate-caller-0054be00-branch.txt).

Function-level P-code alone misrepresents two transfers through overlapping
code entries, so the checked instruction slices remain necessary. The gate
branch is now known; the frontend transition and retail draw submission remain
unobserved.

The old v66 `Base System` allocator fatal did not recur in v112, v113 or v114
and is historical unless observed again. The current frontier is mapping the
constructor and later lifecycle of the nested member, then following
`0x0054be00`'s false branch into frontend initialization and retail draw
submission. The state field's semantic meaning is still unknown.

## Capture decision

No additional dump from the original game is needed for this scheduler
frontier. The existing race captures already support draw-local state and
stream-0/index-buffer analysis. One shared dynamic stream-1 vertex buffer lacks
a payload; capture it only if offline analysis establishes that its exact
bytes are needed for a renderer translation. The existing buffer report
documents that bounded follow-up in
[`SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md`](SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md).

## Next engineering step

Treat the PE entry point as an active main loop, not a function that should
return. Continue mapping writes and consumers of the AptInteger member's
internal `+0x34` state only as needed to explain frontend transition. The
common tail is now mapped to D3D9 EndScene and Present; next trace the calls
that lead to the first guest draw and verify how its resources reach the
Vulkan backend. Do not change guest state, scheduler, or Win32 services without
evidence for that correction. Implement the smallest supported change and run
another bounded probe. Keep generated binaries and supplements in the external
artifact cache.

The existing race capture still lacks one shared dynamic stream-1 vertex-buffer
payload. Do not capture it unless renderer-side static analysis shows those
exact bytes are needed.
