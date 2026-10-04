# Phase 641 — exact external sampler observation frontier

This note records the narrow Process 3 blocker refinement added to the existing
Phase 641 renderer-native-scene handoff.

No new renderer proof or coordination report is introduced. The authoritative
artifact remains `SHIFT.RendererNativeSceneHandoff/1` and the detailed data is
stored under `existing_capture_completion.runtime_evidence_required`.

A missing snapshot observation is actionable only after the existing Phase 573,
576, 578 and 590 chain has already established the exact scene binding, sampler
register and expected D3D9 resource type. The diagnostic never promotes a
basename, resource similarity, path proximity, missing type evidence or a zero
candidate count by itself.

For each actionable row it preserves the exact binding, draw order, register,
sampler/type, capture frame/draw indices, expected D3D9 resource type, observed
snapshot statuses/path cardinalities and the minimal texture stage that must be
observed with snapshot content.

The historical raw capture can therefore be classified precisely: shader/draw
and SetTexture evidence may be reusable while a selected renderer-owned sampler
still requires one draw-local PPM (sampler2D) or six named faces (the proven
samplerCube s3 path). This does not imply that all textures or all stages need a
new capture.

The global `new_capture_required` claim remains false because an independently
proven explicit renderer resource can still satisfy the boundary. The narrower
`capture_observation_required` flag means only that the supplied capture cannot
complete that exact Phase 590 row without the listed content observation.
