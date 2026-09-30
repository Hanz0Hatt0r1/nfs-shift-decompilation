# SHIFT WayPointBase derived query-position pass evidence

This note records the source-backed first waypoint geometry pass implemented by
`FUN_007ade00`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function and caller order

`FUN_00719ea0` prepares the database-wide waypoint geometry in two passes.

First it computes a float at AIDatabase `+0xe0`:

`factor = 1.0 - (DAT_00c12c38 + DAT_00c12c3c) * 0.5`.

It then calls `FUN_007ade00(record, factor)` for every one of the
`AIDatabase +0x68` WayPointBase records at `+0x70`, using the already
proven `0x1bc` stride.

Only after every record has completed that first pass does `FUN_00719ea0`
loop over the same array again and call `FUN_007ada70`.

This ordering matters because `FUN_007ada70` reads the derived position
written by `FUN_007ade00` from linked neighbor records.

## Reflected inputs

`FUN_007ade00` reads four already identified WayPointBase fields:

| Field | Offset |
|---|---:|
| reflected `Position` | `+0x10` |
| reflected `Perpendicular` | `+0x1c` |
| reflected `Dry Lat` | `+0x48` |
| reflected `Wet Lat` | `+0x4c` |

The function does not inspect `active_marker +0x18e`. The caller likewise
invokes it over every record in the logical waypoint count.

## Lateral blend

The source computes:

`lateral = (1.0 - factor) * WetLat + DryLat * factor`

and stores the result at unreflected WayPointBase `+0x138`.

There is no clamp of `factor` in `FUN_007ade00`; values outside
`[0,1]` therefore extrapolate.

The implementation keeps the input/output float boundary rather than assigning
a gameplay name to the AIDatabase `+0xe0` factor or its two global inputs.

## Derived query position

The function then calls two generic vector helpers:

- `FUN_004368e0(dst, vector, scalar)` is directly recovered as
  three-component scalar multiplication;
- `FUN_00432c00(dst, a, b)` is directly recovered as three-component vector
  addition.

Therefore the second half of `FUN_007ade00` is exactly:

`derived_position = Position + Perpendicular * lateral`.

The three float result is written to unreflected WayPointBase
`+0x8c/+0x90/+0x94`.

This same vector is consumed by:

- global path query `FUN_007189a0`;
- linked local query `FUN_00718d00`;
- second geometry pass `FUN_007ada70`.

The two query implementations already on main therefore now have a
source-backed producer for their previously structural `+0x8c` position.

## Runtime implementation

`src/ai/waypoint_derived_position_runtime.py` exposes:

- the exact Wet/Dry lateral interpolation;
- source-equivalent vector scale/add;
- one-record byte update of `+0x138` and `+0x8c..+0x94`;
- the AIDatabase array loop with the exact `0x1bc` stride;
- bounded `count` behavior while preserving storage beyond the logical array.

The module intentionally stops before `FUN_007ada70`. Direction,
link-distance, orientation and curvature outputs belong to the second geometry
pass and remain separately evidence-gated.
