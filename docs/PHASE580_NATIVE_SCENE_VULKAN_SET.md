# Phase 580 — NativeSceneBundle to ordered Vulkan child set

Phase 578 freezes runtime-proven scene draws into
`SHIFT.NativeSceneBundle/1`.

Phase 579 adds one neutral atomic `SHIFT.VulkanDrawBundle/1`.

Phase 580 connects those two boundaries without claiming native scene
execution.

## Contract

The new orchestration contract is:

`SHIFT.NativeSceneVulkanSet/1`.

Implemented in:

`src/scene/native_scene_vulkan_set.py`.

Inputs:

- one ready `SHIFT.NativeSceneBundle/1`;
- the matching `SHIFT.SGBRenderBindingBridge/1`;
- the extracted/analyzed IR root containing `manifest.json`;
- an output directory;
- optionally one external environment-cube DDS.

## Exact scene revalidation

Every Phase 578 draw is rejoined to the original RenderCommand/submesh using
its stored:

- command index;
- submesh index;
- draw order.

Before any child bundle is built, Phase 580 recomputes and verifies:

- RenderCommand SHA-256;
- submesh SHA-256;
- RuntimeProvenDraw SHA-256;
- world-matrix SHA-256;
- shader identity;
- combined draw identity;
- resource path/SHA;
- primitive index;
- draw range;
- runtime binding index.

A stale or edited NativeSceneBundle therefore cannot silently point at a
different current RenderCommand.

## Exact IMB re-resolution

The runtime-proven resource is resolved from IR by:

- logical IMB path;
- source archive;
- decoded/source SHA-256 identity.

The raw IMB payload is decoded again through
`SHIFT.IMBNeutralGeometry/1`.

The exact source primitive is selected by its explicit serialized
`primitive.index`, not by assuming the primitive list is densely indexed.

The reconstructed primitive must match the Phase 578:

- first index;
- index count;
- primitive/triangle count.

No MEB equivalence is inferred.

## 2D DDS resolution

For ordinary material textures, Phase 580 follows:

`RenderCommand texture_id -> RenderBinding.resources -> logical DDS path -> IR manifest -> raw DDS`.

The DDS is decoded through the existing `decode_dds()` reference path and
passed as `SHIFT.ReferenceTexture/1` input to the Phase 579 child builder.

The child therefore produces its normal:

- `textures.svtp`;
- sampler contracts;
- texture provenance.

No BMW-specific DDS material adapter is required for ordinary 2D scene
textures.

## External resources

Renderer-owned external samplers remain fail-closed.

An optional environment cube may satisfy the already-proven:

- samplerCube;
- D3D9 register s3;

contract.

Other external samplers remain explicit
`native_scene_submission.blocking_reasons`.

They do not block preparation of otherwise valid atomic child bundles, but
they do block a claim that the full native scene is submission-ready.

## World-transform boundary

Phase 579 still preserves but does not execute the SGB world matrix.

Therefore Phase 580 may report:

- `ready = true` for the complete ordered child-bundle set;
- `native_scene_submission.ready = false`.

This distinction is intentional.

`ready` means:

all proven scene draws were deterministically resolved and converted to valid
atomic Vulkan bundles.

It does **not** mean:

the scene can already be rendered at correct Silverstone world-space
placements.

Every child whose world transform is not consumed produces:

`draw-N:scene-world-transform-not-executed`.

## Ordered output

Each child lives under:

`draw_0000/`, `draw_0001/`, ...

The top-level output contains:

- `bundle_set_manifest.json`;
- `bundle_set.paths`.

The paths file contains only ready child bundle directories in exact Phase 578
draw order. It is intended as the future input surface for the existing native
multi-draw preparation/execution path.

## CLI

The root importer exposes:

```bash
python shift_importer.py native-scene-vulkan-set \
  native-scene-bundle.json \
  scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan
```

Optional:

```bash
--environment-cube-dds path/to/cube.dds
```

## Regression coverage

Phase 580 tests cover:

- one complete runtime-proven IMB draw -> one Vulkan child bundle;
- deterministic ordered paths output;
- exact NativeSceneBundle hash revalidation;
- exact IMB resource identity;
- explicit primitive-index/range revalidation;
- automatic material 2D DDS resolution from IR;
- external sampler fail-closed behavior;
- world-transform non-execution as a separate native submission blocker;
- root CLI parsing.

## Next

Execute the preserved world matrix in the Vulkan/native draw path.

The preferred next boundary is to stop clip-space normalization for scene
draws and provide a real object-to-world/view/projection transform path while
keeping the existing geometry-only checkpoint behavior available for legacy
tests.

After that, the ordered Phase 580 child set can be admitted to
`native_runtime` as an actual scene render set instead of preparation-only
artifacts.

An authentic Silverstone D3D9 capture remains the external shader-evidence gate
for producing real runtime-proven Phase 578/580 scene draws.
