# Phase 463 — specialized-provider GDB capture

## Goal

Phase 463 extends the existing `tools/gdb_sdf_solver_probe.py` so the runtime probe can observe the provider backend instead of silently stopping at the builtin-solver path.

## Breakpoints

Two source-backed provider solve entries are installed:

- provider 0: `FUN_007c7200`;
- provider 1: `FUN_007cdfc0`.

At each provider solve entry, the probe captures:

- the complete packed factor workspace;
- the static row-pointer table;
- the provider output vector;
- frame/physics metadata when a frame-entry event was observed.

A `gdb.FinishBreakpoint` is then armed for the same function frame and writes the corresponding post-solve snapshot after the provider returns.

## Output

Files are written as:

`provider_pre_<provider>_<hit>.json`

`provider_post_<provider>_<hit>.json`

They conform to `SHIFT.SpecializedProviderCaptureRuntime/1` from Phase 462.

## Lifecycle safety

Return breakpoints are retained by their provider entry breakpoint and are explicitly deleted when `sdf-probe` is reinstalled. This prevents stale finish hooks from surviving a probe restart.

## Scope boundary

The probe captures raw provider state; it does not convert packed workspace bytes into a logical 40×40/34×34 matrix. That conversion remains a separate evidence problem. No provider class name or physical unit is inferred.

The resulting snapshots can now feed Phase 460/461 differential tooling once a real provider capture exists.
