# Phase 639 — portable SDF runtime capture evidence bundle

Phase 638 automatically finalizes a full-mode retail capture with the Phase 637
timeline correlator. Phase 639 turns the resulting capture directory into one
portable deterministic evidence archive.

## Output

A successful full-mode capture now also produces:

`sdf_capture_evidence.zip`

The archive contains only capture evidence and an internal manifest:

`SHIFT.SDFRuntimeProbeEvidenceBundle/1`.

The bundle includes matching files from these evidence families:

- `relation_state_mutation_events.jsonl`;
- `relation_state_mutation_timeline.json`;
- `frame_entry_*.json`;
- `pre_solve_*.json`;
- `provider_pre_*_*.json`;
- `provider_post_*_*.json`;
- `scalar_reset_events.jsonl`;
- `provider_reset_effects.jsonl`;
- `post_solve_*.json`.

The following host-local or copyrighted inputs are deliberately excluded:

- `SHIFT.exe`;
- `attach.gdb`;
- `probe_manifest.json`;
- `provider_capture_preflight.json`.

## Deterministic archive identity

The archive builder uses:

- lexicographic entry order;
- ZIP stored mode instead of variable compression;
- timestamp `1980-01-01T00:00:00` for every entry;
- fixed mode `0644`;
- SHA-256 and byte size for every evidence payload.

Identical capture bytes therefore produce an identical ZIP byte stream and
archive SHA-256.

The internal `evidence_manifest.json` records every included path, evidence
kind, size and SHA-256.

## Capture readiness remains separate

Packaging does not convert blocked evidence into ready evidence.

The bundle manifest exposes both:

- `ready`: whether the portable package itself has the required core files and
  a valid Phase 637 timeline format;
- `capture_ready`: the actual Phase 637 timeline readiness.

A blocked Phase 637 report can still be packaged successfully for inspection;
its `capture_ready` remains false.

## Required core files

Package readiness requires at minimum:

- `relation_state_mutation_events.jsonl`;
- `relation_state_mutation_timeline.json`.

Missing core files or a timeline format mismatch make package `ready=false`,
but the builder still writes the archive containing whatever valid evidence is
available.

## CLI

Standalone packaging is available with:

```bash
python tools/package_sdf_solver_capture.py \
  out/sdf-solver-capture \
  -o out/sdf_capture_evidence.zip
```

The command exits 0 only when package readiness is true, otherwise 2.

## Automatic launcher integration

After a full-mode `run_sdf_solver_probe.py --attach-pid` session:

1. GDB capture completes;
2. Phase 637 writes `relation_state_mutation_timeline.json`;
3. Phase 639 writes `sdf_capture_evidence.zip`;
4. the launcher reports archive path, size, SHA-256, file count and package
   errors.

Full-mode launcher success now requires:

- GDB return code 0;
- Phase 637 timeline ready;
- Phase 639 bundle ready.

Provider-only mode does not create this relation-state evidence bundle because
it intentionally lacks the mutation/frame-entry evidence required by Phase 637.

## Evidence boundary

Phase 639 changes transport only. It does not infer event timing, repair missing
capture data, or schedule relation-state mutation in the native runtime.
