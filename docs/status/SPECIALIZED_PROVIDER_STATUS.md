# Specialized provider status

## Current boundary

`SHIFT.exe.c` source-shape + dispatch/selector evidence + runtime provider capture
are joined by `SHIFT.SpecializedProviderCaptureHandoffRuntime/1`.

## Handoff contract

The handoff contract and Phase 501 mutation-correlation layer:

- keeps `observed_provider_id` runtime-authoritative;
- attaches a source-derived provider solver program only when provider ids match;
- preserves the full capture-bundle contract as a separate evidence layer;
- validates source-derived solver programs independently of the capture;
- remains blocked when the runtime provider id is absent or mismatched;
- correlates packed-workspace change addresses with source-derived factor edges while preserving alias sets.

Use:

`python tools/verify_specialized_provider_capture_handoff.py SHIFT.exe.c <capture-dir> --observed-provider-id <0|1> --reset-events scalar_reset_events.jsonl`

For pre/post mutation correlation:

`python tools/compare_specialized_provider_mutations.py --pre provider_pre_0_000001.json --post provider_post_0_000001.json --source SHIFT.exe.c --provider 0 -o mutation_correlation.json`

Optional `-o` writes the complete handoff manifest.

## Numeric boundary

This is a linkage contract, not numeric proof. Retail/provider numerical equivalence
still requires a real pre/post runtime frame and differential comparison of the
captured packed workspace/output vectors.

## Current next step

Capture a real provider frame, verify the bundle, then use the handoff and Phase 501
correlation report to classify observed packed-workspace mutations against the
source-derived execution program.
