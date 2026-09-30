# SHIFT AIPathInfo: source and PE evidence

The live-memory track analyzer has historically exposed this structure under the
short profile name `Path`. The retail type behind that profile is
`AIPathInfo`. This note records the source and PE evidence used to make its
identity concrete while retaining the legacy output name for compatibility.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Registration and reflection

`FUN_00a83ec0` registers the class name `AIPathInfo`. Its RTTI descriptor
starts at `0x00c0d5a4`, and the registration associates reflection metadata
through `PTR_PTR_00b8afd0` / `DAT_00b8afd4`.

`FUN_006c6f60` builds that reflection table:

| Offset | Reflected name | Analyzer field |
|---:|---|---|
| `+0x10` | `tangent` | `tx`, `ty` |
| `+0x18` | `outside` | `outside` |
| `+0x1c` | `centreDist` | `centre` |
| `+0x20` | `StartNode` | `start_node` |
| `+0x24` | `pathSide` | `side` |
| `+0x25` | `pathEndReached` | `end` |
| `+0x26` | `spawnedge` | `spawn` |
| `+0x27` | `trackEdge` | `edge` |

These are the exact offsets already used by the analyzer's legacy `PATH`
layout.

## Constructor and vtable

`FUN_006bc3a0` initializes the BRefCount header, then writes
`PTR_FUN_00afb150`. It also initializes `StartNode` at `+0x20` and the
first flag byte at `+0x24`.

The retail PE independently confirms the class identity. At
`0x006bc3e0` is the virtual RTTI getter:

```text
b8 a4 d5 c0 00    mov eax,0x00c0d5a4
c3                ret
```

The aligned `.rdata` vtable whose second slot points to that getter starts at
`0x00afb150`. This matches the constructor exactly.

## Analyzer boundary

`analyze_track_paths.py` therefore requires `0x00afb150` for the legacy
`Path` profile. A structurally compatible object with any other executable
SHIFT vtable is rejected.

The public output names remain `Path`, `path.csv`, `path_root_targets.csv`,
and related historical names so existing capture-analysis scripts do not need a
format migration. Their concrete retail class identity is now `AIPathInfo`.

This is distinct from the abstract/reflected `AIPath` registration at
`0x00c0d698` and from the concrete `AIPolylinePath` /
`AISegmentPath` containers.
