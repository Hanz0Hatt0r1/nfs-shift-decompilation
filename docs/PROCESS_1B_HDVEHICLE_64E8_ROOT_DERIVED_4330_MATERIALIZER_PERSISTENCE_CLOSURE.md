# Process 1B — root-derived HDVehicle +0x4330 materializer persistence closure

## Scope

This slice follows the exact `HDVehicle+0x4330` pointer itself at the already-proven root-derived materialization sites. It is intentionally separate from the merged `+0x21b8` writer analysis.

## Result

The affine frontier proves exactly three direct `HDVehicle root + 0x4330` materializers: `FUN_00769520`, `FUN_0076b130`, and `FUN_0076df50`. The escaped-root runtime contract adds the separately proven `FUN_00768a4d` path.

`FUN_00769520`, `FUN_0076b130`, and `FUN_00768a4d` materialize the exact pointer in `ECX` immediately before one already-bounded callee. None stores the pointer, persists it on the stack, or returns it.

`FUN_0076df50` materializes the exact pointer in `EBX` at `0x0076e1c1`. While that identity is live, `EBX` is used only as an argument to the already-bounded `FUN_007c3b00`, `FUN_0076b280`, and `FUN_007618f0` paths. There is no memory store of the exact alias and no return of it. `0x0076e28e xor ebx,ebx` kills the identity before later stores using `EBX`.

The parser descendant contract already proves the full exact-receiver writer surface under these affine consumers is negative for `HDVehicle+0x64e8`.

## Adjudication

The four proven root-derived materialization sites do not create a persistent or returned `HDVehicle+0x4330` alias. This closes materializer-level persistence/return only. Pointer persistence inside downstream consumers and other runtime-derived aliases remain fail-closed.

The manager `+0x374` join remains open; literal `0x004b86cf` is not rejected; provider count remains 7.
