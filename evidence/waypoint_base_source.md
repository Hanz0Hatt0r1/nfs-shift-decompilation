# SHIFT WayPointBase: source, PE, layout, and nearest-query evidence

This note records the retail waypoint element class used by the recovered
AIDatabase waypoint array.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Class identity and exact element size

`FUN_00a8c470` registers class `WayPointBase` at descriptor
`0x00c1c21c`, parent `BPersistent`, with reflection metadata
`DAT_00b8d7bc`.

`FUN_007ae5d0` constructs the object and writes vtable
`0x00b0cad8`. The retail PE contains the descriptor-returning RTTI getter at
`0x00715c70`; its unique vtable candidate is the same `0x00b0cad8`.

AIDatabase allocates and iterates these records at an exact `0x1bc` stride,
including vector constructor/destructor calls. Unlike the singleton
AIDatabase object itself, this provides a direct element-size anchor:
`sizeof(WayPointBase element) = 0x1bc` for the recovered array contract.

## Direct reflected fields

`FUN_007acfc0` emits 20 direct fields:

| Field | Offset | Type | Source description |
|---|---:|---:|---|
| Position | `0x10` | `0x10` | Position of waypoint always dead center of track.(maybe) |
| Perpendicular | `0x1c` | `0x10` | Perpendicular vector (positive to right) |
| Road Left/Right | `0x28` | `0x0f` | Width of road to left/right |
| Far Left/Right | `0x30` | `0x0f` | Farthest left/right we can go |
| Coll Left/Right | `0x38` | `0x0f` | Left/right edge of no-collision corridor |
| Cut Left/Right | `0x40` | `0x0f` | Offset from road left/right to set cut corridor |
| Dry Lat | `0x48` | 10 | Is defined as dry optimal path |
| Wet Lat | `0x4c` | 10 | Is defined as wet optimal path |
| Groove Alpha | `0x50` | 10 | Alpha of translucent groove polygon |
| Sector | `0x54` | `0x0d` | Which sector this waypoint follows |
| Lap Distance | `0x58` | 10 | Distance into lap (0.0 at start/finish) |
| Groove Lat | `0x5c` | 10 | Lateral offset so groove doesn't go over grass |
| Corner Speed Mult | `0x60` | 10 | Fraction of calculated speed to take corner |
| Event Type | `0x64` | `0x0d` | Event type |
| Event Speed Fraction | `0x68` | 10 | Event MPS |
| Branch ID | `0x6c` | `0x0d` | Branch id (pitstop or slot pit) |
| BitFields | `0x70` | `0x0d` | Bit fields |
| Prev Index | `0x74` | `0x0d` | Index to previous waypoint |
| Next Index | `0x78` | `0x0d` | Index to next waypoint |
| Branch Index | `0x7c` | `0x0d` | Index to branched waypoint |

All entries use reflection flags 3.

## Constructor defaults

`FUN_007ae5d0` explicitly initializes the reflected position/perpendicular and
four left/right pairs to zero, Dry/Wet Lat and Lap Distance/Groove Lat to zero,
Corner Speed Mult to `1.0f`, BitFields to zero, and Branch ID / Prev Index /
Next Index / Branch Index to `-1`.

The runtime module deliberately does not invent constructor defaults for direct
fields that are not explicitly written by this constructor, including
`Groove Alpha`, `Sector`, `Event Type`, and `Event Speed Fraction`.

## Reflected index → runtime pointer links

`FUN_00717b90` converts the three reflected waypoint indices into unreflected
runtime links for every source record whose `+0x18e` active marker is nonzero:

| Relation | Reflected index | Runtime pointer |
|---|---:|---:|
| previous | `+0x74` | `+0x17c` |
| next | `+0x78` | `+0x180` |
| branch | `+0x7c` | `+0x184` |

For each relation the source accepts a target only when the index is not the
`-1` sentinel, is below the AIDatabase waypoint count, and the target
`WayPointBase +0x18e` marker is nonzero. A valid target pointer is exactly:

`waypoint_array_base + index * 0x1bc`.

Otherwise the runtime pointer is cleared to zero and the reflected index is
rewritten to `-1`. If the source waypoint itself has `+0x18e == 0`,
`FUN_00717b90` skips it entirely and leaves its index/pointer members
untouched.

The function is called from both `FUN_0071e3ba` and `FUN_0071f099`,
including repeated calls after waypoint graph regeneration/rebuild paths. This
establishes the three pointers as derived runtime links rather than serialized
pointer values.

The retail function explicitly guards only `-1` and `index >= count`.
A malformed index below `-1` would address before the waypoint array; the
Python runtime model rejects that unsafe case rather than emulating an
out-of-bounds source read.

## Simple nearest-waypoint queries

Two small AIDatabase queries are now sufficiently constrained to reproduce
directly:

### `FUN_00718060`

For every `0x1bc` waypoint record:

- requires `Branch ID +0x6c == 0`;
- requires an unreflected 16-bit marker at `+0x18e != 0`;
- computes ordinary 3D squared Euclidean distance from query point to
  `Position +0x10`;
- keeps the first strictly smaller result.

### `FUN_00718120`

The same loop and metric, but requires `Branch ID +0x6c == 1`.

The `+0x18e` word is intentionally exposed only as `active_marker`; its
higher-level meaning is not assigned from these two consumers alone.

These two functions are distinct from `FUN_007189a0`, whose selection metric
and branch/link handling are more complex and remain outside this PR.

## Runtime implementation

`src/ai/waypoint_base_runtime.py` exposes:

- descriptor / RTTI getter / vtable / constructor / destructor identity;
- exact `0x1bc` record size;
- all 20 direct reflected fields and source comments;
- explicit constructor defaults only where written;
- byte-layout decoding for Position, Branch ID, the three reflected link
  indices, their three runtime pointers, and the `+0x18e` marker;
- source-equivalent `FUN_00717b90` index-to-pointer resolution with invalid
  target normalization;
- source-equivalent nearest active Branch-ID 0 and Branch-ID 1 queries over
  captured/decoded record bytes.

This closes the serialized-index → runtime-link bridge used by the waypoint
graph plus a small executable subset of AIDatabase waypoint lookup. The more
complex `FUN_007189a0` path-selection metric and later geometric update
passes remain separately evidence-gated.
