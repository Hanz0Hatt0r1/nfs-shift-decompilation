# Process 1B — escaped HDVehicle root +0x4330 runtime surface

## Scope

This slice closes a non-direct materialization path that was intentionally left outside the exact-root affine frontier. `FUN_00702720` and `FUN_00702770` explicitly load `ECX = 0x00c13700` before handing control to `FUN_00768a30`, so `FUN_00768a4d` receives the exact PC-retail HDVehicle root.

## Runtime path

`FUN_00768a4d` captures the incoming root in `ESI`. At `0x00768c16` it materializes `ESI+0x4330` and calls `FUN_00772570`.

`FUN_00772570` does not read or write `+0x21b8`. Its only same-receiver callee is `FUN_00771db0`, which reads `+0x1b4c/+0x1b40/+0x1b38`, derives the `+0x2128` subobject, and does not forward the original receiver further.

Therefore this exact escaped-root runtime path is negative for writes to `HDVehicle+0x64e8` (`HDVehicle+0x4330 + 0x21b8`).

The compiler unwind cleanup at `Unwind@00a7063f` also computes `base+0x4330`, but it only jumps to the already-bounded destructor `FUN_00756050`; it is not promoted to a runtime producer path.

## Adjudication

This closes `FUN_00702720/70 -> FUN_00768a30/4d -> FUN_00772570 -> FUN_00771db0` as a target-negative escaped-root surface. Other escaped/reconstructed `HDVehicle+0x4330` aliases remain open, as does unrelated Participants Manager `+0x374` reconstruction. Provider count remains 7.
