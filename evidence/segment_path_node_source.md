# SHIFT AISegmentPath node array: source and PE evidence

The retail executable has two distinct path-node layouts. `AIPolyPathNode`
belongs to `AIPolylinePath` and has 0x24-byte elements. The array loaded by
`AISegmentPath` instead contains `AIPathNode` elements of 0x38 bytes. This
distinction matters when following a captured `AISegmentPath.array` pointer:
the 0x24-byte polyline decoder must not be applied to it.

## Source identity and allocation

The evidence is from `SHIFT.exe` SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
and its `SHIFT.exe.c` decompilation SHA-256
`512753a5f91898885263c91664a3d3a5f89c402a00760ee9`.

`FUN_006d8490` (`SHIFT.exe.c:650368`, PE `0x006d8490`) is the concrete path factory. When given the `AISegmentPath` RTTI object at `0x00c0d668`, it allocates `0x38` bytes and calls `FUN_006cfe70`. That constructor writes vtable `0x00afc930` after initializing the recovered `AISegmentPath` fields. This also disambiguates `FUN_006d0fe0` / `0x00afca70`: the latter belongs to the later `AIMarker` descriptor, not `AISegmentPath`.

`FUN_006cfc10` (`SHIFT.exe.c:644589`, PE `0x006cfc10`) reads the serialized
element count, writes it to `AISegmentPath+0x10`, allocates `count * 0x38 + 4`
bytes, writes the count into the four-byte prefix, and stores the first
element address at `AISegmentPath+0x18`. Each element is initialized with
vtable `0x00afbf60`; the loop advances by `0x38`. The allocation size,
prefix, vtable and stride are visible directly in PE instructions
`0x006cfc35-0x006cfc38`, `0x006cfc68-0x006cfc8f`, and
`0x006cfc8f-0x006cfce0`.

The class registration at `FUN_00a846a0` (`SHIFT.exe.c:1415270`) names
`AIPathNode`. `FUN_006d0d10` (`SHIFT.exe.c:645220`, PE `0x006d0d10`) builds
its reflection fields; the PE string table at `0x00afca40-0x00afca5a`
contains `pos2`, `pos1`, and `AIPathNode`.

## Reflected element fields

| Element offset | Reflected name | Type visible in code |
|---:|---|---|
| `+0x10` | `pos1` | 2D vector |
| `+0x18` | `pos2` | 2D vector |
| `+0x20` | `normal` | 2D vector |
| `+0x28` | `height1` | float |
| `+0x2c` | `height2` | float |
| `+0x30` | `dist` | float |
| `+0x34` | `distributionratio` | float |

These offsets are passed to the reflection builder in `FUN_006d0d10` and
match PE calls at `0x006d0d3e`, `0x006d0d80`, `0x006d0dc2`,
`0x006d0e02`, `0x006d0e44`, and `0x006d0e86` (with the final field following
at `+0x34`). `FUN_006ce4e0` also reads the two position pairs and heights
from an element while deriving its center. `FUN_006cf8e0` compares the
`+0x30` distance with the current path distance at `AISegmentPath+0x2c`.

## Project use and evidence boundary

`tools/shift_live_dump/analyze_track_paths.py` now validates captured
`AISegmentPath.array` pointers against the count prefix, 0x38 stride and
`0x00afbf60` vtable. It exports complete arrays from the reference snapshot
to `aisegmentpath_nodes.csv` only when the count prefix and the complete
`AIPathNode` vtable sequence agree across every supplied snapshot, with owner
and element addresses plus the reflected fields. Regressions cover adjacent
elements and reject incomplete cross-snapshot evidence.

The fields' names and byte layout are source-backed. Their gameplay meaning,
whether `dist` is always monotonic, and identity of a particular live array
remain capture questions. A reduced capture lacking the target array cannot
establish that no such array exists in the process.
