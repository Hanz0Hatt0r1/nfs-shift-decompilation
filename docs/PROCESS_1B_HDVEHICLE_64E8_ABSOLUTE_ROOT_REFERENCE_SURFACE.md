# Process 1B — HDVehicle +0x64e8 absolute-root reference surface

## Scope

This slice narrows the remaining P1.3 non-literal writer search after the Participants Manager lifecycle surface was closed by PR #1570. It examines only PC-retail machine-code paths that materialize the exact fixed address `HDVehicle+0x4330 = 0x00c17a30`.

Authority is the PC retail 1.02 executable with SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. The Ghidra SQLite export is navigation/fingerprint support only.

## Exact references

The executable contains four exact references that load `0x00c17a30` as a receiver:

- `0x00702715` in `FUN_00702710` -> `FUN_00771e40`
- `0x0070274d` in `FUN_00702720` -> `FUN_00771e40`
- `0x00702776` in `FUN_00702770` -> `FUN_00772350`
- `0x007027ac` in `FUN_00702770` -> `FUN_00771e40`

No other PC-retail instruction materializes the exact absolute root address.

## Callee boundary

`FUN_00771e40` updates fields under this root and its highest direct root-relative store is `+0x2178`. The unresolved target is `+0x21b8`, so this routine does not write it. It also does not forward the exact root receiver to another callee.

`FUN_00772350` forwards the exact root only to `FUN_00771e40`. Its remaining calls operate on the external parameter or on root-derived subobjects such as `root+0x1688`, `root+0x10e8`, `root+0x1138`, `root+0x16d8`, `root+0x17c8`, `root+0x0fa8`, `root+0x0ff8`, the per-entry `root+0x58+n*0x370` chain, and `root+0x18b8`. It does not write `root+0x21b8`.

Therefore the complete exact-absolute-root reference surface is negative for `HDVehicle+0x64e8`.

## Remaining frontier

This does **not** close the full non-literal writer surface. Still open are affine reconstruction from the `HDVehicle` root `0x00c13700`, escaped aliases, computed addresses, and unrelated writes that could place `HDVehicle+0x4330` into Participants Manager `+0x374`. The final literal site `0x004b86cf` remains fail-closed and is not rejected by this slice. Provider count remains 7.
