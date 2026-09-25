# Phase 186 — BMW runtime capture preflight

## Goal

Provide a deterministic first-pass diagnostic for an external BMW M3 D3D9 capture.
The preflight locates draw candidates that use the exact target MEB identity and
the documented BMW M3 paint primitive ranges before shader execution begins.

## Contract

`SHIFT.BMWRuntimeCapturePreflight/1` reports:

- target MEB path and optional exact resource SHA-256;
- resource-backed draw candidates;
- exact paint-range candidates for primitive 1 and primitive 2;
- frame and draw identity;
- captured shader identity when present;
- runtime integrity and same-instance status;
- explicit blocking reasons.

The preflight is diagnostic. It does not replace `same_instance_gate` and does not
promote a render to ready on resource/range evidence alone.

## Pipeline integration

`bmw_post_capture_pipeline.py` now writes `runtime_capture_preflight.json` and adds
a `runtime_capture_preflight` stage. The pipeline still stops before render-contract
construction when the strict same-instance gate is not proven.

## Evidence boundary

No authentic retail D3D9 capture is claimed by this phase. The tool is intended to
make the first real capture immediately attributable to the exact BMW M3 target
draw without manually searching a large JSONL trace.

## Regression coverage

Tests cover exact paint range detection, wrong resource rejection, missing
same-instance proof and snapshot priority over frame-level draw history.
