# Phase 571 — IMB runtime attribution handoff

Phase 570 proves exact Silverstone IMB resource identity and primitive draw
ranges. Phase 571 closes two remaining static prerequisites for a true
same-instance D3D9 matcher:

1. source-backed vertex-declaration descriptors;
2. lossless preservation of every static VS/PS candidate hidden behind a
   deduplicated prefilter hash.

## Declaration descriptors

The IMB ranking audit now retains the source Type/Usage/Channel triples decoded
by `SHIFT.IMBNeutralGeometry/1` as:

`property_descriptors = [{id, words:[type, usage, channel]}, ...]`.

These are the same source-backed descriptor words already used by the MEB/D3D9
declaration-correlation path.

The ranking stage does not translate Usage ordinals itself. Runtime evidence
still requires the independently recovered D3D9 usage-ordinal map.

## Lossless target deduplication

Phase 568 intentionally deduplicates runtime prefilter targets by the strongest
observable identity. In the Silverstone production corpus this commonly means a
pixel shader SHA-256.

Several static candidates may share that pixel hash while differing in vertex
shader, pair hash or permutation identity. A prefilter target is therefore not
itself a complete attribution candidate.

Phase 571 preserves all contributing static candidates in:

`target.candidate_variants[]`.

Each variant carries:

- permutation identity SHA-256;
- VS+PS pair byte SHA-256;
- vertex shader byte SHA-256;
- pixel shader byte SHA-256;
- FXO source location and program offset;
- pair-selection state;
- exact/static-evidence flag.

Aggregate pair/vertex/permutation fields on the deduplicated target are emitted
only when all contributing variants agree. Otherwise they remain null.

This keeps Phase 569 prefilter behavior unchanged while making later
same-instance narrowing lossless.

## Runtime resource evidence set

The new contract:

`SHIFT.IMBRuntimeResourceEvidenceSet/1`

is implemented in:

`src/scene/imb_runtime_resource_evidence.py`.

It groups binding targets by exact:

`archive + IMB path + decoded IMB SHA-256`.

Each resource row contains:

- source Type/Usage/Channel declaration descriptors;
- all primitive binding indices for that IMB;
- exact primitive draw ranges;
- shader-family identity;
- a `SHIFT.IMBRuntimeResourceEvidence/1` adapter containing
  `resource`, `resource_sha256` and `property_descriptors`.

Those field names are deliberately compatible with the existing
`D3D9RuntimeBindingEvidence/1` resource/declaration correlation code.

The adapter explicitly records:

`meb_equivalence = false`.

Reusing the runtime evidence schema does not imply that IMB and MEB are the
same serialized container.

## Fail-closed boundary

The handoff is not ready if any binding lacks:

- Phase 570 exact resource identity;
- Phase 570 exact draw range;
- source declaration descriptors;
- a capture-ready shader target.

Bindings grouped under the same exact IMB identity must agree on declaration
descriptors.

## Result

The first Silverstone runtime-attribution pipeline is now structurally:

`IMB ranking`
→ `runtime shader target set`
→ `raw D3D9 shader prefilter`
→ `IMB runtime resource evidence`
→ `D3D9 runtime binding evidence`
→ `same-instance shader-variant matcher`.

The first four static/capture-preparation layers are implemented.

## Next

Implement the final matcher. For each runtime draw it must require:

- exact IMB path/SHA match;
- valid bound D3D9 declaration whose records cover the IMB descriptors;
- exact primitive `first_index/index_count`;
- same-instance gate covering that draw;
- observed VS/PS hashes matching exactly one preserved
  `candidate_variants[]` entry.

A pixel-only hit may keep a draw as a candidate, but it must not be promoted to
an exact retail permutation.
