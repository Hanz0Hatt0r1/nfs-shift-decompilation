# Phase 657 — exact Silverstone material texture identity before native Vulkan scene admission

## Playable-slice blocker reduced

Phase 580 already rebuilds every runtime-proven Silverstone scene draw as a
neutral `SHIFT.VulkanDrawBundle/1` and resolves ordinary material DDS resources
from the extracted IR. The producer-side `SHIFT.RenderResources/1` texture rows
already carry exact logical path + SHA-256 identity.

The Phase 580 resolver, however, previously selected the IR texture using only:

```text
logical path
+ preferred archive when available
```

while ignoring the already supplied texture SHA-256 during lookup. Therefore a
single path-matching IR entry with drifted bytes could be selected even though it
disagreed with the exact texture identity emitted by the render-binding producer.

Phase 657 closes that resource identity gap on the direct path:

```text
runtime-proven Silverstone draw
→ SGB render-binding bridge
→ SHIFT.RenderResources/1 texture path + SHA-256
→ extracted IR manifest
→ material DDS decode
→ Vulkan child bundle
```

## Exact lookup rule

For every non-external material sampler, Phase 580 now requires a valid 64-character
producer texture SHA-256 before it attempts IR resolution.

Selection becomes:

```text
preferred archive + logical path + expected SHA-256
        |
        | not present in preferred archive
        v
all admitted IR rows + logical path + expected SHA-256
```

A path-only match with no exact SHA match is reported as:

```text
texture:sN:ir-resource-sha256-mismatch
```

A producer texture row without a valid SHA identity is reported as:

```text
texture:sN:renderer-resource-sha256-invalid
```

Multiple exact path+SHA candidates remain ambiguous through the existing
`_exact_row()` fail-closed policy. Archive order and first-match selection are
not authority.

## Cross-archive fallback

The historical Phase 580 behavior allowing an ordinary material resource to be
found outside the IMB's preferred archive is preserved, but the fallback is now
allowed only when the candidate has the exact same logical path and producer
SHA-256.

This matters for resources legitimately supplied by shared archives such as
`RENDER.bff`: a same-name payload with different bytes in the preferred track
archive cannot shadow the exact resource identity.

## Provenance output

Each admitted `texture_sources` row now records both sides of the join:

```text
sha256
expected_sha256
identity_sha256_match = true
```

The set-level boundary records:

```text
material_2d_dds_render_resource_sha256_revalidated = true
```

This makes the identity decision visible to downstream audits instead of leaving
it implicit in path resolution.

## External sampler boundary unchanged

Phase 657 applies only to ordinary BMT/material-backed DDS resources already
represented in `SHIFT.RenderResources/1`.

It does **not** reinterpret renderer-owned external samplers. In particular:

- external `sampler2D` resources still require the exact Phase 589 snapshot
  contract when needed by native scene submission;
- external `samplerCube s3` still requires the Phase 593 cube snapshot contract
  or another explicitly admitted path supported by that contract;
- a path-similar retail DDS is never substituted for runtime snapshot identity;
- the historical capture's missing portable path+SHA/snapshot observations are
  not silently fabricated.

## Regression coverage

`tests/test_phase657_native_scene_material_texture_identity.py` verifies:

1. exact producer path+SHA and IR path+SHA are admitted;
2. a path match with a different IR SHA is rejected;
3. a renderer texture without an exact SHA is rejected;
4. fallback to another archive succeeds only when the exact producer SHA is
   preserved.

Existing `tests/test_native_scene_vulkan_set.py` continues to cover the full
Phase 580 scene-build path and snapshot behavior.

## Ownership boundary

Phase 657 is Process 3 resource/render admission only. It does not change:

- shader permutation selection;
- renderer-owned sampler ownership;
- SGB/IMX/VHF transform semantics;
- BODY physics semantics;
- persistent vehicle transform production;
- input or camera production;
- Vulkan shader translation or runtime world-matrix upload.

## Result

An ordinary Silverstone material texture can no longer enter a playable native
Vulkan child bundle solely because its logical path matches. The exact texture
identity already produced by the renderer binding must agree with the exact IR
resource identity before DDS decode and bundle construction proceed.
