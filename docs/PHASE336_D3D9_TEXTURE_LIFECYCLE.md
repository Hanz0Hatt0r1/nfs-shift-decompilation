# Phase 336: D3D9 texture-object lifecycle

This phase closes the instrumentation half of the runtime texture-identity bridge.

## Goal

A `SetTexture(stage, pointer)` observation is useful but it does not by itself prove
what D3D9 object was created for that pointer. The native capture producer now emits
the successful creation boundary for 2D and cube textures, allowing the runtime parser
to join a bound pointer to its exact creation instance.

## New capture events

- `create_texture`: returned `IDirect3DTexture9*` pointer, width, height, levels,
  usage, format, pool and best-effort descriptor metadata.
- `create_cube_texture`: returned `IDirect3DCubeTexture9*` pointer, edge length,
  levels, usage, format, pool and best-effort descriptor metadata.

The producer hooks the corresponding `IDirect3DDevice9` vtable entries and records only
successful API calls.

## Runtime contract

`d3d9_texture_lifecycle.py` emits `SHIFT.D3D9TextureLifecycle/1`.

For every non-null `set_texture` binding, the report records:

- the exact runtime texture pointer;
- whether a prior successful creation event for that pointer was observed;
- the creation event's resource type and dimensions/format/pool;
- the creation event index and frame for forensic ordering.

A missing creation event remains `not-observed`; no resource identity is fabricated.

`d3d9_runtime_trace.py` now embeds this lifecycle result and propagates the creation
record into draw-local `active_texture_bindings`.

## Tests

Regression coverage verifies 2D and cube creation schemas, exact pointer joins,
unknown-pointer failure, and draw-snapshot propagation.

## Evidence boundary

This phase proves only:

`runtime texture pointer -> observed D3D9 creation instance`

It does not prove:

`runtime texture pointer -> original SHIFT DDS archive entry`

D3D9 creation calls do not expose the original game resource path or archive SHA.
The next resource-content step is to compare captured texture snapshots against decoded
retail DDS payloads while retaining the pointer/creation join as an independent
constraint.
