# Phase 357 — PhysicsSystem / PhysicsParticipant runtime reconstruction

This phase deliberately leaves the renderer unchanged and opens the next non-rendering
runtime subsystem: the retail PhysX 2.x integration and vehicle physics participant
spawn path.

## Evidence source

Primary source: `SHIFT.exe.c` recovered from the supplied retail `SHIFT.exe` image.

Local source fingerprint used during reconstruction:

`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

Recovered routines:

- `FUN_0070fae0` — Physics Manager constructor
- `FUN_0070f580` — Physics Manager shutdown/destructor
- `FUN_00710870` — Physics asset database guard/getter
- `FUN_007506b0` — PhysX SDK, scene and asset initialization
- `FUN_00750620` — auxiliary physics object lifecycle
- `FUN_00750080` — collision-stream (.csm) loader
- `FUN_0074d290` / `FUN_0074d310` / `FUN_0074d400` — PhysicsTweaker registration/load
- `FUN_0074d640` — PhysicsParticipant config defaults
- `FUN_0074ddc3` — participant spawn path
- `FUN_0074e1a0` / `FUN_0074e340` — participant registration/reinitialization

## New contracts

### SHIFT.PhysicsManagerRuntime/1

The constructor records the concrete retail object name `Physics Manager`, initializes
six array-like fields at byte offsets `0x370..0x384`, and seeds path strings including
`Tracks/_Data/`, `Tracks/`, `vehicles/`, `Physics/`, an opaque global string at
`DAT_00b04554`, and the derived `Drivers/` path.

Shutdown destroys those six fields in reverse order and releases the allocator through
the observed virtual-table offset `0x1c`.

### SHIFT.PhysicsSystemRuntime/1

The startup contract records the exact PhysX setup observed in `FUN_007506b0`:

- PhysX SDK version `0x02080100`
- same version requested from `NxGetCookingLib`
- allocator allocation size `0xc0`
- four 4-byte error/callback objects with source-visible vtable symbols
- SDK parameter writes for IDs `1` and `8`
- exact filter-relation loops over groups `0x1d` and `0x1e`
- scene callback installation through vtable offsets `0x18c`, `0x194`, `0x19c`
- primary `.csm` load through `FUN_00750080(..., 1)`
- optional secondary stream through `FUN_00750080(..., 0)`
- `PhysicsTweaker.xml`, dynamic object XML, `triggers.xml`, AIW and TSL path construction

The module does not assign semantic names to opaque PhysX scene-descriptor words. Raw
values from `FUN_0074e460` remain evidence-only fields.

### SHIFT.PhysicsTweakerRuntime/1

The recovered boundary is preserved as a lazy registry plus XML load:

`DAT_00c13380 bit 0 -> DAT_00c13280 -> FUN_0074c840 -> FUN_00640150(..., Physics DB, 1)`

The target object's virtual load/finish calls remain represented by offsets `0x20` and
`0x24` rather than guessed C++ method names.

### SHIFT.PhysicsParticipantRuntime/1

`FUN_0074ddc3` is represented as a deterministic five-mode state machine:

| Mode | Runtime evidence |
|---:|---|
| 0 | `FUN_0079c920 -> FUN_007927c0 -> FUN_00792920` |
| 1 | `FUN_0079c970 -> FUN_007927c0 -> FUN_00792920` |
| 2 | `FUN_0079c8f0 -> FUN_007927c0 -> FUN_00792920` |
| 3 | slot lookup -> `FUN_00793a80`, then slot-state/event helpers |
| 4 | literal transform from config `+0x28..+0x3c` -> `FUN_007927c0` |

The zero-X/Z spawn diagnostic and participant-ready byte at `+0x4e` are retained as
observable behavior. Numeric mode meanings and helper semantics remain unresolved.

## Collision-stream boundary

`FUN_00750080` verifies the CSM stream version against `0x0afb` and iterates records
through `FUN_0074e880`. The binary record grammar is not promoted in this phase:
the code records the loader boundary and exact version/error behavior without inventing
collision-record field names.

## Explicit unknowns

1. semantic names of the `FUN_0074e460` scene descriptor fields;
2. semantic meaning of PhysX parameter IDs `1` and `8` in this title;
3. full binary record grammar behind `FUN_0074e880`;
4. transform conventions returned by `FUN_0079c920`, `FUN_0079c970`,
   `FUN_0079c8f0` and `FUN_0079c9c0`;
5. higher-level meaning of participant modes `0..4`;
6. runtime semantics of AIW, TSL, dynamic object XML and several participant helpers.

## Verification

`tests/test_physics_system_runtime.py` covers exact version constants, mission-path
construction, collision-filter loop cardinality, manager path/destructor evidence,
opaque scene-descriptor handling, PhysicsTweaker load offsets, participant config
defaults and all five observed participant modes.

All nine tests pass locally.

## Next non-render target

Continue down the physics call graph: finish the participant state helpers, recover the
record consumer `FUN_0074e880`, then follow `CarPhysicsDetails::Load` and
`HighDetailVehicle::IntegrateDriveline`. Renderer changes remain out of scope for
this track.
