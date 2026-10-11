# Process 1B: HDVehicle+0x4330 register-held slot escape probe

## Blocker

`#1961` covers exact selected-slot addresses passed through stack `push` arguments. A separate interprocedural class remains when an exact address of `0x00b83dc0` or `0x00b83ec0` is live in a GPR at a CALL boundary.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_register_slot_escapes.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe` and tracks exact register constants through immediate loads/copies, resolved `lea`, `add/sub` immediate transforms and `xor reg,reg` zeroing.

At every CALL, any GPR whose exact value is one of the two selected source-slot addresses is emitted as an interprocedural escape candidate. The probe intentionally does **not** claim that the live register is an ABI argument: calling convention and callee semantics must be classified separately.

Control-flow branches, jumps, returns and traps clear constant state.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_register_slot_escapes.py \
  /path/to/SHIFT.exe \
  --output evidence/p1b_hdvehicle_4330_register_slot_escape_probe.json
```

Expected SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

## Gate effect

This stacked probe extends interprocedural coverage only. It does not promote:

- `register_argument_abi_classified`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- `memory_derived_indirect_call_target_identity_complete`;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

The probe does not yet classify callee-created aliases, stack-memory aliases, heap/object replacement, arbitrary runtime mutation, or generated/self-modifying code.

## Next

Run on authoritative retail `SHIFT.exe`, classify each register-held selected-slot CALL boundary by calling convention and callee behavior, then trace any callee-created writer aliases before reconsidering exact runtime target identity.
