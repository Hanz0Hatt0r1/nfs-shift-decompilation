# Phase 658 — materialized Silverstone DDS integrity before Vulkan decode

## Playable-slice blocker reduced

Phase 657 joins ordinary Silverstone material textures by exact producer
`path + SHA-256` against the extracted IR manifest. The selected manifest row
then points at a materialized `raw/...` payload that Phase 580 decodes and sends
to the Vulkan child-bundle builder.

For current IR produced by `shift_importer.py build-ir`, those identities are
stronger than a path claim:

```text
decoded BFF resource bytes = data
sha256 = SHA256(data)
decoded_sha256 = SHA256(data)
raw/<digest> = the same data bytes
```

Before Phase 658, Phase 580 recorded the actual raw-file SHA in diagnostics but
did not compare it with the manifest identity before `decode_dds()`. A modified
materialized DDS could therefore survive the Phase 657 manifest join and only be
interpreted later as texture input.

Phase 658 closes that integrity gap for the modern content-addressed IR used by
the playable pipeline.

## Exact integrity chain

For an ordinary material sampler carrying an explicit modern IR
`decoded_sha256`, Phase 580 now requires:

```text
RenderResources texture SHA
        ==
IR manifest sha256
        ==
IR manifest decoded_sha256
        ==
SHA256(materialized raw DDS bytes)
```

The checks happen before DDS parsing and before Vulkan packet construction.

## Fail-closed reasons

If the explicit decoded identity disagrees with the already Phase-657-joined
resource identity, the draw blocks with:

```text
texture:sN:ir-decoded-sha256-mismatch
```

If the actual materialized raw bytes disagree with that decoded identity, the
draw blocks with:

```text
texture:sN:raw-payload-sha256-mismatch
```

The corrupted bytes are not passed to `decode_dds()`.

## Compatibility boundary

Historical synthetic/legacy IR fixtures may contain only `sha256` and omit the
newer explicit `decoded_sha256` field. Phase 658 does not reinterpret those rows;
they retain the Phase 657 path+manifest-SHA behavior.

The current production `shift_importer.py build-ir` path emits both fields from
the same decoded payload and writes those bytes into the content-addressed raw
store. Therefore the first playable Linux pipeline receives the full Phase 658
integrity check without changing the legacy IR ABI.

Per admitted source, `texture_sources` now also records:

```text
decoded_sha256
raw_sha256
raw_identity_sha256_match
```

For explicit modern IR, `raw_identity_sha256_match` must be `true` for a ready
material texture.

The set boundary records:

```text
material_2d_dds_explicit_decoded_sha256_revalidated = true
material_2d_dds_raw_payload_sha256_revalidated_when_explicit = true
```

## External sampler boundary unchanged

This phase applies only to ordinary material-backed DDS resources. It does not
weaken or replace the renderer-owned resource contracts:

- external `sampler2D` still requires Phase 589 snapshot evidence when needed;
- external `samplerCube s3` still requires Phase 593 cube snapshot evidence;
- no retail DDS is substituted for an unobserved runtime snapshot.

## Regression coverage

`tests/test_phase658_native_scene_raw_dds_integrity.py` verifies:

1. exact producer/manifest/decoded/raw SHA identity is admitted;
2. modifying the materialized DDS after manifest creation is rejected before
   decode;
3. drift between `manifest.sha256` and `manifest.decoded_sha256` is rejected.

The full existing Phase 580 suite remains responsible for scene ordering,
runtime provenance, world-transform serialization and external-sampler policy.

## Ownership boundary

Phase 658 is Process 3 resource integrity only. It does not change:

- BFF decompression semantics;
- shader permutation selection;
- external sampler ownership;
- SGB/IMX/VHF transform semantics;
- BODY physics or scheduling;
- persistent vehicle transform production;
- camera/input behavior;
- Vulkan shader translation or world-matrix upload.

## Result

For modern playable IR, the ordinary Silverstone DDS bytes actually consumed by
Phase 580 are now cryptographically joined back to the exact renderer resource
identity before they can enter a native Vulkan draw bundle.
