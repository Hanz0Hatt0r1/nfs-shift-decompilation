# Process 1 — BMW BODY0 targeted runtime probe

## Blocker

Close or materially shorten `SHIFT.BMWBody0BindFrameProof/1` by collecting a bounded runtime observation around BMW construction, first persistent BODY0 updates, and the first player control transitions.

## Input

- Current static BODY0 construction/bind frontier.
- Existing `tools/shift_live_dump` Linux/Wine process-memory tooling.
- Retail `SHIFT.exe` identity already recorded by the Ghidra evidence database.

## Output

A single operator-facing capture command that emits a small, deterministic evidence bundle containing process/module identity, selected memory/register-adjacent observations where available, timestamped sample windows, and explicit capture phases suitable for later provenance analysis.

## Consumer

Process 1 static/runtime provenance analysis for `SHIFT.BMWBody0BindFrameProof/1`, followed by Process 2 retail BODY0 admission. The same capture skeleton should be reusable for retail outer-update cadence and input/control-producer probes.

## Scope

This task does not claim BODY0 semantics from raw numeric coincidence and does not promote observations into a positive proof by itself. It only creates bounded evidence infrastructure required by the current blocker.
