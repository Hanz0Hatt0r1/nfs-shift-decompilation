# Phase 257 — Trackside Camera selection

Phase 257 reconstructs the deterministic reduction in FUN_008119b0.

## Runtime behavior

TrackCameraMan scans the Trackside Cams collection in index order. For each entry it calls FUN_008154d0(camera, query) and keeps the smallest scalar returned by that call.

Important details:

- the initial best score is `FLT_MAX`;
- the initial selected index is `-1`;
- indices are zero-based collection indices;
- a score strictly below `0.0` becomes the current winner and terminates the scan immediately;
- an empty collection therefore returns `-1`;
- `FUN_008154d0` itself is not reimplemented here because its nested vehicle/area dependencies are still partially unresolved.

`trackside_camera_selection_runtime.py` exposes the reduction as `select_min_score()` and keeps the score semantically neutral instead of calling it distance/proximity.

## Runtime context

FUN_00812050 uses this selection path after obtaining a query position and, when the relevant camera state permits, passes the selected index to FUN_0080e1b0 as the active Trackside Camera.

This establishes an important boundary: camera *selection* is now reconstructed separately from the still-unresolved score calculation.

## CLI

```json
{
  "scores": [4.0, 2.0, -0.5, -1.0],
  "query": {"opaque": true}
}
```

```bash
python shift_importer.py trackside-camera-selection input.json output.json
```

## Limits

No camera transform, look-at, FOV, shake, spline geometry or physical distance function is inferred in this phase. Renderer and RENDER.bff remain untouched.