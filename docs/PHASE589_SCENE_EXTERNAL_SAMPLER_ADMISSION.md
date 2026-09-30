# Phase 589 — exact scene external sampler2D admission

Phase 588 adds an explicit transport ABI for externally supplied
`sampler2D` images. It deliberately stops before a scene can treat one of
those images as satisfying a renderer-owned resource requirement.

Phase 589 closes that scene-level admission boundary without inventing an
external texture or reclassifying it as a material DDS.

## Contract

The new input contract is:

`SHIFT.NativeSceneExternalSamplerSnapshots/1`

implemented by:

`src/scene/native_scene_external_sampler_snapshots.py`.

Each snapshot is bound to one exact scene draw and contains:

- `draw_identity_sha256` from `SHIFT.NativeSceneBundle/1`;
- exact IMB archive/path/SHA-256;
- exact primitive index;
- D3D9 sampler register;
- sampler type, currently only `sampler2D`;
- one inline `SHIFT.ReferenceTexture/1` RGBA8 image;
- canonical JSON SHA-256 of that texture object;
- `SHIFT.ExternalSamplerSnapshotProvenance/1` with explicit
  `source_kind` and `source_sha256`.

The contract rejects duplicate draw/register/type rows and malformed or
unhashed texture/provenance input.

## Scene join

`SHIFT.NativeSceneVulkanSet/1` accepts the optional snapshot contract.

For every runtime-proven scene draw the resolver requires all of these to
match before a snapshot can satisfy an external sampler:

1. exact scene `draw_identity_sha256`;
2. exact IMB archive;
3. exact IMB path;
4. exact decoded IMB SHA-256;
5. exact primitive index;
6. exact sampler register;
7. exact `sampler2D` type.

A match produces one draw-local external texture map which is passed to the
Phase 588 `SHIFT.VulkanDrawBundle/1` texture-packet path.

The resulting child bundle marks the sampler as:

`provided-to-vulkan-texture-packet`.

The scene child also preserves a provenance row with the snapshot index,
texture hash, exact resource identity and source provenance.

## Fail-closed behavior

The old behavior remains when no snapshot is supplied:

`external-sampler:runtime-resource-unresolved:sN:sampler2D`.

Supplying a snapshot does not weaken any existing scene identity gates. If a
snapshot matches the draw hash/register but disagrees on resource identity or
primitive index, the child becomes blocked with an explicit
`external-snapshot:...` reason.

An invalid top-level snapshot contract blocks the scene set instead of being
ignored.

## Independence from SVWT

Phase 589 resolves only the renderer-owned external resource.

The pre-prepare `SHIFT.NativeSceneVulkanSet/1` can still contain the separate
`scene-world-transform-not-executed` blocker. Phase 585/586 preparation and
runtime execution resolve that transform boundary independently.

This separation is intentional: providing a shadow/image snapshot cannot be
used as evidence that a world transform was executed, and vice versa.

## CLI

The root importer exposes the contract through the existing scene command:

```bash
python shift_importer.py native-scene-vulkan-set \
  native-scene-bundle.json \
  scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan \
  --external-sampler-snapshots scene-external-snapshots.json
```

The standalone module exposes the same option.

## Native ABI

No new native binary texture format is introduced.

An admitted external `sampler2D` becomes an ordinary descriptor-set-1 SVTP
record at its original D3D9 register, so the existing Phase 588/native runtime
texture upload code consumes it unchanged.

The source distinction remains in JSON provenance and bundle metadata.

## Tests

Regression coverage verifies:

- exact snapshot contract validation;
- canonical texture hash mismatch rejection;
- duplicate draw/register/type rejection;
- exact resource/primitive matching;
- absent-contract compatibility;
- unchanged unresolved behavior when no snapshot is supplied;
- successful scene child admission for exact s7 `sampler2D`;
- child manifest status `provided-to-vulkan-texture-packet`;
- mismatched resource SHA fail-closed behavior;
- root CLI exposure.

## Boundary after Phase 589

The code path no longer needs to guess how an authentic external
`sampler2D` snapshot would enter a Silverstone scene draw.

Still open:

- obtaining authentic provenance-bearing snapshots from retail runtime
  evidence;
- scene-level `samplerCube`/other renderer-owned resources beyond their
  separately proven transport paths;
- exact Silverstone shader attribution from a real D3D9 capture;
- remaining MatrixNumber update history and streaming/LOD behavior;
- the IMX XML neutral adapter.
