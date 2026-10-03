# Phase 622 — exact material texture candidate join

Phase 622 continues the fail-closed renderer evidence chain after Phase 620.
It attacks only material candidates that remain unresolved after exact numeric
BMT -> CTAB -> draw-local constant correlation.

## Inputs

The stage consumes:

- `SHIFT.IMBMaterialConstantCandidateJoin/1` from Phase 620;
- `SHIFT.D3D9TargetDrawLocalEvidence/1`;
- `SHIFT.IMBFXOPairProvenance/1` from Phase 619;
- the original BFF/ZIP corpus.

No original game execution and no new runtime capture are required.

## Proof chain

For each surviving material candidate the stage reconstructs:

```text
exact BMT payload SHA
-> BMT shader + texture parameter
-> exact FX source path and bytes
-> FX sampler name / texture parameter relation
-> Phase 619 verified exact FXO VS+PS pair
-> draw-local reflected sampler name/register
-> exact DDS path and raw payload SHA
-> DDS header-derived D3D9 resource descriptor
-> runtime texture binding/creation descriptor
```

The important distinction is between **positive identity** and **negative
contradiction**.

### Positive identity

A material texture is positively identified only when the historical runtime
evidence carries both:

- `resource_path` equal to the exact BMT-referenced DDS path; and
- `resource_sha256` equal to the raw DDS payload SHA-256.

Only this produces `exact-resource-identity-match`.

### Descriptor comparison

DDS headers provide source-backed values for dimensions, mip count, resource
type, and D3D9 pixel format where the format is representable from the legacy
DDS header.

If a captured texture creation descriptor disagrees with one of those known
values, the candidate receives an exact descriptor contradiction. This is safe
negative evidence because the referenced DDS could not have created that
observed resource shape.

If all available descriptor fields agree, the result is only:

`descriptor-compatible-not-identity`

It is **not** a positive resource match. Width/height/format similarity, object
pointer identity, creation frequency, and file ordering are never promoted to
proof.

## Candidate policy

Phase 620 constant contradictions remain eliminated. The exception is the
Phase 620 `material-constant-conflict-no-survivor` state, where Phase 620
explicitly retained the original set; Phase 622 preserves that policy and
reconsiders all candidates.

A Phase 622 draw becomes `single-candidate-by-exact-material-textures` only
when:

1. exactly one surviving candidate has complete positive DDS resource identity;
2. every other surviving candidate is exactly contradicted; and
3. no candidate remains merely unobserved or descriptor-compatible.

One exact match plus one insufficient candidate stays ambiguous.

If descriptor contradictions remove all but one candidate, but that survivor
has no exact path+SHA runtime identity, the stage reports:

`single-survivor-by-texture-contradiction-unproven`

The survivor is not render-admitted.

## Duplicate provenance

FX and DDS resources are indexed by normalized exact resource path and raw
payload SHA-256.

Byte-identical copies from multiple archives are collapsed as one content
identity while retaining every occurrence. Distinct payloads under the same
exact path are preserved as ambiguity; archive/file order is never used to
choose one.

## DDS coverage

The header parser currently exposes D3D9 format identity for:

- FOURCC formats such as DXT1/DXT3/DXT5 directly from the DDS FOURCC value;
- common legacy RGB layouts (`A8R8G8B8`, `X8R8G8B8`, `A8B8G8R8`,
  `X8B8G8R8`, `R5G6B5`, `A1R5G5B5`, `A4R4G4B4`).

Unknown header encodings remain `format = null`, which removes that field from
comparison instead of guessing.

## Capture boundary

Phase 622 does not request another capture. The existing capture already gives
texture creation/binding descriptors and reflected sampler registers.

Portable texture path/SHA remains a conditional future observation only for
candidates that survive all offline BMT/FX/DDS and descriptor contradictions.
The correct next step is to run this stage on the retained Silverstone evidence
before deciding whether any texture payload/path observation is truly required.

## CLI

```bash
python src/scene/imb_material_texture_candidate_join.py \
  out/silverstone_material_constant_candidate_join.json \
  out/d3d9_target_draw_local_evidence.json \
  out/silverstone_fxo_pair_provenance.json \
  out/silverstone_material_texture_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

The JSON result is `SHIFT.IMBMaterialTextureCandidateJoin/1` and remains a
candidate-narrowing artifact rather than render admission.
