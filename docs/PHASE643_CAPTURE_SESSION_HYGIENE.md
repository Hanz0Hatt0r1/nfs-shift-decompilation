# Phase 643 — capture-session identity and stale-artifact hygiene

Repeated retail SDF probe runs previously reused the same output directory
without an explicit session boundary. JSONL evidence is append-only and frame
snapshots use deterministic filenames, so a reused directory could mix stale
runtime evidence from an older run with a new capture.

Phase 643 makes one prepared output directory represent one fresh capture
session.

## Session identity

Every launcher preparation generates a new opaque 128-bit hexadecimal
`capture_session_id`.

`probe_manifest.json` records the session under:

- `capture_session.format = SHIFT.SDFRuntimeProbeCaptureSession/1`;
- `capture_session.id`;
- `capture_session.single_session_output = true`;
- the exact generated evidence files removed before the new session.

The generated `attach.gdb` passes the same identifier to
`sdf-probe --session-id ...`.

The GDB probe stamps `capture_session_id` onto every JSON/JSONL evidence
payload, including relation mutation, frame entry, builtin/provider solve,
scalar reset, provider reset-effect and post-solve records.

## Stale-artifact cleanup

After the retail executable passes the existing PE/SHA validation, launcher
preparation removes only known generated capture artifacts:

- relation mutation JSONL and timeline JSON;
- frame-entry, builtin-solver and provider-solver snapshots;
- scalar-reset and provider-reset-effect JSONL;
- the previous deterministic evidence ZIP.

Host-local inputs and unrelated files are preserved. In particular,
`SHIFT.exe`, `attach.gdb`, `probe_manifest.json` and arbitrary user files
are not part of the cleanup set.

If executable validation is blocked, old capture evidence is left untouched.

## GDB fail-closed guard

The GDB command independently checks the output directory before installing
breakpoints. If any generated evidence artifact is already present, the probe
refuses to start rather than appending into an ambiguous session.

Manual GDB use without an explicit `--session-id` still receives a fresh
session id. Reinstalling the probe resets the shared runtime event sequence,
scalar-reset counter and last-frame state before new breakpoints are armed.

## Evidence boundary

Phase 643 changes capture provenance and output hygiene only.

It does not:

- infer mutation gameplay semantics;
- admit relation-state mutation to the native scheduler;
- synthesize missing retail evidence;
- change solver/reset/provider numerical behavior.

An authentic full-mode retail capture is still required before the existing
Phase 637–641 evidence chain can authorize any further runtime integration.
