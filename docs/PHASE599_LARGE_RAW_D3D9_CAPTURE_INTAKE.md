# Phase 599 — production-sized raw D3D9 capture intake

## Goal

Make the existing Silverstone runtime-attribution path accept the native proxy's
real JSONL output directly, including the large diagnostic capture produced by
the current D3D9 proxy.

The motivating capture is roughly 497 MB / 1.7 million JSONL records and mixes
runtime-evidence events with proxy, device and D3DPERF diagnostics.

## Changes

### Streaming JSONL reads

`d3d9_runtime_trace.iter_events()` reads the trace line-by-line instead of
materializing the complete file text before parsing it. `load_events()`
remains the compatibility list API, but no longer incurs the additional
`read_text().splitlines()` copy.

`imb_raw_capture_shader_prefilter.validate_files()` now feeds a streaming
JSONL iterator directly into the Phase 569 prefilter. Invalid JSON/non-object
rows are still accumulated as explicit blockers after iteration.

### Raw proxy metadata

The strict runtime-trace loader still rejects events outside its evidence
schema by default. A new opt-in `skip_unsupported=True` mode ignores only
events that are not members of the existing `EVENTS` set; all retained events
still pass `validate_capture_event()`.

`SHIFT.IMBRuntimeCapturePipeline/1` enables that mode for file-based raw
capture intake. This allows the pipeline to consume native captures containing
events such as `proxy_direct3dcreate9`, device diagnostics and D3DPERF markers
without weakening validation of shader/resource/binding/draw events.

### Canonical CreateTexture JSON

The native proxy previously appended observed texture descriptor width/height,
format and pool fields after already serializing the same creation parameters.
That produced duplicate JSON object keys in `create_texture` records.

CreateTexture/CreateCubeTexture now request descriptor status/type/level-count
metadata without re-emitting surface fields already present in the creation
record. SetTexture keeps the complete observed descriptor.

## Evidence boundary

This phase changes capture intake and serialization correctness only.

It does not:

- infer a resource identity from a shader or draw range;
- weaken Phase 572 same-instance gates;
- recover a missing Usage ordinal map;
- claim that the full Phase 598 Silverstone production coverage has been run;
- make the complete runtime evidence builder streaming internally.

The runtime builder still materializes its supported event rows because
integrity, texture lifecycle and draw-state reconstruction currently make
multiple passes over them. Phase 599 removes the avoidable full-file text copy,
streams the cheap shader prefilter, and makes authentic raw proxy JSONL a valid
input to the existing pipeline.
