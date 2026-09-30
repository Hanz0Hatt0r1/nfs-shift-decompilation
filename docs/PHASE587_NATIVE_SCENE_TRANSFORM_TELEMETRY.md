# Phase 587 — native scene transform execution telemetry

Phase 586 makes the offline Linux runtime consume prepared neutral
`SHIFT.NativeSceneVulkanSet/1` input and execute each child's SVWT before GPU
upload.

Phase 587 tightens that checkpoint so a successful frame loop is not enough to
claim transform execution.

## Runtime telemetry

`PacketGeometry` now records whether its `world_transform.svwt` sidecar was
actually consumed and whether the executed transform was translation-only or
used the general affine path.

`SHIFT.NativeRuntimeBootstrap/1` adds:

- `world_transform_draws` — material draws whose SVWT was successfully
  executed before GPU upload;
- `affine_world_transform_draws` — executed transforms that were not
  translation-only.

The counters are derived only after the existing fail-closed Phase 584 affine
rules complete successfully. Missing, malformed, non-finite or singular SVWT
does not increment them.

## CI checkpoint

The neutral scene-set Linux Vulkan smoke uses the existing non-singular affine
fixture and now requires:

```json
"world_transform_draws": 1
"affine_world_transform_draws": 1
```

This distinguishes three cases that previously all looked like a successful
scene-set launch:

1. scene admitted but SVWT ignored;
2. translation-only transform consumed;
3. the intended semantic-aware affine path executed.

Only case 3 satisfies the Phase 587 smoke.

## Compatibility

The BMW single-bundle and `--bundle-set` paths keep the same admission and
rendering contracts. The telemetry fields are additive to the bootstrap record.

## Boundary

Phase 587 improves observability only. It does not create authentic Silverstone
runtime-proven draws, renderer-owned resources, scene streaming/LOD behavior or
per-instance transform history.

Those remain the next external/integration evidence gates.
