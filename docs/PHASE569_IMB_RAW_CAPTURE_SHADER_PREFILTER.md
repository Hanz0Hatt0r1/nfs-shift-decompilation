# Phase 569 — IMB raw D3D9 shader prefilter

Phase 568 reduces the complete Silverstone shader ambiguity surface to a
capture-oriented whitelist of 51 runtime-observable shader hashes.

Phase 569 applies that target set directly to raw JSONL emitted by the native
D3D9 capture producer, before the heavier runtime-binding reconstruction.

## Contract

The new contract is:

`SHIFT.IMBRawCaptureShaderPrefilter/1`

implemented in:

`src/scene/imb_raw_capture_shader_prefilter.py`.

Input:

- `SHIFT.IMBRuntimeShaderTargetSet/1`;
- raw native D3D9 JSONL events.

## State tracking

The prefilter follows the capture producer's existing event grammar:

- `create_vertex_shader`;
- `create_pixel_shader`;
- `set_vertex_shader`;
- `set_pixel_shader`;
- `draw_indexed_primitive`.

Shader creation payloads are decoded from `bytes_hex` and hashed with
SHA-256. The prefilter tracks shader objects by stage/pointer and active VS/PS
state independently per D3D9 device.

Pointer reuse with different bytecode is an explicit blocker rather than being
silently accepted.

## Draw filtering

At every `draw_indexed_primitive` event, the prefilter computes:

- active vertex shader byte SHA-256;
- active pixel shader byte SHA-256;
- concatenated VS+PS pair SHA-256 when both objects are known.

Only draws intersecting at least one Phase 568 target are retained.

For each retained draw the report preserves:

- JSONL line;
- frame;
- capture event index;
- global draw ordinal;
- device pointer;
- original indexed-draw arguments;
- active VS/PS pointers and byte hashes;
- matching target identities and evidence strength;
- candidate IMB binding indices;
- candidate shader families.

## Scoring

The scoring semantics mirror the existing BMW raw-capture prefilter:

- 90 — exact pair-byte hash;
- 80 — both stage hashes satisfy an exact-pair target;
- 40 — vertex or pixel hash prefilter match.

The current Silverstone production target set is entirely pixel-prefilter
evidence, so the expected Phase 568 path enters at score 40.

A score is a filtering strength, not runtime attribution.

## Important boundary

This phase deliberately does **not** assert:

- track resource identity;
- IMB identity;
- primitive/draw-range identity;
- same-instance identity;
- exact retail shader permutation selection.

The report therefore keeps:

- `resource_identity_proven = false`;
- `draw_range_identity_proven = false`;
- `same_instance_proven = false`;
- `selects_permutation = false`.

The prefilter is useful even before those gates because it can reduce a large
capture to draws whose active shaders are members of the 51-hash Silverstone
whitelist.

## Usage

Generate the full target set first:

```bash
python src/scene/imb_runtime_shader_target_set.py \
  out/silverstone-ranking.json \
  out/silverstone-runtime-shader-targets.json
```

Then filter a raw capture:

```bash
python src/scene/imb_raw_capture_shader_prefilter.py \
  out/silverstone-runtime-shader-targets.json \
  shift_d3d9_capture.jsonl \
  out/silverstone-raw-shader-prefilter.json
```

The command returns success when the target set is structurally usable and the
capture contains no malformed/pointer-reuse blockers. A valid capture may still
produce `status = not-found` when none of the target shaders were observed.

## Next

The next step is to reconstruct full
`SHIFT.D3D9RuntimeBindingEvidence/1` only for the retained candidate draws and
join:

`track/IMB resource identity + primitive draw identity + runtime shader hashes
+ same-instance gate`.

Only that join can promote one static Silverstone candidate to the concrete
retail permutation.
