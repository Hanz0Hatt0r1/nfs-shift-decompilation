# Process 1B: HDVehicle+0x4330 callee stack CFG alias writer probe

## Blocker

The merged direct-callee CFG register-alias coverage and pending stack-alias probe still leave one concrete persistence class open: an exact selected-slot address can be spilled to a fixed EBP/ESP local, survive a direct conditional/unconditional CFG edge, reload into a GPR, and become a write destination.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_stack_cfg_alias_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For direct callees entered with exact `0x00b83dc0` or `0x00b83ec0` values in GPRs, it tracks:

- exact register aliases;
- fixed `[ebp+off]` / `[esp+off]` stack-slot spills;
- reloads from those exact stack slots;
- direct conditional and unconditional CFG successors;
- writes through recovered exact register aliases.

The CFG worklist is exact-state and bounded. Nested calls terminate a path. State-limit hits and unresolved branch targets are reported explicitly.

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

Stack-pointer normalization, nested callees, indirect branch targets, heap/object replacement, arbitrary runtime mutation, and generated/self-modifying code remain open.

## Next

Run on authoritative `SHIFT.exe`; classify recovered stack-CFG exact-slot writers. Only then extend concrete surviving paths through nested calls or stack-pointer-normalized aliases.
