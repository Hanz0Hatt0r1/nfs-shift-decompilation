# Phase 579 — neutral runtime-proven Vulkan draw bundle

Phase 578 freezes runtime-proven scene draws into
`SHIFT.NativeSceneBundle/1`, but the existing atomic Vulkan bundle builder is
still BMW-specific and hardcodes the canonical BMW body MEB.

Phase 579 introduces a neutral atomic bundle contract without changing the BMW
ABI.

## Contract

The new contract is:

`SHIFT.VulkanDrawBundle/1`

implemented in:

`src/render/vulkan/vulkan_draw_bundle.py`.

Inputs are:

- `SHIFT.RenderCommand/1` or a `SHIFT.RenderBinding/1` command selection;
- neutral geometry with vertices/indices;
- optional material texture images;
- optional environment cube.

Supported neutral geometry wrappers are:

- `SHIFT.NeutralMesh/1`;
- `SHIFT.IMBNeutralGeometry/1` (its nested mesh is unwrapped);
- the existing `SHIFT.MEB` neutral JSON;
- legacy untagged neutral mesh JSON.

Accepting multiple neutral containers does not assert serialized-container
equivalence.

## Runtime provenance gate

Scene usage requires `SHIFT.RuntimeProvenDraw/1` by default.

The bundle rechecks:

- provenance format/status;
- exact IMB resource kind/path/SHA;
- `runtime-admission` selection source;
- unique selection;
- Phase 575 runtime-selection readiness;
- exact equality between provenance and command draw ranges.

A missing or stale runtime proof blocks the bundle before binary artifacts are
produced.

For non-scene regression/oracle uses the builder can be explicitly called with
`require_runtime_provenance=false` or CLI `--allow-static`. This is an
explicit opt-out rather than an implicit fallback.

## Reused native gates

Phase 579 does not create a second Vulkan execution stack.

It reuses:

- `SHIFT.NativeSubmissionGate/1`;
- `SHIFT.VulkanGeometryPacket/1`;
- `SHIFT.VulkanConstantPacket/1`;
- `SHIFT.VulkanTexturePacket/1`;
- `SHIFT.VulkanCubeTexturePacket/1`;
- sampler-contract generation;
- source-backed BMT → Vulkan pipeline-state translation.

The generated artifact layout intentionally follows the mature BMW atomic
bundle layout:

- `geometry.svpk`;
- `constants.svcp`;
- optional `textures.svtp`;
- optional `environment_cube.svcp`;
- GLSL source files;
- sampler contracts;
- native submission gate;
- runtime provenance gate;
- pipeline state;
- `bundle_manifest.json`.

The new manifest format is neutral; the existing
`SHIFT.BMWVulkanBundle/1` implementation remains unchanged.

## Geometry metadata correction

The shared Vulkan geometry exporter previously labelled all neutral source
geometry as:

`MEB object space`.

Its binary ABI already accepted generic vertices/indices, so Phase 579 changes
only metadata:

- source space is now `neutral object space`;
- source neutral mesh format is recorded;
- source serialized format is recorded when available.

The SVGP binary version/layout is unchanged.

## Scene transform boundary

The current geometry packet normalizes object-space geometry into a clip-space
checkpoint. It does not execute the SGB world matrix.

Therefore a generic bundle with a world matrix records:

`scene_transform.execution_status = "preserved-not-applied"`.

The atomic bundle may still be ready because all atomic GPU artifacts are
valid, but it explicitly records:

`scene_world_transform_executed = false`.

A later scene submission layer must close this gate before claiming correct
Silverstone world-space rendering.

## CLI

The root importer exposes:

```bash
python shift_importer.py vulkan-draw-bundle \
  render-command.json \
  neutral-mesh.json \
  out/vulkan-draw
```

Optional flags mirror the standalone builder:

- `--textures`;
- `--environment-cube`;
- `--command-index`;
- `--submesh-index`;
- `--allow-static`.

## Regression coverage

Phase 579 covers:

- runtime-proven `SHIFT.NeutralMesh/1` bundle construction;
- IMB-neutral wrapper unwrapping;
- runtime provenance required by default;
- explicit static opt-out;
- stale draw-range proof blocking;
- unknown mesh-contract rejection;
- preservation-but-nonexecution of world transforms;
- unchanged BMW bundle implementation through the existing full suite.

## Next

Build the NativeSceneBundle → Vulkan child-bundle adapter.

For each Phase 578 draw it must:

1. re-resolve the exact IMB resource from IR;
2. reconstruct `SHIFT.IMBNeutralGeometry/1`;
3. select the exact RenderCommand/submesh identified by the scene manifest;
4. build one `SHIFT.VulkanDrawBundle/1`;
5. compare child resource/draw/shader/world hashes back to the scene manifest;
6. preserve Phase 578 draw order.

The ordered set still must not claim native scene execution until the world
matrix is consumed by the Vulkan shader/backend path.
