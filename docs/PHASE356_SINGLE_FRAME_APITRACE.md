# Phase 356 — single-frame apitrace extraction

Phase 356 adds a safe handoff path for studying one real frame from the multi-gigabyte SHIFT apitrace capture.

## Tool

`tools/extract_apitrace_single_frame.py` writes a compact `single_frame.trace` and `manifest.json` without creating a permanent text dump of the original trace.

### Recommended: automatic BMW frame selection

```bash
python tools/extract_apitrace_single_frame.py \
  /path/to/shift.trace \
  ./single-frame \
  --auto-bmw \
  --target-runtime-geometry /path/to/bmw_m3_e36_runtime_geometry.json
```

The scanner finds frame boundaries at D3D9 `Present`/`PresentEx`, scores frames by BMW target primitive coverage, and trims the selected frame with `apitrace trim --auto --calls=start-end`.

### Known frame number

```bash
python tools/extract_apitrace_single_frame.py \
  /path/to/shift.trace \
  ./single-frame \
  --frame 123
```

This uses apitrace's frame-aware automatic trim mode (`--frames=123/frame`).

### Known draw-call

```bash
python tools/extract_apitrace_single_frame.py \
  /path/to/shift.trace \
  ./single-frame \
  --draw-call 456789
```

The tool locates the exact containing frame and trims that frame rather than assuming that the draw belongs to the first BMW candidate frame.

## Output

```text
single-frame/
  single_frame.trace
  manifest.json
```

`manifest.json` records the selected frame index, original call range, target draw calls and exact trim command. The original trace remains untouched.

## Evidence boundary

The tool proves only the selection and creation of a single-frame trace. It does not claim that the resulting trace contains all historical resource creation calls; `--auto` asks apitrace to include replay dependencies, and the resulting trace should therefore be treated as the analysis artifact rather than as a raw byte-for-byte slice of the source trace.

The resulting `.trace` is the preferred artifact to upload for independent runtime-state inspection. If the trace still contains more data than practical for transfer, `manifest.json` remains useful for reproducing the same selection locally.
