# Phase 358 — CSM collision records and PhysX scene queries

This phase continues the non-rendering physics decompilation track. Renderer,
RENDER.bff and the BMW rendering gate are untouched.

## 1. CSM record consumer

FUN_00750080 checks the collision-stream version against 0x0afb and dispatches
each record to FUN_0074e880.

FUN_0074e880 now has a machine-readable boundary:

- read one u32 discriminator;
- when discriminator is below 2, read six additional u32 fields at runtime offsets
  +0x04..+0x18;
- fields at +0x10, +0x14 and +0x18 are used as allocation counts;
- the corresponding runtime pointers are stored at +0x1c, +0x20 and +0x24;
- each allocated buffer is registered through a vtable call at +0x18.

The allocated element types are not named because the consumer body does not expose
their schema. The implementation therefore stops at the proven record boundary.

## 2. PhysX scene query wrapper

FUN_0074ef30 is reconstructed as a four-mode scene-query dispatch:

| Wrapper mode | Scene query type | Mask |
|---:|---:|---:|
| 0 | 1 | 0x7fffffff |
| 1 | 2 | 0x7fffffff |
| 2 | 1 | 0x80000000 |
| 3 | 3 | 0x7fffffff |

All calls use the scene vtable at +0x1c0, with default filter 0xffffffff.

The wrapper fails closed to 3.4028235e38 when the scene is absent, mode is
unsupported, distance is negative/NaN, or the query reports no hit. Optional
outputs expose hit position/normal and the source-backed shape-index mapping path.

## Explicit unknowns

- semantics of CSM discriminator values 0 and 1;
- semantic names for record fields +0x04..+0x18;
- allocated CSM element structures;
- exact meaning of scene-query types 1..3 at the PhysX API layer;
- shape-table semantics behind FUN_0077cbf0.

## Verification

Eight focused tests cover the record boundary, truncation behavior, exact query
dispatch values and fail-closed input validation.

All eight tests pass locally.

## Next non-render target

Continue into the concrete vehicle-physics data path: FUN_0074ec30 resource roots
(Chassis, Collision, Engines, GearBox, Suspension, Upgrades, Vehicles) and the
source-backed CarPhysicsDetails / HighDetailVehicle initialization and driveline calls.
