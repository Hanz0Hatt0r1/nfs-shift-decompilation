# Phase 258 — Camera data default state

Phase 258 reconstructs the default data templates initialized before camera XML overrides them.

## Static camera data

FUN_00813180 initializes the `CStaticCamData` template used by FUN_00813300.

Proven registered defaults include:

| Field | Offset | Default |
|---|---:|---|
| Pos | +0x20 | (0, 0, 0) |
| QuatOri | +0x10 | four zero floats |
| FOV | +0x64 | raw f32 `0x3f490fdb` |
| Type | +0x68 | 1 |
| NearZ | +0x6c | 1.0f |
| FarZ | +0x70 | 750.0f |
| Target | +0x78 | 6 |
| LookAt | +0x80 | 6 |
| TargetOffset | +0x84 | (0, 0, 0) |
| LookAtOffset | +0x90 | (0, 0, 0) |
| ProximityShakeFrequency | +0x9c | 12.0f |
| ProximityShakeMagnitude | +0xa0 | 0.0f |
| ProximityShakeMinDistance | +0xa4 | 4.0f |
| ProximityShakeMaxDistance | +0xa8 | 20.0f |
| ProximityShakeMinSpeed | +0xac | 20.0f |
| ProximityShakeMaxSpeed | +0xb0 | 40.0f |
| ShakeFrequencyMin | +0xb4 | 0.0f |
| ShakeFrequency | +0xb8 | 12.0f |
| ShakeMagnitudeMin | +0xbc | 0.0f |
| ShakeMagnitude | +0xc0 | 0.0f |
| SoundEffect | +0xcc | empty |
| LODDistanceMultiplier | +0xd0 | 1.0f |
| OverridedBy | +0xd4 | empty |
| UserDataName | +0xdc | empty |
| UserDataValue | +0xe0 | 0.0f |
| ActiveAreas | +0x2c | empty |

The `ShakeScreenVelocityMin/ShakeFrequencyMin` and `ShakeScreenVelocity/ShakeFrequency` aliases are preserved because the executable registers them at the same storage offsets.

`QuatOri` is intentionally kept as four zeros. The initializer evidence does not justify inserting an identity quaternion.

## Tracking camera data

FUN_0081f8c0 derives the tracking template from the static template and initializes the additional FUN_0081ebc0 fields:

| Field | Offset | Default |
|---|---:|---|
| MovementRate | +0xf0 | 0.0f |
| TrackingRate | +0xf4 | 0.0f |
| SplineID | +0xf8 | -1 |
| TargetSplineID | +0xfc | -1 |
| bAutoZoom | +0x100 | false |
| bStaticDirection | +0x101 | false |
| SplineChaseDir | +0x104 | 0.0f |
| TargetSplineChaseDir | +0x108 | 0.0f |
| TrackingLag | +0x128 | 0.0f |
| TrackingLagSmoothening | +0x12c | 0.8f |
| TrackingErrorFrequency | +0x130 | 2.0f |
| TrackingErrorCorrectionSpeed | +0x134 | 1.0f |
| TrackingErrorMagnitude | +0x138 | 0.0f |
| SplinesRatio | +0x13c | 1.0f |
| bSyncSplines | +0x140 | false |
| OnSplineEndReached | +0x144 | empty |
| OnTargetSplineEndReached | +0x148 | empty |

## Evidence boundary

`camera_default_state_runtime.py` stores raw IEEE-754 bit patterns for float defaults and exposes decoded values only as a convenience. No units are inferred from the numeric values.

Renderer and RENDER.bff remain untouched.