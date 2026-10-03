# Phase 629 — direct renderer bundle production

Phase 629 removes the last manual handoff between the Phase 628 report-bundle
index and the Phase 627 Silverstone renderer production runner.

It adds no renderer proof semantics. The Phase 628 bundle index remains the
only authority that may select reports from a ZIP handoff.

## Tool

`tools/run_silverstone_renderer_bundle_production.py` executes:

```text
report ZIP bundle(s)
→ Phase 628 embedded-format/canonical-payload index
→ normalized exact report inputs
→ Phase 627 production runner
→ Phase 619/620/622/623/624/625/626
```

The normal production use with the existing handoff is now one command:

```bash
python tools/run_silverstone_renderer_bundle_production.py \
  out.zip \
  --output-dir out/silverstone_renderer_bundle_production \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

No manual extraction or filename-based report selection is required.

## Selection boundary

Phase 629 never opens ZIP entries to choose reports itself. It delegates that
operation to `index_silverstone_renderer_report_bundle.index_report_bundles`.
Therefore all Phase 628 rules remain unchanged:

- embedded `format` is the report type identity;
- canonical JSON SHA-256 is the report content identity;
- filename is provenance only;
- archive order is not proof;
- frequency is not proof;
- byte/content-equivalent duplicate occurrences are retained as one content
  identity;
- different canonical payloads for the same report format are ambiguous.

If the bundle index is blocked or ambiguous, Phase 629 does **not** start the
production runner.

## Runtime shader targets

`SHIFT.IMBRuntimeShaderTargetSet/1` is optional in the bundle.

When the Phase 628 index resolves that report, its normalized exact report is
passed to Phase 627. Otherwise Phase 629 uses the same committed
`evidence/silverstone_era3_runtime_shader_targets.json` default already used by
the Phase 627 CLI.

No filename or similarly named file is substituted.

## Object candidate join

`SHIFT.SGBRuntimeObjectCandidateJoin/1` remains optional at bundle-index time.
Phase 627 decides whether it is actually required:

- if Phase 624 reports no repeated placements, Phase 625 is `not-needed`;
- if repeated placements exist and the object-candidate report is absent,
  production remains blocked on that existing offline input.

That blocker is not converted into a new-capture request.

## Output

The output root contains:

```text
inputs/
  silverstone_renderer_report_bundle_index.json
  <normalized Phase 628 reports>
production/
  silverstone_renderer_production_run.json
  <Phase 619-626 reports>
silverstone_renderer_bundle_production_run.json
```

The top-level report format is:

`SHIFT.SilverstoneRendererBundleProductionRun/1`.

It records whether bundle indexing was ready, whether production actually
started, the production result, renderer frontier summary, blockers, and paths
to both manifests.

## Fail-closed policy

Phase 629 preserves these boundaries:

- an indexing blocker prevents production from starting;
- a production blocker remains a production blocker;
- missing input is not candidate contradiction;
- descriptor compatibility is not resource identity;
- ranking is not proof;
- a missing historical capture event does not imply recapture;
- VB/IB `buffer_payload` remains only a last conditional fallback;
- the original game is never executed.

## Regression coverage

`tests/test_run_silverstone_renderer_bundle_production.py` covers:

- ready bundle → normalized reports → production runner;
- committed shader-target fallback when the bundle has no target-set report;
- exact embedded target-set report taking precedence over the fallback;
- distinct canonical payload ambiguity stopping before production;
- propagation of downstream Phase 627 blockers without reinterpretation.
