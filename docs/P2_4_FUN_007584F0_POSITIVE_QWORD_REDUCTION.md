# Process 2 P2.4 — `FUN_007584f0` positive-load qword reduction

## BLOCKER

`SHIFT.Fun007584f0PersistentWriteStage/1` already owns the two destination writes at `HDVehicle+0x0d40/+0x17c0` and their non-positive-load zero branch. Until now, the positive branch still accepted an already-computed qword value.

Direct analysis of the pinned PC-retail `SHIFT.exe` now closes the final scalar reduction immediately before the positive store.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

The exact reduction span is `0x007586f9..0x00758731`, 56 bytes, SHA-256:

`c8f5e51aeeb6a14a947ba7c5c1d44ec8b3c687765377ba8b01254c15c38e9b0f`

The x87 stack sequence computes, in component order `1,0,2`:

```text
numerator   = A[1]*B[1] + A[0]*B[0] + A[2]*B[2]
denominator = A[1]*C[1] + A[0]*C[0] + A[2]*C[2]
result      = numerator / denominator
```

`0x00758731` stores the result as qword at `[ESI+0x0d40]`. The loop runs for indices 0 and 1 with stride `0x0a80`, so the persistent destinations are `HDVehicle+0x0d40` and `HDVehicle+0x17c0`. The alternate branch at `0x0075873b` stores zero and is already owned by the persistent-write stage.

## OUTPUT

`SHIFT.Fun007584f0PositiveQwordReduction/1` internalizes only the proven final ratio reduction.

The three source vec3 values are intentionally named only `A`, `B`, and `C`. Their caller-side semantic meanings and complete construction chain are not yet proven in Process 2.

The native helper:

- preserves retail component accumulation order;
- rejects non-finite input components;
- rejects a zero/non-finite denominator;
- returns the finite qword value consumed by `SHIFT.Fun007584f0PersistentWriteStage/1`.

## LIMITS

This slice does **not** claim bit-identical x87 extended-precision rounding on every host. It owns the recovered valid-domain mathematical reduction and source ordering, not undocumented floating-point environment details.

It also does not yet internalize construction of A/B/C. Therefore:

- the two positive-load qword producers are not complete;
- `FUN_007584f0_computed_payloads` remains on the P2.4 residual frontier;
- no residual-producer promotion bit is set;
- the top-level `FUN_00765c40` provider remains present;
- the lower scene-query provider remains external;
- external provider count remains **7**.

## NEXT STEP

Recover the source construction of positional vec3 A/B/C for both loop iterations from the same retail function. Once those vector producers are native-owned, Process 2 can complete the positive-load qword family and evaluate family-level promotion.
