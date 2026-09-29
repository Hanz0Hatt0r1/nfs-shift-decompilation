# Phase 514 — specialized-provider probe contract validation

## Goal

Close the source-level preflight gap before an authentic specialized-provider GDB capture. The preflight now verifies that the supplied probe script actually implements the capture contract used by the Phase 462–513 provider tooling.

## Probe contract

| Marker | Required evidence |
|---|---|
| python-gdb | import gdb |
| sdf-command | sdf-probe command |
| provider-pre-capture | provider_pre_ output path |
| provider-post-capture | provider_post_ output path |
| scalar-reset-capture | scalar_reset_events.jsonl |
| provider-snapshot | build_provider_capture_payload |

A missing marker is a fail-closed preflight error. The validator never imports or executes the GDB probe outside an actual GDB session.

## CLI output

`tools/preflight_specialized_provider_capture.py` now exposes `probe_script_exists` and `probe_script_valid`. The complete `provider_capture_preflight.json` keeps the detailed marker result.

## Artifact verification

The supplied `shift.zip` contains a PE32/i386 `SHIFT.exe` whose SHA-256 matches the retail fingerprint already enforced by the PE validator:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

This proves the current executable artifact is valid for the source-backed probe targets. It does not create runtime evidence.

## Boundary

Passing Phase 514 proves only that the capture inputs and probe source are structurally compatible with the existing capture contract.

The remaining gate is an authentic 32-bit Wine + GDB runtime session that reaches the provider frame and produces matching pre/post snapshots and scalar-reset events.

## Verification

The phase adds deterministic tests for accepting a probe containing all required markers, rejecting unrelated Python scripts, and exposing the probe-validation state through the CLI.
