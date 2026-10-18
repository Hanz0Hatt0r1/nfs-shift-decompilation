# SHIFT D3D9 race buffer payload evidence — 2026-10-18

## Capture

This report analyzes the two trigger windows recorded after the user confirmed
the original retail game was in a race: frames 5865–5869 and 6983–6987. It does
not contain the raw capture or buffer payload bytes; those remain in the local
capture bundle.

- Raw JSONL: 94,429,444 bytes, SHA-256
  `d90ede38815242dc4a7ff5771b9d886e26931590621631f16ea4617852276afe`.
- Events: 202,870 valid JSON objects; the analyzer reported no malformed or
  non-object lines.
- Target inventory SHA-256:
  `26620dbe10aa578abe1115f56c642037bd2b06199814a886affcecaa4706650f`.
- Machine-readable, compressed analysis:
  [`d3d9_race_target_buffer_payloads_20261018.json.gz`](../evidence/retail_frontier_20261018/d3d9_race_target_buffer_payloads_20261018.json.gz).

## Findings

- The target inventory matched 813 race draws. All 813 are strong capture-local
  draw records, and each has a hashed full-buffer payload snapshot for its
  stream-0 vertex-buffer generation and index-buffer generation.
- The target draws use 105 buffer generations: 52 vertex-buffer generations
  bound to stream 0, one vertex-buffer generation bound to stream 1, and 52
  index-buffer generations. Full-buffer payload files were found and hashed for
  104/105 generations; none of the referenced files was missing or outside the
  payload directory.
- The sole absent generation is vertex buffer `0xd39e4b8`, creation event 224,
  length 131,072 bytes, usage 520 (`D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY`),
  pool 0. It is bound as stream 1 in all 813 target draws across frames
  5865–6987. No `buffer_payload` event for this generation appears in the
  capture.
- The capture contains no retail `resource_path` + `resource_sha256` identity
  pair. The buffer hashes identify captured files at analysis time; they do not
  prove that those exact bytes were present at every historical draw using the
  same COM generation. The report preserves each payload-to-draw frame
  relationship and makes no render-admission claim.

The capture is sufficient for offline shader/draw-local analysis and for
stream-0/index payload comparisons. It does not yet provide the complete target
vertex input because the shared dynamic stream-1 generation has no payload.
Absence of a payload event alone does not prove whether that buffer was never
locked or whether only partial lock ranges were used.

## Follow-up capture and remaining gaps

A bounded follow-up on 2026-10-19 captured a separate generation (`0xd4dfd70`)
of the same 128 KiB stream-1 buffer class. Its five-frame window contains 119
target-shader draws and 1,806 captured payload events; the ranges cover 109/119
computed draw inputs. The raw data and comparison are documented in the
[stream-1 follow-up note](SHIFT_D3D9_STREAM1_FOLLOWUP_20261019.md). This does
not retroactively supply bytes for the older `0xd39e4b8` generation, and ten
input intervals in the new window remain incomplete. The shader inventory
labels the matched signature `crowdgeninstanced`; the follow-up does not prove
which car models were visible.

Any further capture should be limited to a specific unresolved byte range or
to a user-confirmed visible vehicle set. Keep the existing partial-buffer
capture opt-in, trigger it only after the scene is ready, and avoid repeating a
full startup or process dump.

The analyzer and capture mode preserve backward compatibility: existing full
buffer captures continue to work, and partial-range capture remains opt-in.
