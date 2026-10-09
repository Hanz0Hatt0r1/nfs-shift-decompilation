# Process 1D — `FUN_00766510` exact-root handoff

This P1.3D slice reuses two already merged retail contracts rather than reopening their ownership:

- `SHIFT.P1A.P13ASlot01X87StackOutputTrancheClosure/1` proves `FUN_00766510` receives the exact `HDVehicle` root from `FUN_0076d100` at `0x0076d137/0x0076d139`.
- `SHIFT.Fun00766510ResidualTailClosure/1` proves two exact calls to `FUN_00758fc0` with `ECX=ESI=HDVehicle`.

The calls are:

```text
0x00766da5 -> FUN_00758fc0, record HDVehicle+0x37d8
0x00766dba -> FUN_00758fc0, record HDVehicle+0x3858
```

Both share `[EBP-0xc8]` as the reference vector. The merged callee proof pins its HDVehicle accumulator application to exactly:

```text
+0x40a0 +0x40a8 +0x40b0
```

Those qword lanes are disjoint from selected slot3 `HDVehicle+0x28b8..+0x28bf`. Therefore these two exact-root deeper direct calls cannot be the selected slot3 writer.

Reproduce the handoff from merged contracts:

```bash
python3 tools/ghidra/build_p1d_slot3_fun00766510_exact_root_handoff.py \
  evidence/p1a_p13a_slot01_x87_stack_output_tranche_closure.json \
  evidence/fun_00766510_residual_tail_closure.json \
  --output out/p1d_slot3_fun00766510_exact_root_handoff.json
```

This closes only the two proven `FUN_00758fc0` transfers. Other `FUN_00766510` callees, deeper descendants, stored aliases and indirect/callback carriers remain open. Slot3 writer provenance and P1.3D remain false; provider count remains 7.
