# Phase 609 — archive-invariant runtime pipeline candidate groups

## Motivation

Phase 608 narrows runtime/static shader candidates with complete observed draw
ranges. Production output still reports many static bindings because identical
IMB payloads are repeated across the Silverstone Era3 Drift, GrandPrix,
International and National archives.

Those archive copies are distinct source bindings, so they must remain distinct
for runtime instance attribution. They are nevertheless the same decoded mesh
content and can be grouped diagnostically without inventing instance identity.

## Content-group identity

Each surviving pipeline candidate is grouped by:

- exact IMB payload SHA-256;
- primitive index;
- source first index, index count and primitive count;
- exact BMT SHA-256;
- shader family;
- source-derived stream-0 vertex stride;
- ordered IMB vertex-property contract;
- matched runtime vertex/pixel shader hashes.

Archive name and IMB path are intentionally excluded from the group identity
and retained as members of the group.

If IMB SHA-256 is unavailable, the binding index is added to the key so
unrelated candidates can never collapse accidentally.

## Report additions

Each pipeline row now exposes:

- `candidate_content_group_count`;
- `candidate_content_status`;
- `candidate_content_groups[]`, including member binding indices, archives
  and IMB paths.

The summary adds:

- single-content-candidate pipeline/draw counts;
- distinct candidate content-group count;
- candidate content-group count distribution.

## Boundary

A single content group means that all surviving static bindings describe the
same source content contract. It does **not** identify which archive instance
was used at runtime and does not satisfy resource identity, same-instance
identity, shader admission or render admission.

The existing Phase 572/574 exact runtime proof gates remain unchanged.
