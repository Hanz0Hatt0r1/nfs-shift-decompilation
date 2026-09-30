# Phase 578 — runtime-proven native scene bundle

Phase 577 makes runtime proof explicit on the final renderer-neutral
`SHIFT.RenderCommand/1` submesh. Phase 578 freezes those proven scene draws
into a deterministic scene-level manifest without yet constructing
backend-specific Vulkan artifacts.

## Contract

The new contract is:

`SHIFT.NativeSceneBundle/1`

implemented in:

`src/scene/native_scene_bundle.py`.

Input is one ready:

`SHIFT.SGBRenderBindingBridge/1`.

The packager consumes the bridge's aligned DrawPacket/RenderCommand sequence and
the ready `SHIFT.IMBRuntimeRenderBindingJoin/1`.

## Admission rule

A submesh enters the native-scene manifest only when it carries a valid:

`SHIFT.RuntimeProvenDraw/1`.

The packager independently revalidates:

- provenance format/status;
- non-negative Phase 574 binding index;
- exact IMB source kind/path/SHA;
- primitive index;
- exact first/index/primitive counts;
- `selection_status = unique`;
- `selection_source = runtime-admission`;
- Phase 575 runtime-selection readiness;
- equality between provenance draw range and RenderCommand draw range.

A statically unique draw without RuntimeProvenDraw is excluded.

## RenderCommand gate

Runtime provenance is necessary but not sufficient.

The corresponding RenderCommand must also be ready and pass the existing
`validate_render_command()` contract. This keeps all normal geometry, shader,
texture, uniform and renderer-resource checks in force.

## World transform

Every admitted native-scene draw requires an exact numeric 4x4 world matrix.

The packager accepts either:

- a flat 16-scalar matrix; or
- a nested 4x4 matrix.

It stores a normalized 16-float form in the manifest. Missing or non-numeric
world state excludes the draw rather than substituting an identity matrix.

## Shader identity

Each admitted draw must carry complete backend-independent shader identity:

- source FXO payload SHA-256;
- VS+PS pair SHA-256;
- vertex shader SHA-256;
- pixel shader SHA-256;
- `SHIFT.ShaderPermutationIdentity/1` SHA-256.

This is separate from SPIR-V compilation/readiness, which remains the next
backend gate.

## Deterministic draw identity

Each admitted row stores:

- scene/draw order;
- RenderCommand/submesh indices;
- Phase 574 binding index;
- primitive index;
- exact scene wrapper metadata;
- exact IMB resource identity;
- exact draw range;
- world matrix;
- shader identity;
- full RuntimeProvenDraw provenance.

The manifest also computes deterministic SHA-256 values for:

- the complete RenderCommand;
- the command submesh;
- RuntimeProvenDraw provenance;
- world matrix;
- combined draw identity.

Canonical JSON serialization uses sorted keys and compact separators before
hashing.

## Partial coverage

Phase 578 deliberately permits partial scene coverage.

Unproven or otherwise non-packable submeshes are recorded in
`excluded_draws[]` and are never promoted.

The top-level bundle can be ready when at least one draw is proven and all
top-level bridge/join contracts are ready.

Coverage records:

- total RenderCommand submeshes;
- runtime-proven submeshes;
- native-packable proven submeshes;
- excluded submeshes;
- whether scene coverage is complete.

This allows the first authentic Silverstone capture to advance proven geometry
without fabricating the remaining primitives.

## Backend boundary

Phase 578 does **not** build Vulkan/SPIR-V/texture packets.

The manifest records:

`builds_backend_artifacts = false`.

The existing BMW `SHIFT.BMWVulkanBundle/1` builder remains BMW-specific and
still hardcodes its canonical MEB target. Phase 578 therefore does not reuse it
by pretending IMB is MEB.

## CLI

The root importer now exposes:

```bash
python shift_importer.py native-scene-bundle \
  scene-render-binding.json \
  native-scene-bundle.json
```

The standalone module exposes the same input/output pair.

## Next

Generalize the atomic Vulkan bundle builder from its BMW/MEB specialization to
a neutral RenderCommand + neutral geometry path while preserving the existing
BMW ABI.

Then map each `SHIFT.NativeSceneBundle/1` draw to one independently gated
child Vulkan bundle, preserve manifest draw order/world/provenance, and hand the
resulting ordered set to `native_runtime`.

An authentic Silverstone D3D9 capture remains the external evidence gate for
producing real Phase 578 draws.
