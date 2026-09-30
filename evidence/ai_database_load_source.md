# SHIFT AIDatabase AIW load and section-generation lifecycle

This note extends the structural AIDatabase recovery with the retail AIW load
control flow from `FUN_00720190` and its source/meta section fallback path.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## AIW load entry

`FUN_00720190(AIDatabase*)` begins by calling the constructor/reset helper
`FUN_00715690`, then applies a second load-specific preset. Important
load-time values include:

| Offset / reflected field | Load preset |
|---|---:|
| `+0x10` / Garage Depth | `-1.0f` |
| `+0x50` / Worst Adjust | `0.5f` |
| `+0x54` / Mid Adjust | `1.0f` |
| `+0x58` / Best Adjust | approximately `1.3f` |
| `+0x78` / Lap Length | `3.0f` |
| `+0x7c` / Sector 1 Length | `1.0f` |
| `+0x80` / Sector 2 Length | `2.0f` |
| `+0x68` | waypoint count = 0 |
| `+0x70` / Waypoints | null |
| `+0x12f8` | load state = 1 |

The function also clears several byte-sized control fields. The runtime
contract retains native write widths instead of widening them.

## Database path and fail-closed load path

The path/string object is at `+0x44`. When byte `+0x48` is zero,
`FUN_00720190` copies global `DAT_00c13420` into it.

The load order is:

1. `FUN_0071e3b0` cleanup/reset thunk;
2. `FUN_007200b0` persistent/reflection-backed load attempt;
3. if that returns false, `FUN_0074d140` attempts the fallback file open;
4. if the fallback open fails, the function logs `Unable to open AIW %s`,
   writes zero to `+0x12f8`, invokes cleanup again, and stops the successful
   post-load path;
5. after a successful fallback open it invokes cleanup and, when the recovered
   local resource flag is nonzero, calls `FUN_007490f0(1)`.

The runtime contract exposes these branches without implementing either loader.

## Waypoint storage

The loaded waypoint array is explicit:

| Member | Offset |
|---|---:|
| waypoint count | `+0x68` |
| waypoint pointer | `+0x70` |
| waypoint record stride | `0x1bc` |
| per-record classification field | `+0x6c` |
| per-record next-link field | `+0x180` |

After loading, `FUN_00720190` performs three whole-array passes in fixed
order:

1. `FUN_007ada70(waypoint)`;
2. `FUN_007ad940(waypoint)`;
3. `FUN_007acef0(waypoint, waypoint+0x180)`.

It then scans `waypoint+0x6c` and counts zero-valued entries into database
`+0x6c`. No stronger meaning is assigned to this classification field yet.

## External versus generated meta sections

At the end of the load path, global `DAT_00c13424` is passed to
`FUN_0071fd60`. That helper parses a separate file and, on success, fills the
AIDatabase derived/meta array at `+0x139c/+0x13a0`.

The result is inverted into byte `+0x13a4`:

- external meta file loaded successfully → `+0x13a4 = 0`;
- external meta file missing/failed → `+0x13a4 = 1`.

This resolves the role of the byte previously recorded only as a rebuild/mode
flag.

`FUN_0071f850` later builds `0x18`-stride source-section records at
`+0x1394/+0x1398`. When it reaches the requested range, it calls
`FUN_0071dc90`; when `+0x13a4 != 0`, that routine generates one
`0x14`-stride derived/meta record per source record.

The generation path is independently anchored by the retail diagnostic:

`Invalid meta section %u %.0fm:%.0fm for track %s - no corners/straights contained!`

from `.\Source\AI\ai_db.cpp`.

## Runtime implementation

`src/ai/ai_database_load_runtime.py` exposes:

- exact load-specific preset writes;
- database-path offsets and source globals;
- persistent/fallback/failure branch trace;
- waypoint pointer/count/stride and ordered post-load passes;
- external-meta success → generated-meta flag inversion;
- source-section and generated-meta storage topology.

This is still a control/storage contract. It does not parse AIW bytes, assign
full waypoint record semantics, or reproduce the geometric/path calculations
inside the called helpers.
