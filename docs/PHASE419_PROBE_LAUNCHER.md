# Phase 419 — SDF runtime probe launcher

The capture gate now has a deterministic preparation layer around the existing PE validator and GDB probe.

## Prepare mode

`tools/run_sdf_solver_probe.py SHIFT.exe --output out/sdf-solver-capture` validates the supplied retail binary against the known SHA-256/PE/prologue contract and writes two files:

- `probe_manifest.json` with validation, executable identity and capture expectations;
- `attach.gdb` with `source`, `sdf-probe` and `continue` commands using absolute paths.

## Attach mode

Passing `--attach-pid PID` attaches GDB only to the explicitly supplied process and loads the generated probe command file. The launcher never guesses a process and never patches `SHIFT.exe`.

The runtime launcher also exposes a small API for callers that already manage Wine: `launch_retail()` starts the executable under an explicit Wine binary, while `build_attach_command()` builds the exact GDB invocation for a known PID.

## Environment behavior

The launcher fails closed when the retail PE check fails or when Wine/GDB is unavailable. It does not synthesize solver values. A successful prepare step therefore proves only that the target binary and probe configuration are compatible; numeric solver equality still requires a real retail capture.
