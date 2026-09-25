# Phase 256 — Camera class registration and partial inheritance

Phase 256 extends the CameraConfig runtime model with the class-registration evidence used by the generic runtime factory.

## Proven inheritance links

The executable's static initialization records establish these direct camera-related links:

| Derived | Proven base | Initializer |
|---|---|---|
| CCameraView | CBaseCamera | FUN_00a8cdb0 |
| CBaseCamera | CCameraObj | FUN_00a8d190 |
| CFreeCamera | CCameraObj | FUN_00a8d220 |
| CAttachedCamera | CBaseCamera | FUN_00a8d2a0 |
| CStaticCamera | CBaseCamera | FUN_00a8cf90 |
| CTrackingCamera | CStaticCamera | FUN_00a8d510 |
| CSphereArea | CCamArea | FUN_00a8d3f0 |
| COBBArea | CCamArea | FUN_00a8d480 |
| CTrackingCamData | CStaticCamData | FUN_00a8d5a0 |

`resolve_camera_class_chain()` walks only these proven links. Several classes point to the unresolved common base object `DAT_00bfa608`; chains terminating there are marked partial.

## Why this matters

FUN_008117c0 and FUN_00811d40 invoke the generic class-resolution path FUN_006408f0. Having the proven prefix lets later XML analysis distinguish direct/derived runtime classes without guessing the missing base registry.

Examples:

- CTrackingCamera resolves through CStaticCamera and CBaseCamera to CCameraObj, with the CCameraObj base still unresolved.
- CSphereArea and COBBArea both resolve to CCamArea, whose own base remains unresolved.

## Limits

Unknown base objects are preserved as unresolved. No new base-class names, virtual-method meanings or camera behavior are inferred. Renderer and RENDER.bff remain untouched.