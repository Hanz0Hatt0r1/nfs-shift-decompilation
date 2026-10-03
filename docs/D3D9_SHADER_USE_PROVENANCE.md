# D3D9 shader creation/use provenance

## Purpose

`d3d9_shader_use_evidence.py` closes the capture-local gap between shader byte
identity and the concrete `SetVertexShader` / `SetPixelShader` calls that made
those shader objects active at a draw.

The report format is:

`SHIFT.D3D9ShaderUseEvidence/1`

This stage consumes the existing raw JSONL capture only. It does not require the
original game to be started and it does not require a new capture.

## Identity layers

The report deliberately keeps three identities separate:

1. **Shader byte identity** — SHA-256 of bytecode captured at
   `CreateVertexShader` / `CreatePixelShader`.
2. **Shader object generation** — device, stage, COM pointer and the concrete
   creation event. A generation hash and per-pointer generation ordinal prevent
   pointer reuse from collapsing distinct objects.
3. **Shader use identity** — the concrete `SetVertexShader` /
   `SetPixelShader` event that selected a generation and remained active at the
   draw.

Each `DrawIndexedPrimitive` therefore receives:

- exact VS byte SHA-256 when resolvable;
- exact PS byte SHA-256 when resolvable;
- VS creation event and generation hash;
- PS creation event and generation hash;
- VS bind event and bind frame;
- PS bind event and bind frame;
- byte-pair hash;
- generation-pair hash;
- use-pair hash;
- explicit capture-local confidence and missing-state reasons.

A later creation at the same COM pointer cannot retroactively change a previous
binding: generation resolution is frozen at the `Set*Shader` event.

## Target filtering

With `--target-inventory`, only draws whose active pixel-shader byte SHA-256 is
present in the supplied target inventory are emitted. This makes the output
directly usable for the existing Silverstone target set without turning family
membership into proof of scene/material identity.

Without `--target-inventory`, all observed indexed draws are emitted, including
partial rows whose active shader creation could not be resolved.

## CLI

```bash
python src/graphics/d3d9/d3d9_shader_use_evidence.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_shader_use_evidence.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

## Provenance and confidence

`classification=exact-capture-local` requires both VS and PS to have:

- an observed binding event;
- a non-null shader pointer;
- an observed creation generation;
- an exact captured byte SHA-256.

Anything weaker remains `partial-capture-local` with explicit
`missing_shader_use_state` entries. The extractor does not rank unresolved
candidates and does not promote an ambiguous pointer fallback to a proof.

## Renderer blocker status after this stage

### Closed by existing capture + tooling

- shader creation byte identity;
- shader object generation identity;
- shader use/bind-event identity;
- exact capture-local VS/PS byte pairing at `DrawIndexedPrimitive`;
- COM shader pointer reuse disambiguation by creation generation.

### Still open

- exact scene/resource identity for each draw;
- exact IMB/MEB primitive identity where static joins remain ambiguous;
- exact material/BMT identity where several static candidates survive;
- exact FX/FXO permutation naming when byte identity does not uniquely map to a
  single static candidate;
- exact texture payload identity for runtime-owned/external textures without a
  portable path/SHA observation;
- Vulkan render admission.

### Data already present in the historical capture but requiring downstream tooling

- draw ranges;
- VB/IB bindings and creation generations;
- shader constants and their last-write events;
- CTAB-driven sampler bindings;
- texture pointer generations;
- repeated-instance signals from non-zero streams and transform-like constants.

These should be exhausted before requesting another capture.

### Data genuinely absent only when the requirement audit says so

A new capture is justified only for a specific unresolved requirement such as:

- missing `buffer_payload` needed for exact runtime VB/IB payload equality;
- missing portable `resource_path + resource_sha256` needed for exact
  runtime-to-retail resource attribution;
- missing captured texture snapshot needed for exact runtime-owned texture
  payload correlation.

The minimal additional capture should add only the missing event/data field for
the already narrowed target draws; it should not repeat unrelated state.
