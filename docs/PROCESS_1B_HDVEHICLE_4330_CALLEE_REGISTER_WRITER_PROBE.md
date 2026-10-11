# Process 1B: HDVehicle+0x4330 callee register writer probe

## Blocker

The caller-side register-held slot-address inventory still leaves callee-created aliases open. A direct callee can receive the physical GPR value unchanged at entry, copy it to another register, and mutate the selected source slot before any branch or nested call.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_register_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For a direct CALL where an exact `0x00b83dc0` or `0x00b83ec0` value is live in a GPR, the probe:

- resolves the direct callee target;
- seeds callee entry aliases with the physically live register values;
- follows register copies and exact zero-offset `lea` aliases;
- detects writes through `[alias_reg]` in the first straight-line callee span;
- stops at the first branch, jump, return, trap, or nested call.

This avoids making a calling-convention claim: the proof is only that the selected slot address is physically present in a register at callee entry and remains exact until a bounded dereference/write.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_callee_register_writers.py \
  /path/to/SHIFT.exe \
  --output evidence/p1b_hdvehicle_4330_callee_register_writer_probe.json
```

Expected SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

## Gate effect

No global semantic gate is promoted by the probe alone. These remain fail-closed:

- `callee_created_alias_writer_provenance_complete`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact runtime identity for the two memory-derived indirect CALLs;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

The current bound is only the first straight-line direct-callee span. Branch successors, nested callees, stack-memory aliases, heap/object replacement, arbitrary runtime mutation, and generated/self-modifying code remain open.

## Next

Run on authoritative retail `SHIFT.exe`. If first-span exact-slot writers are recovered, classify their source values. If none are recovered, extend only surviving aliases across concrete branch or nested-call boundaries reported by retail evidence.
