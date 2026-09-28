# Phase 504 — specialized-provider runtime capture preflight

## Goal

Phase 504 adds a machine-readable preflight for the first real specialized-provider
runtime capture. It validates the retail executable and probe script, checks that
Wine and GDB are installed, and verifies that GDB exposes its Python interpreter.

Contract:

`SHIFT.SDFRuntimeProbePreflight/1`

## CLI

    python tools/preflight_specialized_provider_capture.py \\
      SHIFT.zip out/provider-capture \\
      --probe-script tools/gdb_sdf_solver_probe.py

The input may be `SHIFT.exe` or an archive containing exactly one `SHIFT.exe`.
The preflight also creates the existing launcher manifest and `attach.gdb`.

## Checks

- retail SHA-256 and probe-function PE/prologue validation;
- probe script existence;
- Wine and GDB discovery;
- Wine and GDB version query;
- GDB Python execution using a deterministic marker.

## Local evidence

The uploaded `shift.zip` contains `SHIFT.exe`, and the executable is PE32/i386.
The current analysis environment does not provide `wine` or `gdb`, so an authentic
runtime capture cannot be executed here. Phase 504 makes that missing capability
an explicit preflight blocker instead of allowing a partially prepared capture to
look runnable.

## Scope boundary

The preflight never launches `SHIFT.exe`, never guesses a process PID, and never
attaches GDB. Passing preflight still does not prove that the complete installed
game content/Pakfiles are available or that a provider frame will occur.
The runtime provider identity, packed-workspace mutations and numeric parity remain
capture evidence.
