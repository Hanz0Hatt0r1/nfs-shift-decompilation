# Phase 259 — CCameraView projection defaults

Phase 259 reconstructs the projection-scalar initializer shared by the camera-view runtime.

## Evidence

`FUN_0081aeb0` explicitly writes four floating-point defaults:

| Field | Offset | Raw bits | Decoded value |
|---|---:|---:|---:|
| FOV | +0x34 | `0x3f490fdb` | 0.7853981853 |
| AspectRatio | +0x38 | `0x3faaaaab` | 1.3333333731 |
| NearZ | +0x3c | `0x3dcccccd` | 0.1 |
| FarZ | +0x40 | `0x443b8000` | 750.0 |

`FUN_0081ac70` independently registers the same offsets under `FOV`, `AspectRatio`, `NearZ` and `FarZ`.

`camera_view_default_runtime.py` therefore exposes those four values as a small versioned contract and retains their exact IEEE-754 bit patterns.

## Limits

The runtime does not provide enough evidence here to attach an angle unit, projection-matrix convention or camera transform semantics to these scalars. No conversion is applied.

Renderer and RENDER.bff remain untouched.