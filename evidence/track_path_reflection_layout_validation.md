# SHIFT track/path reflection layout validation

This note records the automated cross-check between the live-memory track/path
analyzer layouts and the reflection metadata recovered from the retail
`SHIFT.exe.c`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Validator

`tools/shift_live_dump/verify_track_path_reflection_layouts.py` combines:

1. the generic RTTI registry extractor;
2. the generic `FUN_0063a280` reflection field extractor;
3. the actual layout dictionaries loaded from
   `analyze_track_paths.py`.

Each binding requires the recovered reflected field name, numeric reflection
type code, and source byte offset to agree with the analyzer field's base
offset. A mismatch exits non-zero.

For reflected vector-like fields the validator compares the reflected base
offset with the analyzer's first component only. It does not infer vector width
or component count from an otherwise undocumented numeric reflection type code.

## Current coverage

The verifier currently checks 62 reflected base anchors:

| Retail class | Analyzer spec | Bindings |
|---|---|---:|
| `AIPathInfo` | `PATH` | 8 |
| `AIArea` | `INCIDENT` | 17 |
| `AISegmentPath` | `SEGMENT` | 10 |
| `AIPathNode` | `SEGMENT_NODE` | 7 |
| `AIPolylinePath` | `POLY` | 7 |
| `AIPolyPathNode` | `POLY_NODE` | 3 |
| `Knot` | `KNOT` | 6 |
| `AISpline` | `SPLINE` | 4 |

The `AIArea` check intentionally covers the fields decoded by the legacy
`Incident.PathOwner` analyzer profile, not every reflected `AIArea`
collection.

## Usage

```bash
python3 tools/shift_live_dump/verify_track_path_reflection_layouts.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --analyzer tools/shift_live_dump/analyze_track_paths.py \
  --json-out /tmp/track-layout-verification.json
```

A single class can be checked while developing a layout change:

```bash
python3 tools/shift_live_dump/verify_track_path_reflection_layouts.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --class-name AISpline
```

## Boundary

This verifier establishes that the analyzer's decoded field bases agree with
the game's reflection metadata. It does not by itself prove ownership,
allocation stride, array count-prefix conventions, pointer targets, or runtime
liveness. Those remain covered by constructor/factory evidence and the
snapshot validators.
