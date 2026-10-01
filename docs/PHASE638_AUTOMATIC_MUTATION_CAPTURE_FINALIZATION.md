# Phase 638 — automatic relation-mutation capture finalization

Phase 637 can validate a completed full-mode retail capture, but previously the
operator had to invoke the timeline analyzer as a second manual command. Phase
638 closes that operational gap in the normal attach path.

## Automatic full-mode handoff

When `tools/run_sdf_solver_probe.py` is invoked with `--attach-pid` in full
mode, the flow is now:

```text
prepare validated probe bundle
  → attach GDB to the explicit PID
  → run the Phase 635/636 capture until the GDB session returns
  → execute Phase 637 correlation
  → write relation_state_mutation_timeline.json
  → return success only if both GDB and the correlation report are ready
```

The generated post-capture file is:

`relation_state_mutation_timeline.json`

with format:

`SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1`.

The launcher emits a final machine-readable summary containing:

- GDB return code;
- automatic-finalization flag;
- timeline output path;
- Phase 637 readiness;
- mutation count;
- timeline-anchor count;
- correlation summary;
- correlation errors.

A successful GDB process is not enough to return success when Phase 637 is
blocked. Conversely, a ready timeline does not hide a failed GDB session.

## Provider-only behavior

`--provider-only` intentionally preserves its previous behavior. That mode
does not install the relation-state mutation observer or frame-entry anchor, so
Phase 637 correlation is not applicable and automatic finalization is skipped.

The probe manifest now makes this explicit:

- full mode:
  `automatic_timeline_correlation=true`;
- provider-only:
  `automatic_timeline_correlation=false`.

## Import-path hardening

The GDB probe and launcher now add `src/physics` explicitly to `sys.path`
instead of depending on project-root `sitecustomize.py` having run in the
embedding interpreter.

This matters for GDB's embedded Python, whose startup path can differ from a
normal Python process even when the repository root is available later.

## Regression coverage

Phase 638 tests:

- persistence of a ready Phase 637 report;
- automatic finalization after a successful full-mode GDB attach;
- failure when Phase 637 is blocked;
- failure when GDB returns nonzero even if correlation is ready;
- provider-only finalization suppression;
- full/provider-only post-capture manifest metadata.

## Evidence boundary

Automatic finalization reduces operator steps; it does not create missing
runtime evidence.

A real full-mode capture still has to produce the mutation and timeline files
required by Phase 637. Missing, inconsistent or unclassified evidence remains
blocked and causes the launcher to return exit code 2.

No native relation-state mutation is scheduled by this phase.
