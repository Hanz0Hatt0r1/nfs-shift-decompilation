# Process 1B — HDVehicle +0x4330 parser descendant closure

## Scope

This slice closes the exact-receiver parser descendants left open by `SHIFT.HDVehicle64e8Affine4330MaterializationFrontier/1`. The receiver is the proven `HDVehicle+0x4330` subobject and the target is `+0x21b8` (`HDVehicle+0x64e8`). PC retail 1.02 machine/decompiler transfer is authoritative; SQLite is navigation-only.

## Closure result

All 11 exact-receiver callees reached from `FUN_007c3b00` are negative for writes to `+0x21b8`. Several use computed destinations, so the proof uses caller-bounded index domains rather than absence of a literal displacement alone.

Key bounds include:

- `FUN_007715f0`: observed selectors `0,1,3`, yielding `+0x2158/+0x2160/+0x2170`.
- `FUN_007bf0e0`: index `0..3`, formula `receiver + index*0x370 + field`; maximum destination `+0xd78`.
- `FUN_007bfbe0`: selector helper `FUN_007715a0` returns only `0..4`; the `FUN_00771c70 -> FUN_004338a6 -> FUN_00771c7c` table path stays at or below `+0xf28`. Its secondary row/column table helper is likewise bounded far below the target.
- `FUN_007c2110 -> FUN_007bf4e0`: selector is bounded to `<=0x34`; maximum table destination is `+0x1e28`.
- `FUN_007bf310`: observed selectors are exactly `10` and `11`, producing roots `+0x10e8/+0x1138`.

`FUN_007c3920` had a hidden same-receiver chain that required separate tracing. `FUN_007725f0` keeps its computed table in `+0x1bec..+0x1e1c` and its later explicit fields stop at `+0x2188`. The alternate chain `FUN_007c3280 -> FUN_007c01f0 -> FUN_007c0150` writes only `+0x2180`, `+0x1a98`, and `+0x1ae8` on the exact receiver.

`FUN_007be420` captures the exact receiver before reusing its local parameter variable; the only exact-receiver destinations are `+0x2364..+0x2374`. Later undertray destinations use a repurposed local and are not aliases of the HDVehicle subobject.

## Adjudication

The complete exact-receiver descendant surface reachable from `FUN_007c3b00` is now closed-negative for `+0x21b8`. Combined with the three exact-root affine materializers, the proven `root -> root+0x4330` affine path is negative for `HDVehicle+0x64e8` writes.

This is not yet global non-literal closure. Escaped aliases or other reconstructions that do not arise from the three exact-root affine materializers remain possible. Unrelated Participants Manager `+0x374` computed/escaped writers also remain open, so the final literal site `0x004b86cf` is not rejected. Provider count stays 7.
