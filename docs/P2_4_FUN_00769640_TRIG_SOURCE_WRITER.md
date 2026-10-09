# Process 2 P2.4 — `FUN_00769640` trig-source writer

## BLOCKER

`SHIFT.Fun007584f0PositiveQwordTrig/1` owns the retail f64→f32→`FCOS`/`FSIN` bridge, but the two source qwords at `HDVehicle+0x0738/+0x11b8` were still treated as externally acquired values.

Retail `FUN_00769640` is the immediate writer for those qwords. This slice internalizes the proven writer arithmetic and record geometry while deliberately leaving table-value lifetime/acquisition open.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Exact writer span:

`0x00769c05..0x00769c2d`, 40 bytes, SHA-256:

`4ec2458e9f056d77b30baae9dbfe9a20b9e56d6069f19155d9542966709fa26d`

The machine sequence is:

```text
FILD  int32_coefficient
FMUL  slope_qword
FADD  base_qword
FST   destination_qword
```

so the valid-domain mathematical writer is:

```text
result = base_value + int32_coefficient * slope_value
```

## HDVEHICLE PROVENANCE

Merged Process 1 machine evidence already proves that the first physical stack argument to `FUN_0076b280` is exactly `HDVehicle+0x4330`. `FUN_0076b280` forwards that argument to `FUN_00769640`, so the writer table is rooted in the selected HDVehicle rather than a separate external object.

`FUN_00769640` selects records 12 and 13 from a `0x50`-byte table:

| loop | base qword | slope qword | int32 coefficient | destination |
| --- | --- | --- | --- | --- |
| 0 | `HDVehicle+0x54b8` | `+0x54c0` | `+0x54cc` | `+0x0738` |
| 1 | `HDVehicle+0x5508` | `+0x5510` | `+0x551c` | `+0x11b8` |

These offsets follow from the proven `HDVehicle+0x4330` root, relative record base `+0x0dc8`, coefficient base `+0x0ddc`, record stride `0x50`, and selected indices 12/13.

## OUTPUT

`SHIFT.Fun00769640TrigSourceWriter/1` now owns:

- record selection 12/13;
- table geometry;
- destination geometry `+0x0738/+0x11b8`;
- the writer formula `base + coefficient*slope`;
- finite-input/result validation.

The existing `FUN_007584f0` CTest feeds a deterministic native writer result (`0 + 2*0.125 = 0.25`) directly into the native trig bridge and retains the exact Phase748 `FCOS`/`FSIN` witnesses.

## LIMITS

This slice does **not** claim:

- native ownership/lifetime of table values at `+0x54b8..+0x551c`;
- complete internalization of `FUN_00769640`;
- bit-identical excess-precision behavior for every ambient x87 environment.

Therefore the writer arithmetic is native, but source acquisition remains an explicit frontier. The positive-qword producer family remains incomplete, `FUN_007584f0_computed_payloads` remains present, top-level `FUN_00765c40` remains present, lower scene query remains external, and external provider count remains **7**.

## NEXT STEP

Trace the writers/lifetime of the six selected HDVehicle table fields. If they already map to native load/config state, bind them into this writer; otherwise internalize the smallest proven producer upstream before promoting the positive-qword family.
