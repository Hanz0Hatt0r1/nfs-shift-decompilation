# Phase 658 — IR raw payload integrity before native Vulkan scene admission

## Playable-slice blocker reduced

Phase 657 closed the metadata identity join for ordinary Silverstone material
textures:

```text
renderer resource path + SHA-256
→ exact IR manifest row
→ DDS decode
→ Vulkan child bundle
```

The same Phase 580 scene builder already selected each IMB geometry row by exact
archive + logical path + SHA-256.

One consumer-side gap remained in both paths: after selecting the exact manifest
row, `native_scene_vulkan_set.py` opened `row.raw` and decoded its current bytes
without recalculating SHA-256. A stale or modified extracted payload could
therefore disagree with the manifest identity while the metadata row itself still
passed exact selection.

Phase 658 closes that gap before any native geometry or texture decode:

```text
exact IR manifest row
→ persistent raw path
→ read current bytes
→ SHA-256(current bytes) == manifest row SHA-256
→ decode IMB / DDS
→ Vulkan bundle construction
```

## Fail-closed raw verification

`src/scene/native_scene_vulkan_set.py` now routes IR-backed IMB and ordinary DDS
payloads through one reusable `_read_verified_raw_payload()` gate.

The gate requires:

- the manifest row to contain a raw payload path;
- the path to resolve to an existing file;
- the manifest SHA-256 to be a canonical 64-character hexadecimal digest;
- the file to be readable;
- the SHA-256 of the bytes read from disk to equal the manifest SHA-256.

The consumer does not attempt a decode when any of these checks fail.

New blockers include:

```text
imb-resource:raw-payload-sha256-mismatch
texture:sN:raw-payload-sha256-mismatch
```

and equivalent `raw-payload-missing`, `manifest-sha256-invalid`, or
`raw-payload-read-failed:*` reasons where applicable.

## Provenance output

Ready scene children expose the recalculated IMB payload digest:

```text
resource_raw_sha256
resource_raw_identity_sha256_match = true
```

Ordinary material texture source rows expose:

```text
raw_sha256
raw_identity_sha256_match = true
```

The set boundary records:

```text
imb_ir_raw_payload_sha256_revalidated = true
material_2d_dds_ir_raw_payload_sha256_revalidated = true
ir_raw_payload_sha256_revalidated_before_decode = true
```

This is a consumer integrity check, not a new resource identity convention. The
manifest identity remains authoritative; Phase 658 verifies that the persisted
artifact still contains those exact bytes at the point where Vulkan admission
consumes it.

## External resource boundary unchanged

Phase 658 applies only to resources selected through the extracted IR manifest.
It does not change renderer-owned resource ownership or substitute retail files
for runtime evidence:

- external `sampler2D` remains governed by the Phase 589 snapshot contract;
- external `samplerCube s3` remains governed by the Phase 593 cube snapshot
  contract or its existing explicitly admitted source;
- the optional global environment cube path is not reclassified as an IR
  resource;
- no sampler register, shader permutation, scene instance, or runtime resource
  identity is inferred from file similarity.

## Regression coverage

`tests/test_native_scene_vulkan_set.py` now verifies that:

1. a byte-identical IMB manifest payload reaches the existing Vulkan bundle path
   and reports an exact raw SHA match;
2. a modified IMB raw file is rejected before neutral geometry decode;
3. a byte-identical ordinary DDS reports an exact raw SHA match;
4. a modified DDS raw file is rejected before texture decode;
5. the existing external sampler behavior remains unchanged.

`tests/test_phase657_native_scene_material_texture_identity.py` now uses real DDS
content hashes for its ready fixtures, preserving Phase 657 path/SHA semantics
while making them compatible with the stricter Phase 658 consumer gate.

## Ownership boundary

Phase 658 is Process 3 resource/render admission only. It does not change:

- BODY identity or bind semantics;
- native physics scheduling or fixed-step ordering;
- input processing;
- camera-state production;
- `VehicleWorldMatrix` production or its already-closed Vulkan transport;
- renderer-owned snapshot identity;
- shader permutation selection.

## Result

An exact manifest row is no longer sufficient if the persisted extracted payload
has drifted. Silverstone IMB geometry and ordinary material DDS bytes must still
match their exact manifest SHA-256 immediately before native Vulkan scene
construction.