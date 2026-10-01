# Phase 646 — lightweight relation-mutation timeline capture

The current integration blocker is authentic retail runtime evidence. Earlier
full-mode GDB capture installs solver/provider/reset breakpoints and reads full
post-solve RHS vectors. Under Wine that can make a short evidence collection
needlessly intrusive when the immediate question is only where
`FUN_00757d2c` relation-state mutations occur in the frame timeline.

Phase 646 adds a narrower capture mode for that evidence.

## Launcher mode

Use:

```bash
python tools/run_sdf_solver_probe.py /path/to/SHIFT.exe \
  --output out/relation-timeline-capture \
  --attach-pid <PID> \
  --relation-timeline-only \
  --capture-frames 2
```

`--capture-frames N` remains optional, but using a small bounded capture lets
the generated GDB command detach automatically on the Nth post-solve anchor.

`--relation-timeline-only` and `--provider-only` are mutually exclusive.

## Installed breakpoints

The lightweight mode installs only:

1. `FUN_00757d2c` relation-state mutation;
2. frame entry;
3. `FUN_007b4110` post-solve ordering anchor.

It deliberately omits:

- builtin solver entry;
- provider 0/1 solve entry and return probes;
- scalar-reset probe;
- provider reset probes.

The post-solve hook is also a dedicated metadata-only
`PostSolveAnchorProbe`. It records the shared runtime-event sequence, frame
index and physics-system pointer, but does not read scalar count, RHS pointer or
the solved vector.

## Evidence compatibility

The lightweight files still use the same filenames consumed by the existing
pipeline:

- `relation_state_mutation_events.jsonl`;
- `frame_entry_XXXXXX.json`;
- `post_solve_XXXXXX.json`.

Therefore Phase 637/644 timeline correlation, Phase 639/645 packaging,
Phase 640/645 verification and Phase 641 replay run unchanged after capture.

The Phase 643 session id is stamped on all three evidence kinds, and bounded
capture still detaches outside the GDB breakpoint callback.

## Evidence boundary

This mode reduces debugger work; it does not change the meaning of the evidence.
It does not infer a gameplay event, establish fixed-step scheduler semantics or
admit relation-state mutation to the native runtime.

If no authentic runtime mutation is observed in the selected frame window, the
timeline remains blocked rather than synthesizing one.
