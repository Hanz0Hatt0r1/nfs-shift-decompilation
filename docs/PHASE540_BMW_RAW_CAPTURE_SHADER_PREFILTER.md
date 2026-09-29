# Phase 540 — raw BMW D3D9 shader prefilter

Phase 540 adds a fast first pass over the native D3D9 producer's raw JSONL
capture. It is designed to answer one question before the heavier runtime
reconstruction runs:

> Did this capture contain the BMW shader byte identities and canonical indexed
> draw ranges that Phase 538/539 need?

## Raw evidence used

The existing capture producer already emits:

- `create_vertex_shader` with complete `bytes_hex`;
- `create_pixel_shader` with complete `bytes_hex`;
- `set_vertex_shader` / `set_pixel_shader`;
- `draw_indexed_primitive` with `start_index` and `primitive_count`.

No new D3D9 hook is required.

The prefilter SHA-256 hashes shader creation bytes and tracks active VS/PS
objects per D3D9 device. At a canonical BMW primitive draw range it compares:

- pair SHA-256 for exact-pair targets;
- both stage hashes for exact-pair targets;
- one stage hash for prefilter-only targets.

A prefilter-only Phase 538 target can never be promoted to a strong pair match
through a representative static pair hash.

## Output

`SHIFT.BMWRawCaptureShaderPrefilter/1` reports:

- target shader creation hits;
- per-primitive matching draw events;
- active shader pointers and SHA-256 identities;
- exact-pair versus weak prefilter coverage;
- malformed JSON/shader events and shader-pointer reuse.

Shader byte payloads are not copied into the report.

## Boundary

`coverage_ready=true` means every selected primitive had at least one relevant
hash match on its canonical draw range.

It does **not** prove:

- MEB resource identity;
- draw-snapshot integrity;
- same-instance resource ownership;
- exact FXO permutation selection.

Those remain the Phase 539/full
`SHIFT.D3D9RuntimeBindingEvidence/1` gate.

## CLI

```bash
python shift_importer.py bmw-raw-capture-shader-prefilter \
  bmw-runtime-shader-targets.json \
  shift_d3d9_capture.jsonl \
  bmw-raw-prefilter.json
```

This allows a short capture to be rejected or accepted for deeper processing
without first running the entire BMW post-capture pipeline.
