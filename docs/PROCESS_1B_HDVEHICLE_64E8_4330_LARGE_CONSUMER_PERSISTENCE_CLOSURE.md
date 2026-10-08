# Process 1B — HDVehicle+0x4330 large-consumer persistence closure

## Scope

This slice follows the exact `HDVehicle+0x4330` pointer after `FUN_0076df50` forwards it into the two large consumers already bounded by the affine writer contract.

## FUN_0076b280

The exact pointer is `param_1` in original stack slot `[EBX+0x8]`. Retail code rereads that slot 14 times. Twelve uses immediately become field/derived accesses. The only exact-pointer forwards are `0x0076cb40 -> FUN_00769640` and `0x0076cb4c -> FUN_007567a0`. The pointer itself is never stored to memory and is not returned.

`FUN_00769640` rereads the forwarded parameter once for a bounded table access. `FUN_007567a0` rereads it once for fields around `+0x18b8/+0x18c0/+0x18cc`. Neither stores, returns, or forwards the exact pointer.

## FUN_007618f0

The exact pointer is again `param_1` at `[EBX+0x8]`. There are 11 rereads. Exact-pointer forwarding occurs only at `0x00762a11 -> FUN_00756bb0`, `0x0076314b -> FUN_00771db0`, and `0x00763173 -> FUN_00771e10`; the remaining rereads are field/derived accesses. No exact-pointer memory store or return occurs.

`FUN_00756bb0` rereads the parameter six times for field data only. `FUN_00771db0` and `FUN_00771e10` use the receiver for field reads and derive the `+0x2128` subobject; neither persists or returns the exact root.

## Adjudication

The large-consumer families reachable from the proven root-derived affine materializer do not create persistent or returned `HDVehicle+0x4330` aliases. This completes pointer persistence/return for that bounded downstream family, but not for unrelated runtime-derived aliases.

Manager `+0x374` identity remains open; `0x004b86cf` remains fail-closed; provider count remains 7.
