# SHIFT TrackDetails: source, PE, layout, allocation and lifecycle evidence

This note records the source-backed runtime contract recovered for the retail
`TrackDetails` object. It is intentionally limited to class identity, exact
allocation size, direct reflection layout, constructor-visible defaults, and
the recovered load/destructor entry points.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Class identity

`FUN_00a78170` registers `TrackDetails` with descriptor
`DAT_00bcce48`, parent `BPersistent` / `DAT_00bfa608`, and reflection
metadata through `PTR_PTR_00b81eac` → `DAT_00b81eb0`.

`FUN_0049b9c0` constructs the object and writes
`PTR_FUN_00abb208`. The retail PE independently exposes the RTTI getter at
`0x0049bce0`:

```text
b8 48 ce bc 00    mov eax,0x00bcce48
c3                ret
```

The aligned vtable associated with that getter starts at `0x00abb208`.

## Exact allocation size

The allocation stub at PE `0x00432446` pushes `0x1d4` and transfers to
`0x0049ef4d`. That path calls the retail allocator at `0x008868c0` and
then `FUN_0049b9c0`.

Therefore the recovered retail allocation size is exactly **0x1d4 bytes**.
This is stronger than a minimum-span inference. The final reflected 32-bit
field starts at `+0x1d0`, so the recovered reflection layout also reaches
the final four bytes of the allocation.

## Direct reflection layout

Ghidra emits both `thunk_FUN_00d67c70` and `FUN_00d67c70` as copies of
the same builder. After semantic thunk de-duplication, the metadata contains
**44 direct reflected fields**, not 88.

| Field | Offset | Type | Flags |
|---|---:|---:|---:|
| ScenegraphFile | `0x20` | 0 | 3 |
| LeaderboardID | `0x34` | 13 | 3 |
| Length | `0x38` | 13 | 3 |
| XLASTID | `0x3c` | 3 | 3 |
| TrackName | `0x40` | 0 | 3 |
| ShortTrackName | `0x44` | 0 | 3 |
| Track_Location | `0x48` | 0 | 3 |
| Track_Variation | `0x4c` | 0 | 3 |
| Location | `0x50` | 0 | 3 |
| Track Type | `0xa0` | 0 | 3 |
| Allowed Weather | `0x110` | 0 | 3 |
| Allowed TimeOfDay | `0x114` | 0 | 3 |
| Event Types | `0x118` | 0 | 3 |
| Track Description | `0x11c` | 0 | 3 |
| Year | `0x124` | 13 | 3 |
| Sun Angle(DEG) | `0x128` | 1 | 3 |
| Track Surface | `0x12c` | 0 | 3 |
| Track Group | `0x130` | 0 | 3 |
| PreRace Allowed (true/false) | `0x134` | 2 | 3 |
| Max AI participants | `0x138` | 3 | 3 |
| Class | `0x13c` | 0 | 3 |
| DirtSkidmarks | `0x164` | 0 | 3 |
| DrySkidmarks | `0x168` | 0 | 3 |
| GrassSkidmarks | `0x16c` | 0 | 3 |
| GravelSkidmarks | `0x170` | 0 | 3 |
| SandSkidmarks | `0x174` | 0 | 3 |
| GravelDustParticles | `0x178` | 0 | 3 |
| GravelChunkParticles | `0x17c` | 0 | 3 |
| GrassParticles | `0x180` | 0 | 3 |
| AutograssMaterial | `0x184` | 0 | 3 |
| AutograssDensities | `0x188` | 0 | 3 |
| AutograssHeights | `0x18c` | 0 | 3 |
| AI Grip | `0x190` | 10 | 3 |
| AI drift score min | `0x198` | 3 | 3 |
| AI drift score max | `0x19c` | 3 | 3 |
| Rolling Start | `0x1a0` | 2 | 3 |
| Setup group | `0x1a4` | 0 | 3 |
| ZoneName | `0x1a8` | 0 | 3 |
| Post race position | `0x1ac` | 16 | 3 |
| Post race orientation | `0x1b8` | 16 | 3 |
| Post race steering | `0x1c4` | 10 | 3 |
| Time Attack duration short | `0x1c8` | 3 | 3 |
| Time Attack duration medium | `0x1cc` | 3 | 3 |
| Time Attack duration long | `0x1d0` | 3 | 3 |

The numeric type codes are retained as reflection evidence; this contract does
not invent a broader type system from those numbers.

## Constructor-visible defaults

`FUN_0049b9c0` directly establishes the following reflected defaults:

| Field | Default |
|---|---:|
| LeaderboardID | `0xffffffff` |
| Length | `0xffffffff` |
| Year | 0 |
| Sun Angle(DEG) | 0 |
| PreRace Allowed | 0 |
| Max AI participants | 15 |
| AI Grip | `1.0f` |
| AI drift score min | 400 |
| AI drift score max | 4000 |
| Rolling Start | 0 |
| Post race position | `(0,0,0)` |
| Post race orientation | `(0,0,0)` |
| Post race steering | `0.0f` |
| Time Attack duration short | 5 |
| Time Attack duration medium | 10 |
| Time Attack duration long | 20 |

The constructor also performs many raw internal dword writes and initializes
multiple members through helper calls. The runtime contract preserves those
writes and helper offsets without assigning an unproven container/string type
to the helpers.

## Lifecycle

The recovered entry points are:

- constructor: `FUN_0049b9c0`;
- destructor wrapper: `FUN_0049bf00`;
- destructor body: `FUN_0049bd10`;
- load path: `FUN_0049c050`.

`FUN_0049bd10` tears down the member storage before continuing into
`BPersistent` destruction. `FUN_0049c050` is recorded as the source-backed
load entry point; its higher-level resource/list semantics are not promoted by
this first structural contract.

## Runtime implementation

`src/track/track_details_runtime.py` exposes:

- class/RTTI/vtable identity;
- exact `0x1d4` allocation size and allocator call path;
- all 44 direct reflected fields;
- exact direct constructor writes;
- reflected constructor defaults;
- raw helper-initialized member offsets;
- constructor/destructor/load entry-point identities.

The boundary remains structural. Track-list ownership, selection rules,
resource lookup behavior, and meanings of unreflected/internal storage require
additional call-site or loader analysis.
