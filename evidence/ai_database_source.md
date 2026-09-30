# SHIFT AIDatabase: source, PE, layout, and lifecycle evidence

This note records the first source-backed AI subsystem runtime contract promoted
from the generic RTTI/reflection candidate pipeline.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Class identity

`FUN_00a89b80` registers `AIDatabase` with descriptor
`DAT_00c10f58`, parent `BPersistent`, and reflection metadata
`DAT_00b8d070`.

`FUN_0071da20` constructs the object and writes
`PTR_FUN_00b04c88`. The generic RTTI/PE pipeline independently resolves the
same class to unique vtable `0x00b04c88`.

The retail startup stub at PE `0x00a89c70` loads
`ECX = 0x00c10f68` and calls `0x0071da20`. The next startup call registers
cleanup. This proves that the retail AIDatabase used by the observed call sites
is a statically allocated singleton at `0x00c10f68`, rather than an inferred
heap allocation.

## Direct reflected layout

`FUN_0071b530` emits 30 direct fields:

| Field | Offset | Type code | Flags |
|---|---:|---:|---:|
| Garage Depth | `0x10` | 10 | 3 |
| Groove Width | `0x2c` | 10 | 3 |
| Wet Groove Width | `0x30` | 10 | 3 |
| Worst Adjust | `0x50` | 10 | 3 |
| Mid Adjust | `0x54` | 10 | 3 |
| Best Adjust | `0x58` | 10 | 3 |
| Qual Ratio | `0x5c` | 10 | 3 |
| Race Ratio | `0x60` | 10 | 3 |
| Left Handed Pits | `0x64` | 32 | 3 |
| Waypoints | `0x70` | 6 | 2 |
| Lap Length | `0x78` | 10 | 3 |
| Sector 1 Length | `0x7c` | 10 | 3 |
| Sector 2 Length | `0x80` | 10 | 3 |
| Fuel Use | `0x8c` | 10 | 3 |
| TELEPORT | `0x98` | 6 | 2 |
| GRID | `0x9c` | 6 | 2 |
| PITS | `0xa0` | 6 | 2 |
| Pit Lanes | `0xac` | 13 | 3 |
| Starting Grid | `0xb0` | 13 | 3 |
| Pit Spots | `0xb4` | 13 | 3 |
| Garage Spots | `0xb8` | 13 | 3 |
| Track State | `0x1304` | 13 | 3 |
| Dry Line Time | `0x130c` | 10 | 3 |
| Wet Line Time | `0x1310` | 10 | 3 |
| Worst Time | `0x1320` | 10 | 3 |
| Mid Time | `0x1324` | 10 | 3 |
| Best Time | `0x1328` | 10 | 3 |
| Cheat Delta Worst | `0x1330` | 10 | 3 |
| Cheat Delta Mid | `0x1334` | 10 | 3 |
| Cheat Delta Best | `0x1338` | 10 | 3 |

The three reflected collection fields with explicit serializer hooks are:

- `GRID +0x9c`: `FUN_00715fc0` / `FUN_00716100`;
- `TELEPORT +0x98`: `FUN_00716850` / `FUN_007162a0`;
- `PITS +0xa0`: `FUN_00716440` / `FUN_00716610`.

No semantic role is assigned to either member of each callback pair beyond its
association with that reflected field.

## Constructor defaults

Before the common reset, `FUN_0071da20` explicitly writes null pointers at
`+0x1394` and `+0x139c`, so both owned record-array pointers are initialized
independently of their counts.

`FUN_00715690`, called by `FUN_0071da20`, supplies the remaining reset/default state.
Among reflected fields this establishes:

| Field | Initial value |
|---|---:|
| Groove Width | `6.0f` |
| Wet Groove Width | `4.3125f` |
| Qual Ratio | approximately `1.005f` |
| Race Ratio | approximately `0.99f` |
| Waypoints | null |
| Fuel Use | zero |
| Pit Lanes | 1 |
| Starting Grid | 104 |
| Pit Spots | 52 |
| Garage Spots | 3 |
| Dry Line Time | `FLT_MAX` |
| Wet Line Time | `FLT_MAX` |

The runtime contract keeps all constructor writes in raw width/value form as
well, including unreflected members. This matters for byte writes such as
`+0x48`, `+0x12fc`, `+0x13a4`, which must not be silently widened.

## Owned record arrays

Two late object members form an explicit source/derived record lifecycle:

| Member | Offset | Record stride |
|---|---:|---:|
| source-record pointer | `+0x1394` | `0x18` |
| source-record count | `+0x1398` | — |
| derived/meta-record pointer | `+0x139c` | `0x14` |
| derived/meta-record count | `+0x13a0` | — |
| rebuild/mode byte | `+0x13a4` | — |

`FUN_0071dbf0` resets source-record `+0x14` indices to `0xffffffff`
and, when the mode byte is nonzero, destroys/frees the existing `0x14`-stride
derived array.

`FUN_0071dc90` rebuilds one derived record per source record in that mode.
It writes the source/derived indices and obtains the two floats at derived
`+0x0c/+0x10` through recovered helper calls. The implementation records
these as range-start/range-end storage only; it does not assign a stronger
gameplay name to the helper results.

The source itself logs invalid generated meta sections from
`.\Source\AI\ai_db.cpp`, which anchors this lifecycle to the recovered AI
database subsystem.

## Runtime implementation

`src/ai/ai_database_runtime.py` now exposes:

- concrete class/RTTI/vtable/singleton identity;
- all 30 direct reflected fields;
- exact constructor writes with preserved write width and decoded f32 constants;
- reflected-field defaults when a constructor write exists;
- source/meta record pointer/count/stride lifecycle.

This is a structural runtime contract, not a complete AIDatabase implementation.
Object ownership outside the proven singleton, meanings of unreflected members,
helper-call semantics, path-generation algorithms, and AI behavior remain
outside this evidence boundary.
