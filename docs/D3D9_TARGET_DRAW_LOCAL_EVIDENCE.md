# D3D9 target draw-local evidence

## Purpose

`src/graphics/d3d9/d3d9_target_draw_local_evidence.py` is an offline-only
follow-on to the raw capture audit, target draw signature catalogue and pointer
observation stages. It consumes the already-recorded D3D9 JSONL stream and the
existing runtime shader target inventory. It does not launch the game and does
not require a new capture.

The output format is:

`SHIFT.D3D9TargetDrawLocalEvidence/1`

The stage is designed to preserve evidence strength rather than force a final
attribution. In particular it never chooses an FXO permutation merely because a
static ranking prefers it.

## Reconstructed draw state

For every draw whose currently bound pixel shader resolves to a target byte
SHA-256, the stage reconstructs:

- exact captured VS and PS byte SHA-256 pair;
- capture-local VS/PS COM pointer generations;
- vertex declaration byte identity and generation when available;
- all active stream bindings with pointer generation, byte offset and stride;
- stream-0 VB + IB generation and exact indexed draw range;
- non-zero stream state as repeated-instance evidence;
- CTAB-reflected VS/PS float constant windows with the last observed write event
  and frame for every register;
- CTAB-reflected pixel sampler stages with texture pointer generations and
  descriptors;
- any already-present runtime resource path/SHA or sampler snapshot metadata;
- deterministic hashes for shader pair, geometry identity, instance-stream
  identity, sampler state, constant state and the combined draw-local evidence.

D3D9 float constants are state, not draw calls. The stage therefore keeps a
per-device sparse register file and applies every observed
`set_vertex_shader_constant_f` / `set_pixel_shader_constant_f` update before
snapshotting the registers referenced by the shader CTAB at a target draw.

## Transform-like constants

CTAB names containing `world`, `model`, `object` or `instance` are additionally
grouped into a diagnostic transform-like signature. This is deliberately not a
matrix-semantic proof. A name match does **not** establish multiplication order,
coordinate convention, scene-node ownership or retail instance identity.

The value is useful for repeated-draw disambiguation only: if the same
stream-0/IB/draw-range geometry identity appears with different transform-like
constant signatures, the existing capture has proved that those observations
carry distinct draw-local state.

## Repeated-instance disambiguation

Geometry groups preserve stream-0 VB + IB + indexed range identity. Within each
group the stage reports whether repeated observations can be distinguished by:

- non-zero stream pointer generation / offset / stride state;
- transform-like CTAB constant signatures;
- full reflected VS float constant signatures;
- full reflected PS float constant signatures;
- CTAB-filtered texture object state;
- shader pair.

The status `distinguished-by-existing-capture` means only that the observations
are separable inside this capture. It does not assign them to a retail scene
instance.

## Evidence classification

Per-draw classifications are capture-local:

- `strong-capture-local` — target shader identity plus required stream-0 VB,
  IB, reflected constant and sampler bindings were reconstructed from observed
  state;
- `partial-capture-local` — one or more required capture-local pieces are
  unresolved; `missing_capture_local_state` lists each gap.

Neither classification promotes the draw to exact retail resource or primitive
identity.

## Capture requirement audit

The report also contains `capture_requirements`. It explicitly records whether
the input stream contains the event classes needed for later gates:

- shader creation/use identity;
- VS float constants;
- PS float constants;
- `buffer_payload` for exact VB/IB byte equality;
- runtime `resource_path` + `resource_sha256` pairs;
- captured sampler snapshots.

This is intended to prevent unnecessary recapture requests. A new capture should
be considered only for a gate that is reported missing and cannot be supplied by
existing static evidence.

## Historical Silverstone boundary

The existing Silverstone pipeline already established capture-local geometry and
material pointer identities for the target draws. Phase 616 further documented
that the historical production capture contains no `buffer_payload` events.
Therefore exact runtime VB/IB payload equality against static IMB content is a
real capture boundary; descriptor equality and pointer continuity must not be
silently promoted to payload identity.

By contrast, the historical JSONL does contain both vertex and pixel float
constant writes adjacent to draws. Draw-local constant reconstruction and
repeated-state disambiguation should therefore be exhausted offline before any
new run is requested.

## CLI

```bash
python src/graphics/d3d9/d3d9_target_draw_local_evidence.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_target_draw_local_evidence.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

The JSON is emitted with sorted keys and all aggregate rows use deterministic
hashes/orderings so the result can be checked into or compared as a regression
artifact.

## Non-claims

This stage does not claim:

- exact BFF/IMB/MEB path from pointer identity alone;
- exact IMB primitive without a unique static/runtime proof path;
- scene instance identity from a transform-like constant name;
- BMT identity from shared textures;
- FXO permutation identity from ranking or family membership;
- native render admission.

Those gates remain explicit and fail closed.
