# Phase 637 — source-bootstrap renderer production

Phase 637 removes the remaining mandatory renderer JSON handoffs from the
preferred offline production entry point.

The new entry point is:

```text
tools/run_silverstone_renderer_source_bootstrap_production.py
```

Its normal input surface is now source/raw data rather than previously prepared
renderer reports:

- historical D3D9 JSONL;
- source BFF/ZIP corpus;
- either static PE image bytes or previously generated PE evidence;
- optional report bundles used only as canonical cross-checks.

## Dependency graph

The preferred production path is now:

```text
BFF/ZIP corpus
  -> Phase 636 full runtime shader target regeneration
     SHIFT.IMBRuntimeShaderTargetSet/1
        |
        v
historical raw D3D9 JSONL + PE evidence/static PE image
  -> Phase 635 self-bootstrap
       -> Phase 630 raw capture bootstrap
       -> Phase 634 Phase 618 ambiguity regeneration
       -> Phase 633 base requirement-audit regeneration
       -> Phase 619-626 renderer production
```

The Phase 637 manifest is:

```text
SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1
```

## Full shader targets are no longer a manual input

When `--runtime-shader-targets` is omitted, Phase 637 runs Phase 636 against the
provided corpus and passes the resulting full
`SHIFT.IMBRuntimeShaderTargetSet/1` to Phase 635 as an explicit exact input.

The committed compact Phase 568 evidence is used by default as the Phase 636
semantic projection cross-check. It is never used to synthesize missing
candidate variants.

An explicit full target set may still be supplied for diagnostic compatibility.
It must:

- have format `SHIFT.IMBRuntimeShaderTargetSet/1`;
- report `capture_ready=true`;
- contain at least one binding target.

Compact `SHIFT.IMBRuntimeShaderTargetSetEvidence/1` is rejected as a prebuilt
full target set.

## Renderer report bundles are optional

Phase 635 originally consumed at least one ZIP because the older Phase 628
indexer treats `bundle:no-inputs` as an error. In Phase 637 those ZIPs are only
cross-check sources, so requiring one from the user would be an artificial
handoff dependency.

When no `--bundle` is supplied, Phase 637 creates an internal empty ZIP and
passes it to Phase 635. This ZIP:

- contains no JSON reports;
- contains no evidence;
- cannot satisfy any proof gate;
- exists only to represent “no bundle cross-check supplied” to the older
  indexer.

The Phase 635 missing-report results are then handled exactly as designed: the
regenerated draw-local, capture-pipeline, Phase 618 and base-audit reports are
used, while absent bundle copies simply have no canonical cross-check.

If real bundle inputs are supplied, they remain exact canonical cross-check
sources. A mismatch still blocks.

## Preferred CLI shape

A source-driven run can now be expressed without renderer handoff JSON:

```text
python tools/run_silverstone_renderer_source_bootstrap_production.py \
  --capture-jsonl shift_d3d9_capture.jsonl \
  --pe-image SHIFT.exe \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip \
  --output-dir out/renderer-source-bootstrap
```

`SHIFT.exe` is read only as PE bytes by the existing static PE evidence path. It
is not launched.

Optional old report bundles can be added only for cross-checking:

```text
  --bundle out.zip
```

## Compatibility

`--runtime-shader-targets` remains available as an explicit full-target override.
This allows old workflows to be compared against the new regenerated source
path without changing downstream Phase 635 behavior.

`tools/run_silverstone_renderer_pe_image_hybrid_production.py` remains available
as the older compatibility entry point. Phase 637 itself already accepts
`--pe-image`, so the preferred source-driven path does not depend on changing
that compatibility wrapper.

## Proof boundary

Phase 637 does not add inference or ranking:

- Phase 636 preserves tied top-rank shader candidates;
- compact Phase 568 evidence is cross-check only;
- Phase 635 regenerated reports remain authoritative over bundle copies;
- optional bundles are canonical cross-check only;
- the internal empty bundle is explicitly non-evidence;
- missing historical runtime observations do not imply recapture;
- the original executable is never run.

Therefore:

```text
manual full shader target JSON required: no
manual renderer report bundle required: no
original game execution required: no
new capture required: no
```

## Remaining renderer frontier

The principal remaining optional handoff is
`SHIFT.SGBRuntimeObjectCandidateJoin/1`, and even that is only required when
Phase 624 reaches a repeated-resource placement for which Phase 625 needs
scene-instance discrimination.

The next offline step is therefore to trace the existing source-backed SGB
placement/object-handoff builders and determine whether the object-candidate
join can be regenerated from the same corpus plus the already regenerated
runtime capture pipeline.
