# Phase 654 — exact renderer PE evidence from the playable bundle

## Playable-slice blocker removed

After Phase 653, the playable entry point can consume a verified Phase 650
sampler capture-result bundle without manually passing the raw capture JSONL or
capture root. One renderer bootstrap path was still manual: the caller also had
to pass `--renderer-pe-evidence` or `--renderer-pe-image` even when the existing
renderer handoff bundle already contained the exact static PE report.

Phase 654 removes that path handoff for the selected Silverstone/BMW playable
bootstrap:

```text
renderer report bundle(s)
  -> embedded format inspection
  -> canonical JSON SHA-256 identity
  -> one SHIFT.PEImageEvidence/1 payload identity
  -> normalized d3d9_pe_evidence.json
  -> existing --renderer-pe-evidence input
  -> unchanged renderer reconstruction/admission chain
```

No PE image is executed and no new renderer proof semantics are introduced.

## Exact selection policy

`tools/index_silverstone_renderer_report_bundle.py` now recognizes the optional
format:

```text
SHIFT.PEImageEvidence/1
```

under the key `pe_evidence`.

The same Phase 628 selection policy is reused:

- ZIP entry filename is not selection authority;
- archive order is not selection authority;
- occurrence frequency is not selection authority;
- one canonical JSON payload is accepted;
- multiple byte/content-equivalent occurrences remain one payload identity;
- distinct canonical payloads are `AMBIGUOUS` and no PE output is normalized.

PE evidence is optional for the general bundle index. Therefore an ambiguous PE
copy does not invalidate a caller that already supplied an explicit PE selector.
It still cannot be used by the Phase 654 resolver.

## Playable bootstrap behavior

`tools/resolve_playable_renderer_pe_evidence.py` consumes renderer bundle(s) and
requires the `pe_evidence` row to be exactly resolved. It reloads the normalized
JSON, requires `SHIFT.PEImageEvidence/1`, recomputes its canonical SHA-256, and
requires that hash to equal the index identity.

`tools/bootstrap_playable_linux_slice.py` uses this resolver only when both of
these are absent:

```text
--renderer-pe-evidence
--renderer-pe-image
```

At least one `--renderer-bundle` must then be supplied and must contain exactly
one canonical PE evidence payload identity. The resulting normalized path is
fed into the already-existing lower-level bootstrap as
`--renderer-pe-evidence`.

An explicit PE selector remains authoritative and is never overwritten by bundle
content.

The playable report records the in-memory resolution under:

```text
stages.renderer_pe_bundle_resolution
artifacts.renderer_pe_evidence
artifacts.renderer_pe_bundle_index
```

and records that filename/archive order are not PE selection authority.

## Fail-closed cases

Phase 654 blocks before the expensive renderer reconstruction when:

- no explicit PE selector and no renderer bundle are supplied;
- the bundle contains no `SHIFT.PEImageEvidence/1`;
- distinct canonical PE evidence payloads are present;
- the normalized output is missing or unreadable;
- the normalized report format changes;
- the normalized canonical SHA-256 no longer matches the indexed identity.

It never chooses the first duplicate, a familiar filename, a more frequent
payload, or a payload that merely resembles the expected report.

## Ownership boundary

This is Process 3 resource/render bootstrap infrastructure only. It does not:

- identify or bind a BODY;
- change physics scheduling or runtime execution;
- produce `VehicleWorldMatrix`;
- reopen the closed `VehicleWorldMatrix -> Vulkan` transport boundary;
- produce camera/view state;
- execute the retail PE image;
- treat static PE evidence as runtime renderer admission;
- bypass shader/draw/material/sampler/scene admission gates.

## Regression coverage

`tests/test_phase654_playable_bundle_pe_evidence.py` verifies:

1. arbitrary ZIP filenames are accepted only because the embedded report format
   identifies the PE report class;
2. content-equivalent duplicate PE reports resolve to one canonical identity;
3. distinct PE payloads remain ambiguous and produce no normalized PE artifact;
4. the playable entry point injects the exact normalized PE evidence before the
   existing lower-level renderer validation;
5. an explicit PE selector bypasses auto-resolution and remains unchanged.

## Result

For a renderer handoff bundle that already contains exact PE evidence, the
playable resource/render command no longer requires a separate manual PE JSON
path. The remaining renderer blockers are evidence/admission blockers themselves,
not an avoidable path-plumbing step.
