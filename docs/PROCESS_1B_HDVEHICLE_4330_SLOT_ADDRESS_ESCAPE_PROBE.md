# Process 1B: HDVehicle+0x4330 slot-address escape probe

## Blocker

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15` and the merged same-block computed-alias probe leave interprocedural writer paths open for source slots `0x00b83dc0` and `0x00b83ec0`.

A callee can mutate either selected slot if an exact address of that slot escapes as an argument. This probe bounds one concrete class: exact selected-slot addresses pushed into direct callees after local constant propagation.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_slot_address_escapes.py` is SHA-locked to authoritative PC retail 1.02 and tracks exact slot-address constants through:

- immediate register loads and register copies;
- `lea` with fully resolved constant expressions;
- `add/sub` immediate transforms;
- `push` arguments immediately consumed by a subsequent direct/indirect `call` in the same control-flow span.

Pending arguments and constant state are discarded at branches, jumps, returns and traps. The report emits only calls that receive exact `0x00b83dc0` or `0x00b83ec0` addresses.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_slot_address_escapes.py \
  /path/to/SHIFT.exe \
  --output evidence/p1b_hdvehicle_4330_slot_address_escape_probe.json
```

## Evidence boundary

This probe does not claim interprocedural writer closure. It does not yet cover register-argument ABIs, stack aliases reconstructed inside callees, callee-created aliases, heap/object replacement, arbitrary runtime mutation, or generated/self-modifying code.

Therefore these remain fail-closed:

- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact runtime identity for the two memory-derived indirect CALLs;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Next

Run the probe against authoritative `SHIFT.exe`, classify every callee receiving an exact selected-slot address, and then expand into register-argument and callee-created alias classes.
