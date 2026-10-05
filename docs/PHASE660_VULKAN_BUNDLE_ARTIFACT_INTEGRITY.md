# Phase 660 — Vulkan draw-bundle artifact integrity before native prepare

## Playable-slice blocker reduced

The native playable composition has two resource paths that converge on
`SHIFT.VulkanDrawBundlePrepare/1`:

```text
prepared Silverstone track child
        \
         -> playable scene set -> prepare_native_scene_vulkan_set()
        /
rebuilt BMW child
```

`SHIFT.VulkanDrawBundle/1` already records exact SHA-256 values for its emitted
artifacts, including geometry, constants, gates, pipeline state, shaders,
textures, the optional environment cube, world transform, and sampler metadata.

Before Phase 660, `prepare_vulkan_draw_bundle()` explicitly revalidated the
world-transform packet SHA, but other manifest-declared artifacts were consumed
or trusted without a uniform manifest-to-file integrity pass. A persisted child
could therefore drift between bundle construction and the later scene/playable
prepare boundary.

Phase 660 closes that gap before SPIR-V compilation, interface validation, or
native scene preparation.

## Fail-closed integrity pass

`src/render/vulkan/vulkan_draw_bundle_prepare.py` now walks every artifact
identity declared by `bundle_manifest.json`.

For each declared `path + sha256` pair it requires:

- a non-empty relative path;
- no absolute path;
- no `..` traversal;
- a canonical 64-character hexadecimal SHA-256;
- an existing regular file;
- equality between the current file SHA-256 and the manifest SHA-256.

The traversal covers both artifact shapes currently emitted by the neutral
builder:

- mapping entries such as `geometry`, `constants`, `pipeline_state`, gates,
  textures, environment cube, world transform and sampler contracts;
- list entries such as per-stage GLSL `shaders`.

The sampler-contract secondary `metadata_path + metadata_sha256` pair is also
verified when present.

Any mismatch blocks prepare before shader compilation. Example diagnostics:

```text
vulkan-draw-prepare:artifact:geometry:sha256-mismatch
vulkan-draw-prepare:artifact:native_submission_gate:sha256-mismatch
vulkan-draw-prepare:artifact:shaders[0]:path-unsafe
```

## Why semantic revalidation alone is insufficient

A JSON gate can remain syntactically valid and still report `ready=true` after
its bytes have changed. Likewise, a binary packet may remain parseable after
modification. Phase 660 therefore treats the producing bundle manifest as the
artifact identity authority and verifies byte identity before invoking semantic
consumers.

The existing semantic checks remain in place after the integrity gate:

```text
manifest artifact SHA checks
-> native submission gate validation
-> runtime provenance gate validation
-> SVWT validation
-> SPIR-V compilation
-> Vulkan interface validation
```

## Diagnostics and boundary

The prepare result now exposes:

```text
manifest_artifact_integrity.ready
manifest_artifact_integrity.verified_count
manifest_artifact_integrity.artifacts[]
```

Each verified row carries the relative path, expected SHA, actual SHA, and an
explicit match bit.

The boundary also records:

```text
manifest_declared_artifacts_sha256_revalidated = true
artifact_integrity_checked_before_compile = true
```

when the declared bundle artifacts pass the integrity gate.

## Regression coverage

`tests/test_phase660_vulkan_bundle_artifact_integrity.py` verifies:

1. unchanged manifest-declared artifacts are admitted;
2. a changed `geometry.svpk` is rejected before compilation;
3. a modified `native_submission_gate.json` that still says `ready=true` is
   rejected by byte identity even though its semantic ready check still passes;
4. an unsafe shader artifact path is rejected.

The complete existing Python and Linux/Vulkan suites remain the integration gate
for Silverstone scene children, BMW children, world-transform packets, native
runtime scheduling, input, and persistent BODY state.

## Ownership boundary

Phase 660 is reusable Process 3 resource/render infrastructure. It does not
change:

- resource producer identities;
- shader permutation selection;
- Phase 593/659 external sampler ownership;
- BODY identity or physics scheduling;
- input processing;
- camera production;
- `VehicleWorldMatrix` production or execution semantics.

## Result

A Vulkan child is no longer considered prepared solely because its manifest and
semantic gate files remain readable. Every artifact identity declared by the
producing `SHIFT.VulkanDrawBundle/1` manifest must still match the bytes present
at the final native-prepare boundary used by both Silverstone track and BMW
playable composition.
