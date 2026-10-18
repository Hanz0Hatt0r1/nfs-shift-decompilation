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

A hash-pinned Revenginstr P-code pass now covers this gate, the two inspected callers,
and its direct helpers; the 351 exported rows and instruction-level cross-check
are recorded in [the UI state-gate evidence report](REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md).
The two inspected callers, `0x0045c480` and `0x004692e0`, call `0x0050ceb0` on the
`0x00545d90` singleton plus `0x108`. The gate passes its argument plus `0x10`
to `0x0082f3c0`, which checks a word at helper argument plus `0x24`; the
combined state field is singleton plus `0x13c`.

Instruction-level evidence confirms that a nonzero field at gate offset
`0x34`, or a nonzero result from `0x0050c880`, returns true through
`0x0048fb36`. A zero helper result can call a virtual method at offset `0x24c`
through the object at gate offset `0x48`, then returns false. The helper first
checks its byte at `+0x0c`; if nonzero it calls a virtual method at slot `+4`.
The history address `0x0050c8a9` is its zero-byte path, which returns zero; a
following `0x00833670` is consistent with the gate's optional virtual callback.
The image also contains an indirect call through `0x00ac59d0` on a helper path.

The live field values, callback result, and selected frontend transition remain
unknown. Function-level P-code alone misrepresents two transfers through
overlapping code entries, so the checked instruction slices are part of the
evidence. No captured value yet shows whether this gate prevents frontend
initialization or retail draw submission.

The old v66 `Base System` allocator fatal did not recur in v112, v113 or v114
and is historical unless observed again. The current software frontier is identifying which frontend state and draw
submission should run during the active app loop, and whether the `0x0050ceb0`
state gate or its surrounding state machine is preventing that transition.

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
return. Trace the frontend transition and renderer submission called during
that loop; resolve the object state around `0x0050ceb0` / `0x0050c880` and map
its callers into the UI state machine. Check how those retail draw resources
reach the Vulkan backend before changing scheduler or Win32 services. Implement
the smallest correction supported by evidence and run another bounded probe. Keep generated binaries
and supplements in the external artifact cache.

The existing race capture still lacks one shared dynamic stream-1 vertex-buffer
payload. Do not capture it unless renderer-side static analysis shows those
exact bytes are needed.
