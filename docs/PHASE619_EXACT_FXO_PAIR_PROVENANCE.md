# Phase 619 — exact FXO VS/PS pair provenance

Phase 618 classifies unresolved Silverstone draw attribution without choosing a
candidate by rank. One class, `shader-provenance-distinct-candidates`, requires
an exact static proof that the recorded VS/PS hashes really come from concrete
embedded programs in the retail FXO corpus.

Phase 619 adds that offline proof layer:

`SHIFT.IMBFXOPairProvenance/1`.

## Why this stage exists

The existing IMB material shader ranking already records:

- FXO entry path;
- pixel-program offset;
- vertex-program offset;
- VS byte SHA-256;
- PS byte SHA-256;
- concatenated VS+PS pair SHA-256;
- shader permutation identity SHA-256.

However the ranking stage deduplicates byte-identical FXO payloads across the
input archives before material ranking. Its `candidate_file` therefore records
an FXO entry path but does not retain the complete archive-occurrence set.
Ranking is also intentionally not proof.

Phase 619 reopens the supplied offline corpus, finds every occurrence of each
candidate FXO entry path, parses the embedded shader programs again, and
recomputes all byte identities at the recorded offsets.

## Exact verification

For every candidate variant the verifier requires:

1. an explicit vertex-program offset;
2. an explicit pixel-program offset;
3. a VS blob at the vertex offset;
4. a PS blob at the pixel offset;
5. exact SHA-256 equality for the expected VS bytes;
6. exact SHA-256 equality for the expected PS bytes;
7. exact equality for pair/permutation hashes when those hashes were present in
   the input contract.

The pair hash is recomputed as:

```text
SHA256(vertex_program_bytes || pixel_program_bytes)
```

The permutation identity is independently rebuilt through the canonical
`build_shader_permutation_identity()` path.

A verified result has confidence `exact-byte-equality`.

## Duplicate provenance policy

The same FXO entry path may occur in more than one BFF. The stage never chooses
the first archive or first file occurrence.

If several occurrences contain the same verified bytes, the result is:

`content-equivalent-multiple-source-occurrences`.

Every archive/source occurrence is retained in the artifact. If only one
occurrence verifies, it is `exact-source-occurrence`. If none verify, the
candidate remains unresolved or contradictory rather than being rescued by
ranking.

## Phase 618 filter

With `--ambiguity-audit`, only VS/PS pairs referenced by Phase 618
`shader-provenance-distinct-candidates` are audited. Material-distinct and
geometry-only ambiguity classes are ignored by this stage.

If Phase 618 contains no shader-provenance-distinct rows, the result is
`no-shader-provenance-distinct-candidates`; this is not a request for another
capture.

## CLI

```bash
python src/scene/imb_fxo_pair_provenance.py \
  evidence/silverstone_era3_runtime_shader_targets.json \
  out/silverstone_fxo_pair_provenance.json \
  --corpus Silverstone_Era3_.zip \
  --corpus /path/to/RENDER.bff \
  --ambiguity-audit out/silverstone_d3d9_draw_local_ambiguity_audit.json
```

`--corpus` may point to a BFF directly or to a ZIP containing BFFs.

## Blocker accounting

This stage can close only the static side of exact shader provenance:

```text
candidate FXO entry
→ exact embedded vertex program
→ exact embedded pixel program
→ exact byte pair
→ all source archive occurrences
```

It does not prove that a particular scene object or primitive issued a runtime
draw. Runtime shader-use identity remains supplied by the capture-side
`CreateShader → SetShader → DrawIndexedPrimitive` evidence.

### Closed by existing data + tooling

- validation of ranking-produced VS/PS hashes against retail FXO bytes;
- validation of exact program offsets and stages;
- recovery of all matching source archive occurrences for a deduplicated FXO
  candidate;
- exact VS/PS pair provenance for Phase 618 shader-provenance ambiguity.

### Still separate blockers

- material-distinct candidate sets: require BMT/DDS/constant/sampler evidence;
- metadata-equivalent LOD/geometry alternatives: require scene/instance or exact
  geometry identity;
- exact runtime resource path for pathless capture objects;
- VB/IB payload equality when geometry identity cannot be closed offline.

### Data present but needing further tooling

The historical capture already contains exact shader creation bytes, bind/use
history, draw ranges, float constants, texture bindings and texture descriptors.
Those should continue to be exhausted offline before recapture is considered.

### Data actually absent from the historical capture

Existing audits establish that the historical Silverstone capture does not
contain buffer payload snapshots. It also lacks the newer optional portable
resource path/SHA and sampler-state/snapshot observations where those events are
not present.

None of those observations is required for Phase 619.

## Non-claims

Phase 619 does not:

- select a shader candidate because it ranks higher;
- collapse two different byte pairs into one candidate;
- choose one archive when identical FXO bytes exist in several archives;
- prove BMT/material identity;
- prove scene-instance identity;
- prove render admission.

If two exact byte-pair candidates remain, the result remains ambiguous.
