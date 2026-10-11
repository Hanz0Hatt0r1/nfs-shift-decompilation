# Process 1B: HDVehicle+0x4330 callee stack alias writer probe

## Blocker

The merged caller-side and direct-callee register alias probes still leave one concrete interprocedural persistence class open: an exact selected-slot address can be spilled into a callee stack local, later reloaded into a register, and then used as a write destination.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_stack_alias_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For direct callees entered with an exact `0x00b83dc0` or `0x00b83ec0` value live in a GPR, the probe tracks:

- exact register aliases;
- spills into fixed `[ebp+off]` / `[esp+off]` stack locals;
- reloads from those exact stack locals;
- writes through a recovered exact register alias.

The current bound is deliberately straight-line. It stops at branches, jumps, nested calls, returns, and traps.

## Gate effect

No semantic gate is promoted by this probe alone. These remain fail-closed:

- `callee_stack_alias_writer_provenance_complete`;
- `nested_callee_alias_writer_provenance_complete`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact runtime identity for the two memory-derived indirect CALLs;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

CFG stack-slot merges, stack-pointer normalization, nested calls, indirect branches, heap/object replacement, arbitrary runtime mutation, and generated/self-modifying code remain open.

## Next

Run on authoritative `SHIFT.exe`; classify any recovered stack-alias writers. If negative, extend only stack aliases or nested-call paths that survive retail evidence.
