# Process 1B: HDVehicle+0x4330 callee CFG alias writer probe

## Blocker

Merged #1964 bounds the first straight-line direct-callee span for exact selected-slot register aliases. The next remaining callee-created alias class is an exact slot address that survives a conditional/unconditional branch before the write occurs.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_cfg_alias_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For each direct CALL boundary where `0x00b83dc0` or `0x00b83ec0` is exact in a GPR, the probe resolves the direct callee and runs a bounded exact-state CFG walk. It:

- preserves exact aliases through register copies and resolved `lea`/`add`/`sub` transforms;
- follows direct `jcc`, loop and `jmp` successors plus conditional fallthrough;
- deduplicates exact `(instruction, alias-state)` visits;
- detects writes through `[alias_reg]` anywhere in the bounded callee CFG;
- terminates a path at nested CALL, return, trap or an unresolved branch target;
- caps the worklist at 256 exact states per callee entry.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_callee_cfg_alias_writers.py \
  /path/to/SHIFT.exe \
  --output evidence/p1b_hdvehicle_4330_callee_cfg_alias_writer_probe.json
```

Expected SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

## Gate effect

The probe expands only the bounded direct-callee CFG class. It does not promote:

- `callee_cfg_alias_writer_provenance_complete`;
- `nested_callee_alias_writer_provenance_complete`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact runtime identity for the two memory-derived indirect CALLs;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

Nested calls stop a path. Stack-memory aliases, indirect branch targets, heap/object replacement, arbitrary runtime mutation and generated/self-modifying code remain open. A state-limit hit is reported and must remain fail-closed.

## Next

Run against authoritative retail `SHIFT.exe`. Classify any recovered CFG exact-slot writers by source value. If no writer survives and no state/unresolved-target boundary remains, move only to nested-call and stack-memory alias classes that are concretely observed.
