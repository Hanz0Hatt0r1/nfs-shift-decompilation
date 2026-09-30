# Phase 595 — pre-admission runtime OBJECT candidate join

Phase 594 can solve the current MultiMatrix root from one exact runtime-observed
world matrix for a selected MatrixNumber slot.

That solve still needs an independent way to determine **which SGB OBJECT** a
runtime observation may belong to before RenderBinding admission exists.

Phase 595 adds that pre-admission narrowing layer.

## Contract

New contract:

`SHIFT.SGBRuntimeObjectCandidateJoin/1`

implemented by:

`src/scene/sgb_runtime_object_candidate_join.py`.

Inputs:

- `SHIFT.SGBScenePlacement/1`;
- `SHIFT.SGBObjectRenderHandoffSet/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`;
- the analyzed IR `manifest.json`.

## Runtime resource side

For each Phase 573 runtime resource result the join requires:

- exact runtime archive name;
- normalized IMB path;
- decoded SHA-256;
- ready D3D9 same-instance gate;
- one exact matching archive/path/SHA row in the IR manifest.

A runtime resource that cannot be revalidated against the IR manifest remains
blocked.

## SGB side

Scene candidates are built before RenderBinding admission from the source-backed
placement/wrapper identity:

- FLAT/SUMM → SUMM wrapper source record;
- PART/NODE → NODE wrapper source record;
- recursive OBJECT path inside that wrapper;
- logical OBJECT resource reference;
- transform mode / MatrixNumber state;
- placement spatial evidence.

No RenderBinding/admission `binding_index` is used.

## Join rule

A runtime IMB resource is compared to SGB candidates by normalized logical
resource path after the runtime archive/path/SHA has already been independently
validated against the IR manifest.

This produces zero, one or multiple SGB OBJECT candidates.

The result records:

- exact runtime resource identity;
- all matching placement/wrapper/object paths;
- MatrixNumber and numeric-world readiness per candidate;
- whether the logical candidate set is unique.

## Important archive boundary

Current SGB placement/handoff contracts do **not** preserve the source BFF
archive identity of the SGB-side resource reference.

Therefore:

`sgb_source_archive_identity_available = false`.

An exact runtime archive/path/SHA plus one logical SGB candidate is useful
narrowing evidence, but Phase 595 does not relabel that as an exact
OBJECT/runtime attribution.

## Fail-closed behavior

The join is not ready when:

- scene placement/capture inputs are not ready;
- runtime archive/path/SHA is missing;
- runtime same-instance resource evidence is not ready;
- exact runtime resource identity is absent from the IR manifest;
- no SGB OBJECT candidate references the runtime logical path.

Multiple SGB OBJECT candidates are allowed as an explicit ambiguous candidate
set. In that case the contract may be ready, but
`identity_complete = false`.

## No promotion

Phase 595 explicitly does not authorize:

- MultiMatrix root solving;
- a world matrix;
- RenderBinding admission;
- draw admission.

Even a unique logical scene candidate remains pre-admission evidence.

## CLI

```bash
python shift_importer.py sgb-runtime-object-candidate-join \
  out/scene-placement.json \
  out/object-handoffs.json \
  out/silverstone-runtime-attribution.json \
  out/ir \
  out/runtime-object-candidates.json
```

## Next

The next transform step needs an independent witness that can promote one
candidate OBJECT without relying on a later RenderBinding binding index.

Possible witnesses include exact SGB-side archive provenance, independently
recovered runtime wrapper/object identity, or a source-backed spatial/runtime
transform correlation strong enough to distinguish repeated logical resources.

Only after that witness exists may Phase 594 root reconstruction be attached to
a previously blocked MatrixNumber OBJECT.
