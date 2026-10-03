# Phase 618 — draw-local static ambiguity audit

Phase 617 establishes an exact runtime `resource-shape + geometry-generation`
join for all target draws, but a surviving static candidate set is still only
candidate evidence. Phase 618 classifies those surviving ambiguity sets without
ranking or choosing a winner.

## Production motivation

The Silverstone Phase 617 production report contains:

- 1,581 target draws;
- 1,581 exact `resource-shape + geometry` joins;
- 743 single-static-candidate draws;
- 838 ambiguous-static-candidate draws;
- 55 capture-local geometry identities;
- zero candidates rejected by the Phase 617 exact shader-byte contradiction
  gate.

The result means shader-byte contradiction is not the next useful generic gate.
The remaining work has to be split by what actually differs between the
surviving static candidates.

One observed ambiguity pattern is an LOD-named pair such as
`crowd_man_01_loda.imb` and `crowd_man_01_lodb.imb` sharing the same BMT,
primitive draw range, stride and pixel-shader evidence. The path naming is useful
for diagnostics, but it is not identity proof and Phase 618 never chooses one
LOD from the name.

## Input/output

`src/scene/imb_draw_local_ambiguity_audit.py` consumes:

- `SHIFT.IMBDrawLocalStaticCandidateJoin/1`.

It emits:

- `SHIFT.IMBDrawLocalAmbiguityAudit/1`.

Each ambiguous draw records:

- the surviving content-group set;
- compact static candidate metadata;
- distinct BMT count;
- distinct static shader-pair evidence count;
- distinct shader family, draw range, primitive index and stride counts;
- whether candidates are metadata-equivalent after portable IMB identity is
  removed;
- whether every candidate came from Phase 612 cross-VS donor recovery;
- a path-name-only LOD sibling diagnostic;
- the next evidence gate;
- the minimum useful offline/capture evidence for that class.

The report also groups repeated ambiguity sets and repeated geometry identities,
so a small number of unresolved candidate sets can be prioritized instead of
re-inspecting all 838 draws independently.

## Ambiguity classes

### `metadata-equivalent-lod-siblings`

All proof-relevant Phase 617 candidate metadata is equal after IMB/content/path
identity is removed, and every candidate path normalizes to the same terminal
`_lod*` family.

Next gate:

1. exact static scene/instance resource reference;
2. source-backed LOD selection metadata tied to that instance;
3. only if those offline proofs are unavailable, portable runtime resource
   identity or targeted stream-0 VB + IB payload equality.

The LOD name itself is never used to select a winner.

### `metadata-equivalent-geometry-alternatives`

Candidates have the same current proof contract but are not a recognizable
terminal `_lod*` path family.

The same scene-reference/portable-geometry identity gate applies.

### `material-distinct-candidates`

Surviving candidates differ in BMT SHA. These should be attacked offline first
through exact BMT shader-parameter/DDS contracts and draw-local
sampler/constant evidence. Descriptor similarity alone is not sufficient.

### `shader-provenance-distinct-candidates`

Candidates differ in recorded static VS/PS provenance. The next gate is exact
embedded FXO VS+PS byte-pair provenance. No FXO candidate is selected by rank,
family name or frequency.

### `mixed-static-metadata-candidates`

More than one static evidence dimension differs. The stage keeps the ambiguity
and asks the next stage to split candidates using exact source-backed fields.

## Cross-VS donor boundary

Phase 612 intentionally allowed a static donor VS mismatch when a sibling runtime
pipeline proved the same pixel shader and input layout. Phase 618 only reports
whether all or any surviving candidates use that recovery path. It does not turn
the mismatch into a rejection rule.

## Capture policy

Phase 618 is designed to prevent premature recapture.

The recommended order is:

1. exact offline material evidence where BMTs differ;
2. exact offline FXO pair provenance where shader provenance differs;
3. static scene/instance/LOD references for metadata-equivalent geometry
   alternatives;
4. only then targeted stream-0 VB + IB payload capture for the remaining exact
   geometry generations, or a portable runtime resource path/SHA event.

External texture snapshots are only useful when the unresolved class actually
requires texture content identity.

## Usage

```bash
python src/scene/imb_draw_local_ambiguity_audit.py \
  out/silverstone_d3d9_draw_local_static_candidate_join.json \
  out/silverstone_d3d9_draw_local_ambiguity_audit.json
```

Inspect the compact summary first:

```bash
python - <<'PY'
import json
p = 'out/silverstone_d3d9_draw_local_ambiguity_audit.json'
with open(p, encoding='utf-8') as f:
    d = json.load(f)
print(json.dumps(d['summary'], indent=2, ensure_ascii=False))
PY
```

Useful fields are:

- `ambiguity_class_counts`;
- `next_gate_counts`;
- `unique_ambiguous_candidate_set_count`;
- `ambiguous_geometry_pointer_identity_count`;
- `metadata_equivalent_except_imb_identity_draw_count`;
- `lod_path_diagnostic_draw_count`;
- `all_cross_vs_donor_ambiguous_draw_count`;
- `surviving_content_group_count_distribution`;
- `candidate_contract_count_distribution`.

## Non-claims

Phase 618 does not prove:

- retail IMB identity from one surviving candidate;
- LOD identity from a filename;
- BMT identity from shared texture descriptors;
- FXO permutation identity from ranking;
- scene-instance identity from capture-local pointers;
- render admission.
