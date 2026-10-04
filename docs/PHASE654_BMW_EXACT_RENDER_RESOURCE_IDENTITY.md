# Phase 654 — exact BMW playable render resource identity

## Playable-slice blocker reduced

The Phase 644 playable scene already admits the exact retail BMW primary,
cockpit and RENDER archives by canonical archive SHA-256.  The older Phase 533
BMW material helpers, however, predate the current Process 3 fail-closed resource
policy: some local resolvers may accept a byte-identical duplicate occurrence or
fall back from an exact shader path to a basename.

That behavior is still useful for historical analysis, but it is not sufficient
proof for the first playable Linux slice.

Phase 654 therefore inserts an independent admission gate between:

```text
Phase 533 complete BMW body material admission
and
Phase 645 VHF body transform -> Phase 643 playable composition
```

The new contract is:

```text
SHIFT.BMWPlayableRenderResourceIdentityGate/1
```

## What is revalidated

The gate does not rediscover the vehicle dependency graph.  It consumes the
resource provenance already emitted by every ready Phase 533 body primitive and
revalidates the resources that were actually selected:

- body MEB;
- primitive BMT;
- BMT-referenced FX source;
- DDS sources materialized into the render slice.

For each logical path, the already SHA-admitted BMW primary, cockpit and RENDER
archives are scanned together.  Playable admission requires exactly one matching
logical resource occurrence across that exact archive set.

The selected occurrence is then checked against the Phase 533 claim:

```text
archive
entry index, when the legacy provenance contains it
payload SHA-256
exact logical path
```

Legacy DDS provenance did not retain an entry index.  Phase 654 does not guess
one: it derives the index only after proving that the DDS logical path has exactly
one occurrence in the exact admitted archive set, and records the observed index
in the gate output.

## Shader path rule

The shader path carried by `material_binding.shader` must equal the selected
`shader_source.path` after slash/case normalization.

Therefore a historical resolver result such as:

```text
BMT shader: bodywork.fx
selected source: render/shaders/bodywork.fx
```

is blocked even when the basename and bytes happen to match.  The production BMW
BMT evidence already carries the exact logical path `render/shaders/bodywork.fx`.

External shader files are not admissible in the Phase 654 playable resource gate;
the playable path must remain rooted in the already admitted retail archives.

## Duplicate rule

For MEB/BMT/FX/DDS:

```text
0 occurrences -> MISSING
1 exact occurrence -> eligible
2+ occurrences -> AMBIGUOUS
```

This is true even when all duplicate payload bytes are identical.  Byte equality
is not semantic resource identity, and archive order or the first duplicate is
never selection authority.

## FXO cache boundary

The retail BMW/cockpit archives intentionally contain repeated shader-cache FXO
copies.  Phase 654 does not reinterpret those copies as a resource identity.
The renderer continues to consume the exact selected shader/permutation **program
byte identity** established by the existing material/shader gates.

Accordingly:

- byte-identical FXO copies may remain a byte-equivalence class;
- Phase 654 does not select one FXO occurrence as the semantic source;
- byte equivalence is explicitly not promoted to resource identity.

This preserves the useful Phase 536 program deduplication without carrying its
older "one logical retail resource" wording into the playable resource identity
contract.

## Playable integration

`src/scene/native_playable_scene_bootstrap.py` now applies Phase 654 immediately
after a ready Phase 533 body admission.  The gate is embedded in the existing
`SHIFT.BMWBodyMaterialAdmission/1` stage as:

```text
playable_render_resource_identity_gate
```

If Phase 654 blocks, the admission is downgraded before:

- VHF body transform materialization;
- Phase 643 track+vehicle composition;
- `scene_set_ready`.

No new coordination report is required.

## Ownership boundary

Phase 654 is Process 3 resource identity only.  It does not change:

- BODY identity or bind semantics;
- physics scheduling;
- `VehicleWorldMatrix` production or transport;
- camera-state production;
- VHF/BODY frame interpretation;
- shader permutation selection criteria.

## Regression coverage

`tests/test_bmw_playable_render_resource_identity.py` freezes:

- unique exact resource admission;
- rejection of byte-identical duplicate shader occurrences;
- rejection of shader basename substitution;
- payload SHA-256 drift rejection;
- external shader source rejection;
- claimed entry-index substitution rejection.

`tests/test_native_playable_scene_bootstrap.py` verifies that Phase 654 is a hard
playable gate and that VHF/Phase 643 work does not execute after it blocks.

## Result

For the canonical BMW body path, a ready Phase 533 material slice is no longer
enough by itself to seed the playable scene.  The exact retail MEB/BMT/FX/DDS
resource identities selected by that slice must first be unique and
provenance-consistent inside the exact admitted BMW/Cockpit/RENDER archive set.
