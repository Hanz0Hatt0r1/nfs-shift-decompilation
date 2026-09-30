# Phase 570 — IMB runtime identity/provenance handoff

Phase 569 can reduce a raw D3D9 capture to draws whose active shaders intersect
the Silverstone target whitelist, but runtime attribution still requires exact
resource, declaration and primitive identity.

Phase 570 closes the static side of that handoff.

## Complete target provenance

`SHIFT.IMBRuntimeShaderTargetSet/1` previously deduplicated capture targets by
their strongest runtime-observable identity. For the current Silverstone corpus
that usually means pixel shader SHA-256.

That is correct for prefiltering, but several distinct static VS/PS candidates
can share one pixel shader hash. Collapsing those candidates without retaining
their individual pair/vertex identities would lose information required by a
later same-instance match.

Phase 570 therefore preserves every contributing static candidate under:

`target.candidate_variants[]`.

Each variant keeps:

- permutation identity SHA-256;
- pair byte SHA-256;
- vertex byte SHA-256;
- pixel byte SHA-256;
- FXO source location;
- pair-selection state;
- exact/static evidence flag.

The deduplicated target remains the prefilter key. Variant identities remain the
attribution candidates.

If all variants agree on a stage/pair hash, that value is also exposed on the
deduplicated target. If they disagree, the aggregate field is left null rather
than choosing one.

## Exact IMB identity in ranking

`SHIFT.IMBMaterialShaderRanking/1` now retains for every primitive binding:

- archive name;
- IMB resource path;
- decoded IMB SHA-256;
- IMB entry index;
- exact primitive `first_index` / `index_count` / triangle count;
- primitive type word;
- source Type/Usage/Channel descriptors.

These are derived from the same source-backed IMB payload used for the Phase
566–568 material/shader ranking.

## Runtime resource handoff

The new contract is:

`SHIFT.IMBRuntimeResourceEvidenceSet/1`

implemented by:

`src/scene/imb_runtime_resource_evidence.py`.

It groups primitive bindings by exact:

`archive + IMB path + IMB SHA-256`.

For each IMB it preserves:

- property descriptors needed for D3D declaration correlation;
- all primitive draw ranges belonging to that resource;
- binding indices and shader-family identity;
- a small `SHIFT.IMBRuntimeResourceEvidence/1` adapter suitable as resource
  identity input to the existing D3D9 runtime evidence builder.

The adapter explicitly records:

`meb_equivalence = false`.

It reuses the generic fields already consumed by the runtime evidence code
(`resource`, `resource_sha256`, `property_descriptors`) without claiming
that IMB and MEB are the same serialized format.

## Fail-closed gates

A resource handoff is blocked if any primitive binding lacks:

- exact IMB SHA-256;
- resource path/archive identity;
- a valid triangle draw range;
- Type/Usage/Channel property descriptors;
- a capture-ready shader target.

Bindings sharing the same exact IMB identity must also agree on declaration
descriptors.

## Why this phase is separate

Shader prefiltering and same-instance attribution are different claims.

Phase 569 answers:

> Did the capture use shader bytes that belong to the static Silverstone target
> surface?

Phase 570 supplies the evidence needed to ask:

> Was that shader active on a draw using this exact IMB resource, this exact
> declaration shape and this exact primitive index range?

Only the second question can support a retail permutation attribution.

## Next

The next step is a per-primitive runtime matcher over
`SHIFT.D3D9RuntimeBindingEvidence/1`:

`exact IMB resource identity + declaration descriptors + primitive draw range
+ same-instance draw gate + observed VS/PS hashes → surviving static candidate
variant(s)`.

The matcher must remain fail-closed when the runtime draw does not identify one
static pair/permutation uniquely.
