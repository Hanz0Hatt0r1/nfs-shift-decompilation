# Phase 666 — native collision-query boundary

Phase 666 ports the caller-visible Phase 370 `FUN_00765c40 -> FUN_007b0710` contract into `shift_runtime_physics` without inventing the unresolved collision backend or the transform that produces the query world position.

## Query record

The native contract preserves the seven-double caller layout:

- query position `(x, y + 0.15, z)` at `+0x00`;
- `+0x18 = 200.35`;
- `+0x20 = 9.999999933815813e36`;
- `+0x28` is treated as an output-height slot and is not semantically initialized before a hit;
- `+0x30` carries the previous cache-handle token;
- the source-visible cache-aware call flag is `1`.

The runtime address is represented as an opaque integer token rather than a host pointer so the native contract does not claim ownership or allocator semantics.

## Returned surface record

The existing `0x58`-byte record topology remains frozen at the caller boundary:

- query point `+0x04`;
- normal `+0x10`;
- returned height `+0x1c`;
- triangle vectors `+0x20/+0x2c/+0x38`;
- valid flag `+0x44`;
- opaque auxiliary field `+0x48`;
- hit counter `+0x50`.

No PhysX class/type name is assigned.

## Hit/miss behavior

`apply_fun_007b0710_visible_result()` preserves only source-backed visible behavior:

- miss: returned handle is null and the output normal is exactly `(0, 1, 0)`;
- hit: output normal is copied from the returned record, `+0x28` receives the record height, and `+0x30` receives the returned record token;
- cache reuse is reported only when the incoming token exactly equals the returned token.

`apply_fun_00765c40_post_query_state()` then freezes the caller writes:

- `+0x38dc = returned handle`;
- hit: `+0x38e0 = original_world_y - returned_height`;
- miss: `+0x38e0 = existing +0x38e8 fallback`.

All finite scalar/vector inputs are validated; malformed `+0x44` flags fail closed.

## Regression

`shift_runtime_collision_query_check` covers:

- exact query constants and Y bias;
- cache-token propagation and exact reuse detection;
- hit normal/height propagation;
- miss `(0,1,0)` fallback;
- caller `+0x38dc/+0x38e0` hit and miss paths;
- invalid record flag and non-finite rejection.

`native-physics-recent` is extended through Phase 666.

## Remaining boundary

This phase does **not** execute the retail collision backend, traverse track geometry, infer PhysX types, or derive the query world position. The next safe step is to prove the `FUN_00765c40` world-position producer or to join this native query contract to an already evidence-backed neutral track query interface without weakening the fail-closed admission rules.
