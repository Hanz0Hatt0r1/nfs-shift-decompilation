# Phase 656 — exact BMW VHF source identity for playable placement

## Playable-slice blocker removed

Phase 645 recovers the canonical BMW body placement from the retail VHF
hierarchy and converts the hierarchy matrix into the already established SVWT
row-vector convention. Phase 654 separately revalidates the MEB/BMT/FX/DDS
resources selected for the playable BMW render slice.

One resource provenance gap remained on the critical path:

```text
exact BMW primary BFF
  -> vehicles/bmw_m3_e36/bmw_m3_e36.vhf
  -> body hierarchy matrix
  -> playable vehicle world transform
```

`SHIFT.BMWVHFBodyWorldTransform/1` previously recorded the archive basename and
VHF logical path, but not the exact VHF entry identity that produced the matrix.
A downstream consumer therefore could not distinguish the proven retail VHF
payload from a same-name substitution using the transform artifact alone.

Phase 656 makes that source resource identity explicit and fail-closed.

## Exact VHF identity

Before the hierarchy is accepted, `build_bmw_vhf_body_world_transform()` opens
the already selected primary BMW BFF and requires exactly one entry whose
normalized logical path equals:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

The transform source now records:

```yaml
source:
  archive: BMW_M3_E36.bff
  vhf_resource: vehicles/bmw_m3_e36/bmw_m3_e36.vhf
  vhf_entry:
    archive: BMW_M3_E36.bff
    archive_sha256: <exact primary-BFF SHA-256>
    entry_index: <exact BFF entry index>
    path: vehicles/bmw_m3_e36/bmw_m3_e36.vhf
    decoded_sha256: <decoded VHF payload SHA-256>
    decoded_size: <decoded byte count>
```

The primary archive itself has already passed the Process 3 retail archive
identity gate before Phase 645/656 is invoked. The additional fields bind the
matrix artifact to one exact resource occurrence inside that admitted archive.

## Duplicate rule

VHF source selection uses the same fail-closed semantic-identity rule as the
other playable resources:

```text
0 exact logical occurrences -> MISSING
1 exact logical occurrence  -> eligible
2+ logical occurrences      -> AMBIGUOUS
```

Byte-identical duplicate VHF payloads are still ambiguous. Archive order and
"first occurrence" are never selection authority.

## Downstream admission

`apply_bmw_vhf_body_world_transform()` now requires the VHF provenance before it
can attach the matrix to `SHIFT.BMWMaterialSliceSet/1`.

It validates that:

- the VHF archive name is present and agrees with the transform source;
- the archive SHA-256 is present;
- the entry index is non-negative;
- the VHF logical path equals the transform's `vhf_resource` exactly after path
  normalization;
- the decoded VHF SHA-256 is present;
- the decoded VHF byte count is positive.

A transform artifact with missing or malformed VHF identity cannot seed the
playable scene.

## What does not change

Phase 656 is provenance-only Process 3 work. It does **not** change:

- the VHF hierarchy evaluation algorithm;
- the Phase 645 column-vector -> SVWT row-vector transpose;
- the selected body node or body MEB identity;
- BODY identity/bind semantics;
- physics scheduling or native physics execution;
- `VehicleWorldMatrix` production or transport;
- camera/view state;
- shader or material selection.

The closed `VehicleWorldMatrix -> Vulkan` infrastructure boundary remains
unchanged.

## Regression coverage

`tests/test_bmw_vhf_body_world_transform.py` verifies that:

- a ready transform carries exact VHF source provenance;
- malformed VHF logical-path provenance is rejected;
- downstream transform application rejects missing VHF provenance;
- existing matrix/body identity behavior is unchanged.

`tests/test_bmw_vhf_body_world_transform_integration.py` builds a real mini-BFF
and verifies that:

- archive SHA-256 is computed from the actual BFF bytes;
- the exact VHF BFF entry index/path are recorded;
- decoded VHF SHA-256/size are recorded from the actual payload;
- two logical-equivalent VHF entries are rejected even when their bytes are
  identical.

## Result

The playable BMW placement chain now has exact provenance for the resource that
actually defines its static VHF transform. The remaining vehicle placement work
is no longer hidden behind a name-only VHF source reference; any later blocker
must come from renderer admission or from the separately owned dynamic runtime
state, not from ambiguity in the Phase 645 VHF resource identity.
