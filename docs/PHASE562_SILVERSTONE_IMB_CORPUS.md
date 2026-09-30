# Phase 562 — Silverstone Era3 IMB corpus closure

Phase 562 validates the Phase 560–561 IMB path against the supplied production
Silverstone Era3 corpus instead of only synthetic fixtures.

## Corpus

Input:

`Silverstone_Era3_.zip`

SHA-256:

`5423f5a0356e664a504f90c812e32bbbd4e2a0abe83c546fdc658305661a1e2f`

The archive contains four visual BFFs and four Physics BFFs. The visual archives
contain 427 `.imb` resources in total:

- Drift: 117;
- GrandPrix: 103;
- International: 99;
- National: 108.

The Physics BFFs contain no `.imb` resources.

Exact per-archive hashes and aggregate results are committed in
`evidence/silverstone_era3_imb_corpus.json`.

## Result

All **427 / 427** production IMB resources decode through the recovered
v0.4 grammar with:

- zero decode failures;
- version `0.4.0.0` for every resource;
- zero trailing bytes after the final primitive record;
- 96,872 vertices;
- 428 primitives;
- 105,336 triangles;
- 92 resources with bone blocks/palettes.

The only observed Type/Usage/Channel property IDs are:

`200, 460, 220, 240, 250, 130, 231, 580, 310`.

Every one is already handled by `SHIFT.IMBNeutralGeometry/1`. Therefore the
Silverstone production corpus does not reveal a new vertex-stream semantic gap
for the first native track slice.

Observed source layouts reduce to four exact property sets:

- 192 resources: `200,460,220,130`;
- 82 resources: `200,460,220,240,250,130`;
- 61 resources: `200,460,220,240,250,130,231`;
- 92 resources: `200,460,220,240,250,130,580,310`.

426 resources contain one primitive and one contains two.

## Reusable audit

`tools/audit_imb_corpus.py` now accepts BFF files or ZIPs and emits
`SHIFT.IMBCorpusAudit/1`.

It uses the repository's existing BFF Type 0/1/2 extraction path and the
Phase 560 neutral adapter, so future track corpora can be checked without a
special Silverstone script.

Example:

```bash
python tools/audit_imb_corpus.py \
  Silverstone_Era3_.zip \
  -o out/silverstone-imb-audit.json \
  --require-all-ready
```

Unknown source-backed vertex streams are preserved/deferred by the geometry
adapter; the corpus audit reports them but does not reinterpret them.

## Boundary

This phase proves binary geometry coverage for the supplied Silverstone Era3
IMB corpus. It does **not** prove:

- every referenced MTX/BMT/FX/FXO resolves to a draw-ready material;
- runtime SceneGraph transform-update history for MatrixNumber instances;
- visibility/streaming scheduling;
- native Vulkan image parity.

Those are the next vertical-slice gates.
