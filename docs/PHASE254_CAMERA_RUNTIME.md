# Phase 254 — Camera configuration and TrackCameraMan runtime

Phase 254 reconstructs camera configuration boundaries visible in retail SHIFT.exe without inventing camera behavior.

## Loader contract

FUN_00811160 establishes the global configuration chain:

1. Cameras\\CameraConfig.xml
2. Tracks\\CameraConfig.xml when no track-specific name is selected, otherwise Tracks\\<track>\\CameraConfig.xml

FUN_008127c0 resolves the active camera definition. A named definition may be attempted using the supplied string first; when that attempt fails, the source formats Cameras\\%s.xml. The routine then always loads Cameras\\localCams.xml.

`build_camera_load_plan()` models these as ordered candidates and does not decide file existence.

## XML object boundary

FUN_00812650 registers three TrackCameraMan groups:

| XML group | member offset | loader / serializer |
|---|---:|---|
| Trackside Cams | +0x14 | FUN_00812260 / FUN_00816d30 |
| Splines | +0x48 | FUN_00812450 / FUN_008117c0 |
| Areas | +0x7C | FUN_00812550 / FUN_00811d40 |

FUN_008117c0 and FUN_00811d40 enumerate an `elements` container, read each element's `class` and `id`, then use the nested `data` boundary to construct the runtime object.

`parse_camera_xml()` mirrors that boundary and preserves unknown attributes/data as raw XML-derived values.

## Registered property evidence

FUN_008156b0 registers the static-camera data surface: Name, Pos, QuatOri, FOV, Type, NearZ/FarZ, Target, LookAt, target/look-at offsets, proximity shake, screen velocity, sound-effect, LOD and userdata fields, plus ActiveAreas.

FUN_0081ebc0 registers the tracking/spline data surface: MovementRate, TrackingRate, SplineID, TargetSplineID, AutoZoom/StaticDirection, spline chase directions, tracking lag/error controls, SplinesRatio, synchronization and spline-end callbacks.

FUN_0081e780 registers Centre/Radius for the first area form; FUN_0081e880 registers XForm/Dimensions for the second area form.

The executable's numeric type_code and structure offset are retained as evidence records. They are not promoted into a new semantic ABI.

## Explicit limits

This phase does not resolve class inheritance, implement TrackCameraMan selection logic, synthesize look-at matrices or shake/FOV behavior, or modify renderer code and RENDER.bff.

Evidence sources are the recovered functions FUN_00811160, FUN_008117c0, FUN_00811d40, FUN_00812650, FUN_008127c0, FUN_008156b0, FUN_0081ebc0, FUN_0081e780 and FUN_0081e880.