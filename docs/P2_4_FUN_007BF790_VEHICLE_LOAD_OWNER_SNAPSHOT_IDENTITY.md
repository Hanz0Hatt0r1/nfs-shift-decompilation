# Process 2 P2.4 — VehicleLoadData owner snapshot identity

## Scope

The existing `SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1` reads caster values from a supplied byte image, but does not check the originating HDVehicle owner field. The Phase738 ownership contract identifies `VehicleLoadData* = *(HDVehicle+0x66b4)`, with a retail 32-bit pointer and allocation size `0x3848`.

This slice adds `SHIFT.Fun007bf790VehicleLoadOwnerSnapshotIdentity/1`. Given two **externally supplied** byte images and an explicit 32-bit address token for the load-data image, it reads the owner field from the HDVehicle image as little-endian bytes, rejects null/short images and zero/mismatched addresses, and composes the existing native caster binding and record materialization.

## Source authority

PC retail 1.02 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Reuses the existing Phase738 `SHIFT.Fun007618f0VehicleLoadDataOwnership/1` and `SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1` evidence. No new field meanings or numerical caster values are inferred.

## Safety and tests

The helper never dereferences the retail pointer, never assumes host pointer width, and rejects inconsistent snapshots before reading caster fields. A focused Python regression checks upstream evidence, compiles a C++17 executable, and tests matching owner address, caster output, short/null images, zero pointer, and mismatched pointer. Existing source-backed integer conversion and zero-range prior-count semantics remain unchanged.

## Unresolved ownership

Address equality is **not** proof that the supplied bytes were actually acquired from that address, or that their lifetime is valid. Neither memory acquisition nor VehicleLoadData lifetime is native session-owned. The selected BMW CDF values remain unpromoted; `FUN_007584f0_computed_payloads` is incomplete; `FUN_00765c40` remains an external provider, and provider count stays **7**.

Next: integrate an authoritative memory/snapshot owner into `NativeVehicleProviderSession` and establish lifetime, rather than treating this identity guard as full producer ownership.
