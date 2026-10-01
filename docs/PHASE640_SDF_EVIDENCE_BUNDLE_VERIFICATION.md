# Phase 640 — portable SDF evidence bundle verification

Phase 639 produces deterministic `sdf_capture_evidence.zip` archives. Phase
640 adds an independent verifier that treats every received archive as
untrusted input.

## Verification contract

`verify_sdf_runtime_probe_evidence_bundle(...)` emits:

`SHIFT.SDFRuntimeProbeEvidenceBundleVerification/1`.

The verifier independently checks:

- valid ZIP structure;
- exactly one `evidence_manifest.json`;
- no duplicate entries;
- root-only safe entry names;
- no path traversal;
- exact manifest format/version;
- manifest file count;
- no duplicate manifest rows;
- allowed capture-file names only;
- no undeclared archive entries;
- no declared-but-missing entries;
- required mutation/timeline files;
- fixed entry order;
- stored compression;
- fixed 1980 timestamp;
- fixed 0644 regular-file mode;
- exact byte size for every evidence file;
- exact SHA-256 for every evidence file;
- exact archive policy;
- Phase 637 timeline format;
- agreement between manifest and timeline readiness/status.

## Readiness layers

The verifier keeps three states separate:

- `ready`: archive integrity/structure verification passed;
- `package_ready`: Phase 639 package declared its required core inputs valid;
- `capture_ready`: Phase 637 timeline itself is ready.

`evidence_ready` is true only when all three are true.

A structurally authentic bundle may therefore verify successfully while still
containing a legitimately blocked retail capture.

## Launcher self-verification

The full explicit-PID launcher now verifies the ZIP it just built before
reporting success. Full-mode success therefore requires:

1. GDB return code 0;
2. Phase 637 timeline ready;
3. Phase 639 bundle ready;
4. Phase 640 independent verification ready.

The launcher reports verification readiness/errors alongside the archive
identity.

## CLI

```bash
python tools/verify_sdf_solver_capture_bundle.py \
  sdf_capture_evidence.zip
```

Exit code is 0 for integrity-ready archives and 2 otherwise.

## Regression coverage

Phase 640 includes tests for:

- valid Phase 639 archives;
- valid integrity with a blocked capture;
- payload tampering;
- manifest/timeline readiness forgery;
- extra executable entries;
- path traversal;
- non-deterministic ZIP metadata;
- missing/corrupt archives;
- launcher self-verification success/failure.

## Evidence boundary

Integrity verification does not authorize native scheduler behavior. It only
proves that a portable evidence archive is internally consistent with the
Phase 639 manifest and the included Phase 637 timeline.
