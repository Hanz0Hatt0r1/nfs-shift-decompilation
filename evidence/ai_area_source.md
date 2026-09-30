# SHIFT AIArea path-owner fields: source and PE evidence

The live-memory track analyzer has historically exposed the relevant subset of
this object as `Incident.PathOwner`. The retail class that owns those reflected
fields is `AIArea`. This note records the evidence used to make its runtime
identity concrete while retaining the legacy output name.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Registration and reflection

`FUN_00a83e10` registers class `AIArea`. Its RTTI descriptor begins at
`0x00c0d588`, derives from `AIAreaBase`, and binds reflection metadata
through `PTR_PTR_00b8afa8` / `DAT_00b8afac`.

`FUN_006c67e0` builds the same metadata table used by the analyzer. Among the
fields it reflects are:

| Offset | Reflected name | Analyzer field |
|---:|---|---|
| `+0x30` | `incident pos` | `incident_x/y/z` |
| `+0xd4` | `area type` | `area` |
| `+0xd8` | `path pointer` | `path` |
| `+0xdc` | `CentrePos` | `cx/cy/cz` |
| `+0xe8` | `Radius` | `radius` |
| `+0xf0` | `active` | `active` |
| `+0xf4` | `active incident` | `active_incident` |
| `+0xf8` | `roaming characters` | `roaming` |
| `+0x100` | `incident path dist` | `incident_path_dist` |
| `+0x104` | `incident timer` | `incident_timer` |
| `+0x108` | `interest level` | `interest_level` |
| `+0x10c` | `min spacing` | `min_spacing` |
| `+0x110` | `TrackDist` | `track_dist` |
| `+0x114` | `RaceFlag` | `race_flag` |
| `+0x118` | `AreaIndex` | `area_index` |
| `+0x11c` | `nMarshals` | `n_marshals` |
| `+0x120` | `nFlagMarshals` | `n_flag_marshals` |

The reflection builder also exposes additional AIArea collections that the
current narrow path-owner profile does not decode.

## Constructor and vtable

`FUN_006c3a20` initializes the BRefCount-derived object and writes
`PTR_FUN_00afc048`.

The retail PE independently contains the virtual RTTI getter at
`0x006c3c30`:

```text
b8 88 d5 c0 00    mov eax,0x00c0d588
c3                ret
```

The aligned `.rdata` vtable whose RTTI slot points to this getter starts at
`0x00afc048`, matching the constructor.

## Analyzer boundary

`analyze_track_paths.py` therefore requires `0x00afc048` for the legacy
`Incident.PathOwner` profile. An object with the same field shape but another
executable SHIFT vtable is rejected.

The output name `Incident.PathOwner` and `incident_pathowner.csv` are kept
for compatibility with existing capture-analysis scripts. Their concrete owner
class identity is now `AIArea`.
