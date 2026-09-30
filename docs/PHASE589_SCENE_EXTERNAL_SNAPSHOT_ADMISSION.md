# Phase 589 — exact scene external sampler2D snapshot admission

Phase 588 adds an explicit external-`sampler2D` transport channel to the
existing SVTP binary ABI. Phase 589 connects that channel to the neutral
Silverstone scene pipeline without inferring renderer-owned resource identity.

## Snapshot-set contract

New contract:

`SHIFT.SceneExternalTextureSnapshotSet/1`

Each row is bound to all of the following:

- `draw_order`;
- `scene_draw_identity_sha256`;
- sampler name;
- sampler type, currently exactly `sampler2D`;
- original D3D9 sampler register;
- a relative `SHIFT.ReferenceTexture/1` JSON path;
- SHA-256 of that exact ReferenceTexture file;
- caller-supplied source provenance.

The loader rejects unsafe paths, duplicate `(draw_order, register)` rows,
invalid hashes, non-2D sampler types and missing provenance.

The source-provenance field is preserved but does not by itself prove that a
snapshot is an authentic retail capture.

## NativeSceneVulkanSet admission

`build_native_scene_vulkan_set()` now accepts an optional snapshot-set path.

A supplied snapshot resolves one external sampler blocker only when:

1. its draw order selects the same Phase 578 scene draw;
2. its draw-identity SHA-256 equals that draw's exact identity hash;
3. the selected RenderCommand submesh declares exactly one external sampler at
   the same register;
4. sampler name and `sampler2D` type match exactly;
5. the snapshot-set content hash gate is ready.

Only then is the ReferenceTexture forwarded to Phase 588
`external_textures`, producing an SVTP record at the original D3D9 register.

Without a matching snapshot, the existing blocker remains:

```text
external-sampler:runtime-resource-unresolved:sN:sampler2D
```

No fallback lookup by sampler name or retail DDS filename is attempted.

## Unused and stale snapshots

A snapshot that does not bind to a scene draw is itself a blocker. This covers:

- stale draw hashes;
- wrong sampler name/type/register;
- snapshots for draws not present in the current scene set.

The set therefore cannot silently carry unused renderer state from a different
capture/draw.

## CLI

```bash
python shift_importer.py native-scene-vulkan-set \
  native-scene-bundle.json \
  scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan \
  --external-texture-snapshots external-snapshots.json
```

The produced child bundle preserves snapshot provenance and reports exactly
which external registers were admitted.

## Interaction with Phase 585/586

Phase 589 does not change the native runtime ABI.

Once all non-transform scene blockers are resolved, the existing
`SHIFT.NativeSceneVulkanSetPrepare/1` gate can discard only the historical
`scene-world-transform-not-executed` marker, prepare the children, and Phase
586 can execute them through `native_runtime --scene-set`.

## Boundary

Phase 589 closes explicit **scene admission** for externally supplied 2D
snapshots. It does not create the snapshots.

Authentic Silverstone runtime evidence is still required to provide real
renderer-owned texture content for the relevant draw/register pairs. Cube
resources remain on their separately proven path.
