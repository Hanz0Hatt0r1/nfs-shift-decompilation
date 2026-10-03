# Phase 635 — self-bootstrap renderer production

Phase 635 connects the renderer evidence stages that were previously available
as separate offline tools into one fail-closed production path.

The new entry point is:

```text
tools/run_silverstone_renderer_self_bootstrap_production.py
```

It never launches the original game and does not request a new capture.

## Dependency order

The runner executes the existing proof stages in dependency order:

```text
historical raw D3D9 JSONL
+ exact/full SHIFT.IMBRuntimeShaderTargetSet/1
+ PE evidence or static PE image
        |
        v
Phase 630 raw capture bootstrap
        |
        +--> regenerated draw-local evidence
        +--> regenerated runtime capture pipeline
        |
        v
Phase 634 ambiguity regeneration
        |
        +--> Phase 603 runtime signature catalog
        +--> IMB corpus audit
        +--> Phase 606 pipeline candidates
        +--> Phase 610 geometry candidates
        +--> Phase 611 material candidates
        +--> Phase 613 pointer observations
        +--> Phase 615 geometry-pointer candidates
        +--> Phase 617 draw-local static candidates
        +--> Phase 618 ambiguity audit
        |
        v
Phase 633 renderer base-audit regeneration
        |
        v
Phase 619-626 renderer production
```

The top-level manifest is:

```text
SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1
```

## Bundle role after Phase 635

The following reports are no longer selection-authoritative bundle inputs in the
self-bootstrap path:

- `SHIFT.D3D9TargetDrawLocalEvidence/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`;
- `SHIFT.IMBDrawLocalAmbiguityAudit/1`;
- `SHIFT.D3D9RendererRequirementAudit/1`.

They are regenerated from their source evidence. If a bundle contains copies,
those copies are only canonical-JSON cross-checks.

A matching copy confirms exact identity. An absent copy is allowed. A differing
copy blocks production with a canonical mismatch. When several bundle variants
exist, regeneration may identify one only by exact canonical equality; filename,
archive order, occurrence count and ranking never select a winner.

## Runtime shader target boundary

Phase 635 still requires the **full**:

```text
SHIFT.IMBRuntimeShaderTargetSet/1
```

including its per-binding candidate variants.

The committed compact Phase 568 evidence:

```text
evidence/silverstone_era3_runtime_shader_targets.json
```

has format:

```text
SHIFT.IMBRuntimeShaderTargetSetEvidence/1
```

and is intentionally not accepted as a substitute for the full target set.
The compact report contains enough byte hashes for capture prefiltering, but it
does not contain the per-binding candidate variants required by Phase 606 and
other exact attribution stages.

Phase 635 therefore fails closed when only the compact report is available.
Regenerating the full target set from source corpus evidence is the next offline
bootstrap frontier; weakening Phase 606 to accept the compact report would not
be valid evidence recovery.

## Object candidate join boundary

`SHIFT.SGBRuntimeObjectCandidateJoin/1` remains optional at the start of the
pipeline.

It is passed to Phase 619-626 production only when the Phase 628 bundle index
resolves one exact normalized report. No ambiguous object-candidate variant is
selected.

The report becomes materially required only if Phase 624 proves a repeated
scene-resource draw and Phase 625 needs scene-instance discrimination. If that
gate is not reached, absence of the object join is not an early production
blocker.

## Static PE entry point

`tools/run_silverstone_renderer_pe_image_hybrid_production.py` now delegates to
Phase 635 after statically decoding the PE image.

The outer compatibility contract remains:

```text
SHIFT.SilverstoneRendererPEImageHybridProductionRun/1
```

but its inner production manifest is now:

```text
SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1
```

The PE file is still read only as bytes through
`d3d9_pe_evidence.analyze_d3d9_pe_image_file`; it is never executed.

## Proof semantics

Phase 635 is orchestration only. It does not change the proof strength of any
underlying stage.

In particular:

- ranking or frequency is never proof;
- a single static candidate is not render admission;
- descriptor equality is not portable texture or geometry identity;
- capture-local pointer equality is not portable resource identity;
- missing historical capture events do not imply recapture;
- the Phase 634 conflicting-FX-path rule remains fail-closed;
- canonical handoff mismatch blocks instead of silently preferring regenerated
  or bundled content;
- Phase 625 still requires source-backed scene-instance evidence when repeated
  placements remain.

## Capture boundary

Phase 635 adds no new capture requirement.

Known historical gaps remain conditional downstream observations:

- `SetSamplerState` history;
- VB/IB payload bytes;
- portable runtime resource path + SHA-256;
- texture snapshots.

None of those observations is required merely to regenerate the Phase 603→618
ambiguity graph or the base requirement audit. They should only be requested if
a later exact survivor proves that specific missing observation is necessary.

Therefore:

```text
original game execution required: no
new capture required: no
```

## Remaining offline frontier

After Phase 635, the largest remaining manually supplied renderer bootstrap
contract is the full `SHIFT.IMBRuntimeShaderTargetSet/1`.

The next step should reconstruct that full target set from the existing
IMB/BMT/FX/FXO source corpus and existing shader/material contracts, retaining
all candidate variants and exact provenance. The compact Phase 568 report may be
used as a byte-hash cross-check, but not as a replacement for missing per-binding
candidate evidence.
