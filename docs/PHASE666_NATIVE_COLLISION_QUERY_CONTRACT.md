# Phase 666 — native FUN_00765c40 → FUN_007b0710 collision-query contract

Phase 666 ports the caller-visible Phase 370 collision-query/cache boundary into `shift_runtime_physics`. It does not implement or guess the collision provider behind `FUN_007b0710` / `FUN_0074f560`.

## Query record

`build_fun_00765c40_collision_query_record()` preserves the recovered caller payload:

- query position `(x, y + 0.15, z)`;
- `+0x18 = 200.35`;
- `+0x20 = 9.999999933815813e36`;
- `+0x28` reserved for returned contact height;
- `+0x30` carries the previous query/cache handle;
- cache-aware `param_3 = 1`.

The record remains described by source offsets instead of relying on host C++ structure packing.

The transform that produces the incoming `(x,y,z)` world-position value remains external. Phase 666 does not invent its ownership or coordinate provenance.

## Returned 0x58-byte cache record

The native contract freezes the source-observed layout:

- `+0x04` cached query point;
- `+0x10` returned normal;
- `+0x1c` contact height;
- `+0x20/+0x2c/+0x38` triangle vertices;
- `+0x44` valid flag;
- `+0x50` hit counter;
- record size `0x58`.

`+0x00`, `+0x48`, and remaining fields stay opaque.

## Hit/miss projection

`apply_fun_007b0710_collision_query_result()` models only source-backed observable writes:

### Hit

- output normal receives the returned record normal;
- query `+0x28` receives returned contact height;
- query `+0x30` receives the returned cache-record handle;
- the returned handle is exposed;
- cache reuse is recorded when the incoming handle matches the returned address token.

### Miss

- returned handle is null;
- output normal is exactly `(0, 1, 0)`;
- no contact height is emitted.

`project_fun_00765c40_query_scalar()` then reproduces the caller-visible `+0x38e0` boundary:

- hit: `original_world_y - returned_contact_height`;
- miss: existing caller fallback from `+0x38e8`.

The returned handle itself belongs to caller state `+0x38dc`.

## Scope

This is an interface/observable-state port, not a collision engine. The following remain intentionally unresolved:

- the implementation and ownership of the collision provider;
- PhysX class/type names;
- physical names or units for the derived caller scalar;
- the exact upstream transform feeding the query world position.

The native boundary validates finite numeric inputs and cache-record vector fields and fails closed on an invalid source-valid flag.

## Regression

`shift_runtime_collision_query_contract_check` covers:

- exact query constants and source offsets;
- `+0.15` Y bias;
- cache-aware `param_3`;
- hit normal/contact-height/cache-handle writes;
- matching-cache reuse and replacement-cache behavior;
- miss `(0,1,0)` normal;
- caller hit scalar and miss fallback;
- non-finite and invalid-record rejection.

`native-physics-recent` now executes and verifies Phases 656–666.

## Next boundary

The next integration target is the source-backed composition around `FUN_00765c40`: connect a proven transformed wheel query position and per-wheel cached handle to this contract, then pass its `+0x38e0` scalar into the already-native Phase 663 `FUN_00766510` response path. Provider execution itself should stay abstract until its native track/surface ownership is proven.
