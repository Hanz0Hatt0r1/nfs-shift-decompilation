# Process 1A — `FUN_00766510` residual tail closure

## BLOCKER

P1.1c was the remaining `FUN_00766510/contact_response` tail blocker: exact `FUN_00758fc0` scheduling, the final transformed cumulative-vector add, and the guarded residual state/diagnostic tail.

## INPUT

PC retail 1.02 remains semantic authority. The Ghidra SQLite export is used only to navigate exact callsites; machine transfer in `SHIFT.exe` is adjudicating evidence.

## OUTPUT

`SHIFT.Fun00766510ResidualTailClosure/1` closes P1.1c.

### Auxiliary pair schedule

The two `FUN_00758fc0` calls are exact and ordered:

```text
0x00766d95 lea  edx,[ebp-0xc8]
0x00766d9b lea  eax,[esi+0x37d8]
...
0x00766da5 call FUN_00758fc0
0x00766daa lea  ecx,[ebp-0xc8]
0x00766db1 lea  eax,[esi+0x3858]
...
0x00766dba call FUN_00758fc0
```

Both use `ECX=ESI=HDVehicle`, both use the same `[EBP-0xc8]` reference vector, and the record order is `+0x37d8` then `+0x3858`. The pair sits after the preceding direct cross-product callsite `0x00766cef` and before the primary direct cross-product callsite `0x00766fe9`; the later direct site is `0x00767266`.

Inside `FUN_00758fc0`, `0x007590df` calls `FUN_00753650`, then the three result lanes are added directly to `HDVehicle+0x40a0/+0x40a8/+0x40b0`.

### Final transformed vector add

At `0x00767395`, `FUN_007aefb0` transforms the cumulative vector through `[HDVehicle+0x33a0]+0xd4`. The same transformed three lanes are then added to:

```text
BODY0+0x48/+0x50/+0x58
HDVehicle+0x40a0/+0x40a8/+0x40b0
```

This is the final direct contribution to those accumulators in `FUN_00766510`.

### Guarded tail

`0x007673ac` compares `[EBP-0x1]` with zero; the branch at `0x00767400` jumps directly to the function epilogue when zero. The taken tail has exactly seven direct HDVehicle snapshot writes:

```text
+0x42f8
+0x4300
+0x4308
+0x4310
+0x4318
+0x4320
+0x4328
```

The same block references diagnostic strings including `Totl LiftCoeff`, `Measured Force`, and `Measured Torque`. No physical semantics are assigned to these snapshot fields. There are no further direct writes to the caller accumulator or BODY0 `+0x48/+0x50/+0x58` after the final add.

## GATES_CHANGED

- P1.1c auxiliary scheduling: **closed**.
- P1.1c final transformed-vector add: **closed**.
- P1.1c guarded direct state/diagnostic tail: **closed**.
- P1.1c complete: **true**.
- P1.1a complete: **false**.
- P1.1 complete: **false**.
- `contact_response` provider removal authorized: **false**.
- external-provider count remains **7**.

## NEXT_STEP

Process 1A now concentrates only on P1.1a: close the earlier runtime config globals, sample-history scheduling, and participant `+0x4b0` ownership feeding `FUN_00713630`. Only after that may Process 1 publish the final handoff to Process 2 P2.3.
