# Process 1B: HDVehicle+0x4330 memory-target writer provenance probe

## Why this exists

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14` now contains two positive memory-derived indirect CALL targets:

- `0x00553247`, derived from the object pointer loaded from `0x00b83dc0`;
- `0x005539ac`, derived from the object pointer loaded from `0x00b83ec0`.

Both calls obtain the callable value through `[object+0x4] -> edx -> call edx`. Their exact runtime target identities are still unresolved and therefore remain fail-closed.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_memory_target_writer_provenance.py` is a SHA-locked retail probe for PC 1.02. It:

- inventories every disassembly reference to `0x00b83dc0` and `0x00b83ec0`;
- separates direct absolute writes from reads/references;
- records writer instruction/source operands for follow-up provenance;
- verifies the two positive call-site shapes and nearby `[object+0x4]` target loads;
- emits machine-readable JSON for the next bounded writer/alias analysis.

Run:

```bash
python tools/ghidra/analyze_p1b_hdvehicle_4330_memory_target_writer_provenance.py /path/to/SHIFT.exe --output evidence/p1b_hdvehicle_4330_memory_target_writer_provenance_probe.json
```

The executable must match SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Evidence boundary

This probe intentionally does **not** claim target identity from the fact that `[object+4]` is called. It also does not claim that direct absolute writers are the only possible writers: register-derived aliases, copies, heap/runtime mutation and other indirect stores must still be classified after the retail report is generated.

Accordingly the following gates stay false:

- exact runtime target identity complete;
- global `indirect_entry_into_carriers` ruled out;
- `manager+0x374 -> HDVehicle+0x4330` identity join complete;
- final `0x004b86cf` / slot2 adjudication;
- aggregate P1.3 control producer complete.

External provider count remains 7.

## Next

Run the probe against authoritative retail `SHIFT.exe`, then trace each recovered writer and alias path into the two object-pointer slots. Only after the runtime identities behind `[object+4]` are proven may the two positive CALL sites be compared against the 15 canonical P1B carrier addresses.
