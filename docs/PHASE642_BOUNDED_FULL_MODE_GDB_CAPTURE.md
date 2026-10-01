# Phase 642 — bounded full-mode GDB capture

The full SDF probe previously continued indefinitely after attachment. That is
useful for manual sessions, but it keeps the retail process under debugger
control until the user explicitly ends GDB and can amplify breakpoint overhead.

Phase 642 adds an optional bounded full-mode capture.

## Launcher option

```bash
python tools/run_sdf_solver_probe.py /path/to/SHIFT.exe \
  --output out/sdf-solver-capture \
  --attach-pid <PID> \
  --capture-frames 2
```

`--capture-frames N` requires a positive integer and is supported only in
full mode.

The generated GDB command file becomes:

```text
source .../gdb_sdf_solver_probe.py
sdf-probe .../capture --capture-frames N
continue
detach
quit
```

## Terminal event

The capture budget is implemented at `FUN_007b4110` post-solve entry.

`PostSolveProbe` still records the normal post-solve JSON snapshot first.
On the Nth post-solve hit it then returns `True`, which ends the command
file's `continue`. GDB consequently executes `detach` and `quit` outside
the Python breakpoint callback.

No detach command is issued from `Breakpoint.stop()`.

## Why post-solve

Post-solve is already one of the Phase 635 shared timeline anchors and is
common to the full frame evidence path. Using it as the terminal breakpoint
lets the final requested frame retain its post-solve observation before GDB
detaches.

## Mid-frame attachment

The debugger may attach while a retail frame is already in progress. A very
small budget can therefore observe a post-solve before the first captured
frame-entry.

Phase 642 does not hide this case. Phase 637 correlation remains fail-closed
and the Phase 638–641 automatic pipeline returns blocked if frame ownership or
timeline evidence is incomplete.

Using a small budget greater than one (for example 2) is a practical first
capture because it limits debugger residence while allowing a complete
frame-entry→post-solve interval after a possible partial first frame.

## Provider-only mode

Bounded capture is deliberately rejected with `--provider-only`. That mode
does not install the full post-solve/frame-entry evidence path and therefore
has no Phase 642 terminal anchor.

## Manifest

`probe_manifest.json` now records:

- `probe.capture_frames`;
- `probe.auto_detach`.

Unbounded mode keeps `capture_frames=null` and `auto_detach=false`.

## Evidence boundary

Phase 642 changes debugger lifetime only. It does not change mutation,
frame/reset/solve capture semantics and does not authorize native scheduler
behavior.
