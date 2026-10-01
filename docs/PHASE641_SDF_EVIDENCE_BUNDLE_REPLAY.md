# Phase 641 — portable SDF evidence bundle replay

Phase 640 verifies the integrity and internal consistency of a portable Phase
639 ZIP. Phase 641 independently replays the verified raw evidence through the
Phase 637 correlator and compares the recomputed report with the embedded
`relation_state_mutation_timeline.json`.

## Path-independent Phase 637 output

The Phase 637 analyzer no longer stores the host-local absolute
`capture_directory` path in its report.

That field was not part of the evidence semantics and prevented exact replay
inside a temporary directory. Removing it also prevents local filesystem paths
from leaking into portable evidence archives.

## Replay pipeline

```text
sdf_capture_evidence.zip
  → Phase 640 integrity verification
  → safe temporary materialization of declared evidence files
  → Phase 637 recomputation from raw mutation/frame/reset/solve artifacts
  → exact dictionary comparison with embedded timeline
```

The result format is:

`SHIFT.SDFRuntimeProbeEvidenceBundleReplay/1`.

## Readiness separation

Replay exposes:

- `ready`: verification passed and embedded/recomputed timelines match;
- `package_ready`: Phase 639 package readiness;
- `capture_ready`: embedded Phase 637 capture readiness;
- `evidence_ready`: all replay/package/capture gates are ready.

A blocked retail capture can therefore replay exactly while keeping
`evidence_ready=false`.

## Semantic mismatch detection

Phase 640 checks manifest-declared hashes and timeline readiness/status. A
modified timeline can be re-hashed into a modified manifest and remain
structurally self-consistent.

Phase 641 closes that gap by recomputing the Phase 637 report from the raw
evidence. Any semantic difference produces:

`embedded-timeline-replay-mismatch`.

The replay report publishes canonical SHA-256 values for both the embedded and
recomputed timeline dictionaries.

This is a reproducibility check, not a cryptographic authenticity signature:
an attacker able to replace both raw evidence and all derived artifacts can
still create a self-consistent new archive.

## Launcher self-replay

The full explicit-PID launcher now requires:

1. GDB capture success;
2. Phase 637 timeline readiness;
3. Phase 639 package readiness;
4. Phase 640 integrity verification;
5. Phase 641 exact replay.

Provider-only mode remains outside this relation-state evidence path.

## CLI

```bash
python tools/replay_sdf_solver_capture_bundle.py \
  sdf_capture_evidence.zip
```

Exit code is 0 when replay is exact and 2 otherwise.

## Evidence boundary

Replay proves deterministic derivation of the embedded timeline from the raw
captured artifacts. It does not prove external authenticity and does not
authorize native scheduler behavior.
