# Phase 616 — exact geometry payload candidate join

Phase 615 proved that capture-local stream-0 VB/IB object continuity does not
cross from the 24 already-single resource shapes into the 15 remaining
ambiguous shapes in the historical Silverstone capture. The result is useful but
negative: 55 geometry pointer identities cover all 1,581 target draws, while all
31 ambiguous identities are unseeded.

Phase 616 therefore stops trying weaker pointer/descriptor heuristics and adds an
exact byte-level geometry gate:

`SHIFT.IMBRuntimeGeometryPayloadCandidateJoin/1`.

## Evidence used

The static side is reconstructed directly from each candidate `.imb`:

- `parse_imb_binary_mesh(..., decode_primitives=True)` provides the original
  planar Type/Usage/Channel stream bytes;
- each raw source element is copied to its recovered `runtime_element_offset`
  inside `runtime_vertex_stride`, producing the exact expected runtime
  interleaved stream-0 vertex buffer;
- every primitive's `indices_u16` is packed directly as little-endian u16,
  matching the observed D3D9 `D3DFMT_INDEX16` buffers;
- SHA-256 is computed over those exact byte strings.

The runtime side consumes existing native-capture `buffer_payload` events. A
payload is usable only when:

- `snapshot_status == captured`;
- `offset == 0`;
- `captured_byte_size == buffer_length > 0`;
- the payload file exists and has exactly that size;
- all accepted full snapshots for the same COM pointer + creation-event
  generation have one SHA-256.

A Phase 615 geometry identity may be narrowed only when both its stream-0 VB and
IB generations have stable full payloads **and every existing static candidate**
has a complete static payload fingerprint. Zero matches, missing files,
unstable runtime bytes, or incomplete static inventory fail open and retain the
original candidate set.

## What this can prove

An exact VB+IB match can prove that one runtime geometry allocation has the same
mesh bytes as one or more static IMB candidates. It does **not** by itself prove:

- the runtime logical resource/archive path;
- BMT/material identity;
- which SGB scene instance issued the draw;
- shader or render admission.

The output remains candidate-only. Existing Phase 572 same-instance/shader
admission gates stay independent.

## Historical capture

The existing production capture has no `buffer_payload` events, so running Phase
616 against it is expected to report `runtime-payload-missing` and perform no
narrowing. This is a capability boundary, not a failed attribution.

## Capture once with payloads

The current launcher already exposes the required native-capture feature. Under
Wine/PortProton, launch the same Silverstone scene and trigger near the target
scene:

```bash
bash tools/run_shift_capture_wine.sh \
  --game /path/to/SHIFT.exe \
  --proxy /path/to/built/d3d9.dll \
  --output out/shift-capture-payload \
  --mode capture \
  --buffer-payloads \
  --trigger \
  --pre-frames 2 \
  --post-frames 60
```

Press `F10` when the relevant Silverstone scene is visible. Triggered capture is
useful here because the native producer retains the latest full buffer payload
per resource before the trigger and flushes those deferred snapshots when the
trigger activates.

On native Windows the equivalent PowerShell launcher option is
`-CaptureBufferPayloads`.

After regenerating the Phase 613→615 reports from that same capture, run:

```bash
python src/scene/imb_runtime_geometry_payload_candidate_join.py \
  out/d3d9_runtime_geometry_pointer_candidate_join.json \
  out/shift-capture-payload/shift_d3d9_capture.jsonl \
  out/d3d9_runtime_geometry_payload_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --payload-root out/shift-capture-payload/buffers
```

`--corpus` may be repeated for `.zip` or `.bff` inputs. The analyzer only
extracts logical IMB paths present in the Phase 615 candidate sets.

## Main metrics

The result summary reports:

- `runtime_payload_complete_identity_count` / draw count;
- `payload_reduced_identity_count` / draw count;
- `newly_single_payload_identity_count` / draw count;
- `payload_conflict_identity_count` / draw count;
- `removed_candidate_count`;
- `geometry_payload_gate_status_counts`.

A useful production result has stable payload coverage for the ambiguous
identities and either `reduced-by-exact-geometry-payload` or
`payload-non-discriminating`. A conflict is never used to reject the existing
static candidate set; it is diagnostic evidence that the reconstructed/static
assumption needs review.
