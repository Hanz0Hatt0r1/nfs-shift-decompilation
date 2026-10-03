# Target D3D9 texture/sampler provenance

## Purpose

`d3d9_target_texture_sampler_evidence.py` reconstructs draw-local texture object
and use identity for Silverstone target draws while keeping explicit sampler
state as a separate observation.

The report format is:

`SHIFT.D3D9TargetTextureSamplerEvidence/1`

The stage consumes the existing JSONL capture only. It does not run SHIFT and it
does not require another capture to recover texture creation/binding history
that is already present.

## Evidence chain

For each target draw the extractor follows:

```text
CreatePixelShader
→ SetPixelShader
→ CTAB sampler registers
→ CreateTexture/CreateCubeTexture
→ SetTexture
→ optional SetSamplerState writes
→ DrawIndexedPrimitive
```

Each CTAB-selected sampler row retains:

- sampler register and CTAB name;
- texture COM pointer;
- texture creation event/frame;
- per-pointer generation ordinal and generation SHA-256;
- concrete `SetTexture` bind event/frame;
- creation/bind descriptor fields;
- portable `resource_path` + `resource_sha256` only when actually observed;
- captured snapshot metadata only when actually observed;
- every explicit sampler-state value plus its last write event/frame;
- deterministic texture-use and sampler-state signatures.

Texture generation is resolved at `SetTexture` time. A later
`CreateTexture` at the same COM address therefore cannot rewrite provenance for
an earlier draw.

## Sampler state policy

`SetSamplerState` is intentionally not required for an otherwise exact
capture-local texture binding. D3D9 sampler state persists and may remain at a
default or previously established value. If no explicit write is present in the
capture, the row says `no-explicit-write-observed`; it does not invent a value
and it does not automatically request a new capture.

If explicit writes are present, the report records numeric state IDs, known
D3D9 state names, values, and last-write provenance.

## Conservative resource classification

The `resource_scope` field is evidence-based:

- `portable-resource-identified` requires both `resource_path` and
  `resource_sha256`;
- `captured-snapshot-backed` requires an observed captured snapshot;
- `runtime-object-generation-only` means a creation generation is known but no
  portable resource identity is proven;
- `runtime-pointer-only` means even creation generation is unresolved;
- `unbound` means the CTAB sampler has no current texture binding.

Absence of a retail path is **not** interpreted as proof that a texture is
external/runtime-owned.

## CLI

```bash
python src/graphics/d3d9/d3d9_target_texture_sampler_evidence.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_target_texture_sampler_evidence.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

## Historical Silverstone capture boundary

The currently available historical raw capture contains texture creation and
binding history, so texture object generations and concrete `SetTexture` use
provenance can be reconstructed offline.

The inspected capture does not expose the following observations:

- `set_sampler_state`;
- `buffer_payload`;
- `resource_sha256` / portable path+SHA pairs;
- captured texture `snapshot_status` metadata.

The extractor makes these absences machine-readable under
`capture_observations` instead of converting them into guesses.

## Renderer blocker status after this stage

### Closed from existing evidence

- texture creation object identity;
- texture COM generation identity;
- concrete texture-use (`SetTexture`) identity at target draws;
- CTAB-based sampler-stage selection when reflection is available;
- safe distinction between portable resource identity and capture-local texture
  identity;
- pointer-reuse protection for texture objects.

### Still open

- explicit sampler-state snapshots for this historical capture;
- exact DDS/static resource identity where no path+SHA or exact payload witness
  exists;
- proof that a pathless texture is external/runtime-owned;
- exact BMT identity when multiple static material candidates remain;
- exact FX/FXO permutation naming when shader byte identity maps to multiple
  static candidates;
- Vulkan render admission.

### Already present but requiring further correlation tooling

- target draw ranges;
- exact VS/PS byte identities and bind provenance;
- texture descriptors and bind chronology;
- VB/IB creation generations;
- CTAB-aware float constants and write provenance;
- repeated-instance signals.

### Minimal additional capture only if later proof requires it

Do not request a broad replacement capture. If a downstream proof reaches a
hard boundary, add only the missing observation for the already narrowed target
set, for example:

- `set_sampler_state` if exact non-default sampler values are required;
- `buffer_payload` if exact runtime VB/IB byte equality is required;
- path+SHA or texture payload/snapshot evidence if exact runtime-to-retail
  texture identity is required.

Until a downstream proof specifically depends on one of those facts, the
existing capture remains sufficient for the texture binding work above.
