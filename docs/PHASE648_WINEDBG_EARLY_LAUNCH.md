# Phase 648 — WineDbg early-launch SDF probe

Phase 647 established that a long mid-session relation-timeline capture can
observe hundreds of solver frames without seeing `FUN_00757d2c`. The remaining
setup/runtime provenance question therefore needs the probe armed before
vehicle/race setup, not a wider attach window.

## Early-launch mode

The launcher now supports:

```bash
python tools/run_sdf_solver_probe.py /path/to/SHIFT.exe \
  --output out/relation-early \
  --launch-under-winedbg \
  --relation-timeline-only \
  --stop-after-relation-mutation \
  --capture-frames 900
```

This mode starts:

```text
winedbg --gdb --no-start --port <loopback-port> SHIFT.exe ...
```

and separately starts GDB with:

```text
set tcp auto-retry on
set tcp connect-timeout <seconds>
target remote 127.0.0.1:<loopback-port>
source .../gdb_sdf_solver_probe.py
sdf-probe ...
continue
```

WineDbg creates the Win32 debuggee under the debugger and waits for the GDB
frontend. Therefore the probe command is installed before the launcher issues
its first debugger `continue`. This removes the previous process-discovery and
mid-session attach race from the capture path.

## Provenance

`probe_manifest.json` records:

- `startup_mode = "winedbg-gdb-proxy"`;
- the selected loopback GDB proxy port;
- `startup_ordering =
  "debuggee-created-under-winedbg-and-held-before-first-continue"`.

This is startup/control provenance only. It does not claim that a relation
mutation occurs during setup and it does not promote relation-state scheduling
without authentic captured evidence.

## Fail-closed behavior

Early launch requires a direct validated retail `SHIFT.exe`. ZIP input remains
valid for prepare/validation workflows but is rejected for early launch because
an extracted executable in the capture directory is not a complete game
runtime.

The launcher also blocks on:

- missing WineDbg or GDB;
- invalid proxy ports;
- invalid GDB connect timeout;
- a nonzero GDB session result;
- a WineDbg proxy that does not exit cleanly after the GDB frontend disconnects;
- the existing Phase 637–647 timeline, session, bundle, verification and replay
  gates.

WineDbg output is written to `winedbg_gdb_proxy.log` as host-local diagnostic
information. It is not promoted into the portable evidence bundle.

## Compatibility

The existing explicit `--attach-pid` path remains unchanged. The two target
modes are mutually exclusive.

Optional game arguments can be forwarded with repeated `--game-arg=VALUE`.
A fixed port can be supplied with `--winedbg-port`; otherwise an ephemeral
loopback port is allocated. GDB connection retries default to 30 seconds and can
be changed with `--gdb-connect-timeout`.
