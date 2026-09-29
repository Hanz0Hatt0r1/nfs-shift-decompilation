# Phase 515 — low-stop specialized-provider capture mode

## Goal

Reduce debugger intervention during an authentic specialized-provider capture. The existing full probe installs breakpoints for the builtin solver and per-frame entry path in addition to provider events. Phase 515 adds an explicit provider-only mode.

## CLI

`python tools/preflight_specialized_provider_capture.py SHIFT.zip out/provider-capture --probe-script tools/gdb_sdf_solver_probe.py --provider-only`

or:

`python tools/run_sdf_solver_probe.py SHIFT.exe --output out/provider-capture --provider-only --attach-pid <PID>`

The generated `attach.gdb` contains `sdf-probe <output> --provider-only`.

## Provider-only behavior

The mode omits builtin `FUN_007b0f20` solver and `FUN_007b4110` post-solve breakpoints and does not install the per-frame `FUN_007b3f40` frame-entry breakpoint.

Provider solve entries remain installed for both known providers. Scalar-reset and provider-reset probes remain installed so the existing provider capture and reset-effect schemas can still be populated.

## Boundary

Provider-only captures intentionally omit per-frame backend observations. Provider pre/post snapshots remain runtime-authoritative, while frame metadata may be absent.

This mode is intended for cases where the full probe's per-frame debugger stops cause excessive simulation disturbance. It does not change provider schema semantics or claim numeric parity by itself.
