# Phase 585 — neutral NativeSceneVulkanSet prepare/admission

Phase 580 builds `SHIFT.NativeSceneVulkanSet/1`: an ordered set of exact
runtime-proven Silverstone `SHIFT.VulkanDrawBundle/1` children.

Phases 581–584 then close the scene-transform side of the atomic material path:

- SVWT serializes the source-backed SGB world matrix;
- SVGP v3 carries exact SHIFT vertex property IDs;
- the native material executor applies general non-singular affine transforms
  to POSITION/NORMAL/TANGENT/TANGENT2.

The remaining handoff problem is that the existing prepare/set infrastructure
is BMW-specific. Phase 585 adds a neutral preparation contract without
relabeling scene children as BMW bundles.

## Neutral atomic prepare

New module:

`src/render/vulkan/vulkan_draw_bundle_prepare.py`

emits:

`SHIFT.VulkanDrawBundlePrepare/1`.

A neutral child is admitted only when all of these remain true:

- `bundle_manifest.json` is `SHIFT.VulkanDrawBundle/1` and ready;
- `SHIFT.NativeSubmissionGate/1` is present and ready;
- `SHIFT.VulkanDrawRuntimeProvenanceGate/1` is present and ready;
- a non-null scene world matrix has a safe, content-hash-matched
  `SHIFT.VulkanWorldTransformPacket/1`;
- all copied GLSL shaders compile and reflect through the existing SPIR-V gate;
- the descriptor/resource interface is ready.

The prepare report records the exact source manifest hash, gate artifacts,
SPIR-V/interface reports and the world-transform packet identity.

It does not execute `native_runtime`.

## Neutral SPIR-V and interface APIs

The established BMW APIs remain backward-compatible.

Phase 585 adds neutral entry points:

- `compile_vulkan_bundle()`;
- `validate_vulkan_bundle_interface()`.

They accept both:

- `SHIFT.BMWVulkanBundle/1`;
- `SHIFT.VulkanDrawBundle/1`.

The existing BMW wrappers still require BMW input and preserve their legacy
JSON shapes.

The neutral interface result uses:

`SHIFT.VulkanInterfaceGate/1`.

## Scene-set prepare

New module:

`src/scene/native_scene_vulkan_prepare.py`

emits:

`SHIFT.NativeSceneVulkanSetPrepare/1`.

It validates:

- source set format/readiness;
- exact draw_count and ready_draw_count;
- contiguous draw_order;
- each source draw ready state;
- strictly relative ordered child paths;
- child manifest SHA-256 against the Phase 580 recorded identity;
- one ready `SHIFT.VulkanDrawBundlePrepare/1` per child;
- one prepared world-transform packet per scene child.

The output is persisted as:

`bundle_set_prepare.json`.

This intentionally shares the filename used by the existing multi-draw runtime
handoff while keeping a distinct neutral format.

## Phase 584 transform blocker handling

Phase 580 predates native SVWT execution, so its set manifest records blockers
of the form:

`draw-N:scene-world-transform-not-executed`.

Phase 585 treats only that exact blocker class as resolvable by the now-proven
Phase 584 child execution capability.

Any other native-scene blocker remains blocking, including unresolved external
renderer resources.

This means the prepare gate cannot silently promote an unresolved shadow map,
cube, or other renderer-global resource merely because affine transforms are
now executable.

## Portable draw-order sidecar

Phase 580 previously wrote `bundle_set.paths` using the output directory
prefix.

Phase 585 corrects this contract. Each line is now strictly relative to the
set root, for example:

```text
draw_0000
draw_0001
draw_0002
```

The prepare gate rejects:

- absolute paths;
- parent traversal;
- output-directory-prefixed paths;
- order/path mismatch.

This makes the bundle set relocatable and suitable for a native loader.

## CLI

The root importer exposes:

```bash
python shift_importer.py native-scene-vulkan-prepare \
  out/native-scene-vulkan \
  --validator glslangValidator
```

By default the result is written to:

`out/native-scene-vulkan/bundle_set_prepare.json`.

## Tests

Phase 585 covers:

- neutral bundle acceptance by the generic SPIR-V/interface APIs;
- BMW wrapper rejection of neutral input;
- atomic neutral prepare success;
- runtime-provenance gate requirement;
- SVWT hash tamper rejection;
- set-level resolution of only the Phase 584 transform blocker;
- unresolved external-resource blocker preservation;
- non-relative/path-order rejection;
- child manifest SHA tamper rejection;
- exact portable `bundle_set.paths`;
- root CLI parsing.

## Boundary after Phase 585

A scene set can now be built and fully prepared without BMW relabeling.

The prepare report explicitly keeps:

`native_runtime_scene_set_loader_available = false`.

Phase 586 should extend `native_runtime` to:

1. accept `SHIFT.NativeSceneVulkanSet/1` +
   `SHIFT.NativeSceneVulkanSetPrepare/1`;
2. accept neutral `SHIFT.VulkanDrawBundle/1` children;
3. consume each child SVWT before GPU upload using the Phase 584 semantic
   affine rules;
4. preserve the prepared draw order;
5. report the neutral scene-set source rather than
   `SHIFT.BMWVulkanBundleSet/1`.

External runtime resources remain a separate fail-closed gate.
