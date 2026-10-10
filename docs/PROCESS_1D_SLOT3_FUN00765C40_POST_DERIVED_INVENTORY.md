# Process 1D — FUN_00765c40 post-derived pointer inventory

This tranche continues P1.3D after the merged wheel-root, wheel+0x678 and wheel+0x7a8 closures. It classifies the remaining machine-visible pointer families in `FUN_00765c40` without promoting numeric proximity to wheel identity.

## Machine result

Five byte-hash-locked windows are covered against PC retail 1.02 `SHIFT.exe`:

- `0x00765ed4..0x00765f28`: the `HDVehicle+0x6730` manager/subobject path;
- `0x00766081..0x007663bf`: the 12-entry `+0x3430/+0x35c8/+0x35f8` local-array loop;
- `0x007663c0..0x00766504`: the 4-entry `+0x36e0` local-array loop;
- complete decoded bodies of `FUN_00a62940` and `FUN_00a628a0` used by the `+0x6730` path.

### `HDVehicle+0x6730`

`FUN_00765c40` materializes this exact HDVehicle-local address at `0x00765ed8` and `0x00765ef5`, passing it as `ECX` to `FUN_00a62940` and `FUN_00a628a0` respectively.

`FUN_00a62940` copies the incoming receiver to `EDI` at `0x00a62947`. During runtime node setup the exact receiver is persisted as a back-pointer at:

- `0x00a62a20`: `[node+0x24] = HDVehicle+0x6730`;
- `0x00a62a63`: `[node+0x34] = HDVehicle+0x6730`.

This is a real runtime-generated pointer store, but the pointer identity is the distinct `HDVehicle+0x6730` manager/subobject. It is **not** the selected wheel root `HDVehicle+0x2380`, a wheel-relative alias, or the selected target `HDVehicle+0x28b8..+0x28bf`.

`FUN_00a628a0` copies the receiver to `ESI` at `0x00a628a5`; after that assignment the complete body contains no store or push of the receiver value itself.

### Remaining HDVehicle-local arrays

`FUN_00765c40` also materializes:

- `HDVehicle+0x3430`, `HDVehicle+0x35c8`, `HDVehicle+0x35f8` for a 12-entry loop;
- `HDVehicle+0x36e0` for a 4-entry loop.

Their cursors are held in stack locals and advanced with fixed strides. They are not selected wheel aliases. Some cursor-derived values are passed into helper functions, so this tranche does not claim their complete callee lifetime is closed.

## Boundary

The following remain fail-closed:

- callee-facing lifetime of the `+0x3430/+0x35c8/+0x35f8/+0x36e0` array cursors;
- runtime/generated **selected-wheel** aliases;
- aggregate pointer copies;
- callbacks and indirect entry;
- global stored/escaped-alias and slot3 writer provenance gates.

Therefore `runtime_generated_pointer_stores_ruled_out`, `callee_created_aliases_ruled_out`, `stored_or_escaped_aliases_ruled_out`, `slot3_writer_provenance_proven`, `p1_3d_complete`, and aggregate P1.3 remain false. External provider count remains 7.

## Next step

Trace the four immediate helper surfaces receiving these local-array pointers: `FUN_007afd20`, `FUN_007baa70`, `FUN_00747b90`, and `FUN_007aefb0`, and adjudicate any nonlocal persistence with exact pointer provenance.
