# Phase 515 — low-stop specialized-provider capture mode

## Goal

Reduce debugger intervention during an authentic specialized-provider capture. The full probe also installs builtin-solver and per-frame hooks; provider-only mode avoids those extra stops.

## CLI

`python tools/preflight_specialized_provider_capture.py SHIFT.zip out/provider-capture --probe-script tools/gdb_sdf_solver_probe.py --provider-only`

or:

`python tools/run_sdf_solver_probe.py SHIFT.exe --output out/provider-capture --provider-only --attach-pid <PID>`

The generated `attach.gdb` invokes `sdf-probe <output> --provider-only`.

## Provider-only behavior

The mode omits breakpoints for `FUN_007b3f40`, `FUN_007b0f20` and `FUN_007b4110`. It retains both specialized provider solve entries and the provider/scalar reset hooks.

Provider pointer conditions restrict scalar/provider reset stops to known provider vtables. Frame metadata may be absent because the per-frame entry breakpoint is not installed.

## Boundary

This is a debugger-intervention optimization only. It does not change provider storage schemas, provider identity rules or the numeric-equivalence evidence boundary.

## Verification

Regression coverage verifies the provider-only command generation, manifest mode propagation, source-level breakpoint selection and preflight pass-through.
