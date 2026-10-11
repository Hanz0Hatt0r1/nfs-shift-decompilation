# Process 1B: HDVehicle+0x4330 computed alias writer probe

## Blocker

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15` narrows the two positive memory-derived CALLs to bounded visible table targets `0x00553260` and `0x00553a90`, neither of which is a canonical P1B carrier. The remaining blocker is writer completeness for source slots `0x00b83dc0` and `0x00b83ec0`: computed aliases, runtime mutation and interprocedural stores are still open.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_computed_alias_writers.py` adds a SHA-locked scan over authoritative PC retail 1.02. It tracks exact register constants inside one linear control-flow span and resolves register-derived memory destinations such as:

- `mov reg, imm` / register copy;
- `lea reg, [constant expression]`;
- `add/sub reg, imm`;
- scaled-index address expressions where every participating register is exact.

Constant state is cleared at calls, branches, jumps, returns and traps. Only writes whose resolved effective address is exactly `0x00b83dc0` or `0x00b83ec0` are emitted as selected computed-alias writers.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_computed_alias_writers.py \
  /path/to/SHIFT.exe \
  --output evidence/p1b_hdvehicle_4330_computed_alias_writer_probe.json
```

The executable must match SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Gate effect

This PR adds the analyzer and regression surface only. It does **not** promote runtime/alias writer completeness or exact runtime target identity before a retail report is generated and every recovered writer is classified.

Still fail-closed:

- `runtime_or_alias_writer_provenance_complete`;
- `memory_derived_indirect_call_target_identity_complete`;
- global `indirect_entry_into_carriers`;
- `manager+0x374 -> HDVehicle+0x4330` identity join;
- `0x004b86cf` / slot2;
- aggregate P1.3.

External provider count remains 7.

## Next

Run the probe on authoritative `SHIFT.exe`. If selected writers are recovered, classify their source values and call-target consequences. Then expand to value-derived, interprocedural, heap/runtime and arbitrary mutation writer classes before reconsidering the exact runtime target identity gate.
