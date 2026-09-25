# Phase 255 — TrackCameraMan spline reload semantics

Phase 255 reconstructs the reference-maintenance logic inside FUN_00811ae0. This is the next runtime layer after Phase 254's CameraConfig file and XML object boundary.

## Source-observed reload sequence

Before the XML load, the runtime saves:

- old Trackside Cams count from this+0x38 into this+0xc0
- old Splines count from this+0x6c into this+0xc4

After the XML payload is ingested, the runtime:

1. marks every newly appended spline record with the opaque runtime field at object offset +0x24;
2. checks pre-existing tracking cameras and sets SplineID or TargetSplineID to -1 when the reference is outside the new spline count;
3. walks newly appended tracking cameras, adds the old spline count to each non-negative SplineID and TargetSplineID, and then invalidates the value if it falls outside the new spline array;
4. optionally invokes the TrackCameraMan completion callback.

The tracking-camera fields are the same fields registered by FUN_0081ebc0 at +0xf8 and +0xfc.

## IR contract

`camera_spline_reload_runtime.py` models the deterministic reference maintenance without pretending to know the meaning of the opaque object marker at field index 0x3b.

The input distinguishes existing cameras from newly loaded cameras because the source applies different rules to the two groups.

Negative references are normalized to -1 and remain unset. The post-load spline count may not be smaller than the pre-load count.

## CLI

Input example:

```json
{
  "old_spline_count": 12,
  "new_spline_count": 16,
  "existing_cameras": [{"SplineID": 3, "TargetSplineID": 15}],
  "newly_loaded_cameras": [{"SplineID": 0, "TargetSplineID": 2}]
}
```

Run:

    python shift_importer.py camera-spline-rebase input.json output.json

## Limits

This phase does not implement spline geometry, camera movement, camera selection, class inheritance or camera rendering. It only reproduces the proven SplineID/TargetSplineID maintenance around a TrackCameraMan reload.

Renderer and RENDER.bff remain untouched.