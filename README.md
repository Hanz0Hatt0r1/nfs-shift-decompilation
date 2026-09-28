# Need for Speed: SHIFT — Decompilation & Resource IR

Evidence-driven reconstruction of *Need for Speed: SHIFT* resource formats, runtime contracts and rendering/physics boundaries.

> **Current mainline: Phase 500**
>
> Phases 499–500 add deterministic indexing and verification for specialized-provider runtime capture bundles. Exact retail numeric parity remains capture-gated.

## Mission

Reconstruct observable formats, binary layouts, dependencies and runtime boundaries as deterministic, machine-readable intermediate representations.

Canonical render path:

`BFF → IR → VHF/MEB/BMT/DDS → FX/FXO → DrawBinding → RenderCommand → native renderer`

Linux/Vulkan is the native renderer direction. The desktop software renderer is the deterministic reference oracle.

## Evidence policy

Static source/PE evidence, runtime observations and neutral renderer contracts are separate layers.

Use explicit states such as `proven`, `verified`, `inferred`, `ambiguous`, `unknown`, `unsupported` and `blocked`. Missing evidence is never replaced with a plausible value.

## Current status

| Area | State | Current boundary |
|---|---|---|
| BFF/XMem-LZX | verified | Type 0/1/2 paths and X12d=2 covered; Type 3 uses an external Oodle-compatible runtime |
| Resource IR | active/verified | typed parsing, hashes and provenance |
| MEB / vertex ABI | strong static coverage | BMW descriptor triples and D3D9 Type/Usage evidence are source-backed |
| BMW COLOR0 | statically resolved | 460 → [4,6,0] → Type 4 / D3D9 COLOR |
| BMW COLOR1 | statically described, corpus-limited | 461 → [4,6,1]; no positive 1.02 corpus instance |
| Material/shader linking | implemented | BMT → FX → FXO, CTAB samplers/constants, linked shader pair |
| Desktop reference renderer | active oracle | geometry, DDS, multi-sampler, samplerCube, VS→PS, explicit semantics, skinned command path |
| Skinning | contract implemented | MEB 310/580, explicit SkinPose, CPU reference, GLES parity |
| BAB animation | evidence-backed | bank/channel grammar reconstructed; remaining axis/order/trailing semantics explicit |
| SGB / scene | partial | NODE/PART/SUMM/OCCL/FLAT runtime boundaries and FLAT tree |
| Camera | active | loader/state/event/control primitives reconstructed |
| Vehicle physics | active | CDF/EDF/GDF/SDF and wheel/contact/solver boundaries |
| Builtin solver | source-backed | sparse-solver lifecycle and matrix/kernel layers |
| Specialized providers | capture-ready | 40/34 scalar domains, structural solver IR, reset/selector provenance |
| Provider numeric parity | blocked on capture | requires an authentic runtime frame |
| Vulkan | active native backend | bootstrap, packets, reflection gates, BMW material/DDS bridge |
| Android | deferred | waits on stable desktop/native runtime boundary |

## BMW M3 E36 vertical slice

The render slice is:

`VHF → MEB → BMT → FX/FXO → DrawPacket → RenderCommand`

The physics asset slice is:

`CDF + EDF + GDF + SDF → SHIFT.VehiclePhysicsAssetGraph/1`

### BMW paint bindings

| Material | FX sampler | D3D9 slot | Resource |
|---|---|---:|---|
| diffuseTexture | diffuseMap | s1 | COMMON_PAINT.dds |
| specularTexture | specularMap | s2 | COMMON_PAINT_SPECULAR.dds |
| scratchControlTexture | scratchControlMap | s4 | COMMON_BLANK.dds |
| environmentMap | environmentMap | s3 | external cube |
| shadow map | sShadowMap_f1_0 | s0 | external renderer resource |

## D3D9 / vertex ABI

MEB property descriptors are `[Type ordinal, Usage ordinal, Channel]`.

For BMW:

- 460 → `[4,6,0]`
- 461 → `[4,6,1]`
- Type 4 → `D3DDECLTYPE_D3DCOLOR`
- Usage ordinal 6 → D3D9 Usage 10 (`COLOR`)

This closes the static declaration mapping. It does **not** close same-instance runtime attribution.

Runtime closure requires correlation of MEB identity, declaration, vertex/index buffers, shaders and the exact `DrawIndexedPrimitive` boundary.

## Runtime capture

The D3D9 producer captures declaration/buffer/shader/constant/texture state and exact draws. Optional payload capture records texture mip data and VB/IB bytes. Draw-local snapshots are keyed by `(frame, draw_index)`.

Linux/apitrace tooling provides an alternate path for extracting unique BMW draw/resource instances and trimming large traces.

## Specialized-provider physics track

Current provider boundary:

`FUN_007b3f40 → FUN_007b2210(selector) → provider vtable +0x1c(selector) → provider +0x18 solve`

The repository now models:

- 40- and 34-scalar provider domains;
- row-pointer/workspace topology;
- pivot and acceptance structure;
- factor/write/dependency/update/operator IR;
- execution schedules and output-vector flow;
- read-before-write boundaries;
- provider vtable/reset lifecycle;
- scalar selector/reset provenance;
- live reset-effect and callsite evidence;
- reset→solve ordering;
- capture-session and capture-bundle verification.

### Phase 499–500 capture bundle

`tools/verify_specialized_provider_capture_bundle.py` indexes:

```text
provider_pre_<provider>_<hit>.json
provider_post_<provider>_<hit>.json
scalar_reset_events.jsonl
```

A bundle is structurally ready only when its required pre snapshot exists and integrated validation passes. A post snapshot is optional for pre-only diagnostics.

The bundle layer performs provenance/orchestration; it does not infer matrix semantics or claim numeric equivalence.

## Useful commands

```bash
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR \
  --reset-events CAPTURE_DIR/scalar_reset_events.jsonl \
  -o provider_bundle_manifest.json

python tools/extract_trace_tail.py SHIFT.trace SHIFT_tail_500MiB.trace

python tools/extract_apitrace_unique_bmw.py \
  --target-runtime-geometry evidence/bmw_m3_e36_kit00_body_loda.runtime_geometry.json \
  capture.trace

python vehicle_physics_bundle.py BMW_M3_E36.bff out/bmw_physics

./shift-bff-viewer /path/to/BMW_M3_E36.bff
```

## Current CI note

At commit `9bab80af4673856f77d58bed684e7a5290ff6f03`:

- native: success;
- capture-producer: success;
- linux-vulkan: success;
- Python CI: fails during collection because `tools/run_specialized_provider_differential.py:131` contains an unterminated string literal.

This is a current code/CI issue, not evidence that the documentation or capture-bundle design is invalid.

## Repository map

| Path | Purpose |
|---|---|
| `shift_importer.py` | importer and analysis CLI |
| `resource_formats.py`, `meb_format.py`, `csm_format.py` | core format parsers |
| `draw_packets.py`, `render_command.py` | neutral render contracts |
| `reference_renderer.py`, `shader_reference.py` | desktop oracle |
| physics runtime modules | vehicle/constraint/solver evidence |
| `native_capture/` | Windows D3D9 capture producer |
| `native_vulkan/` | Linux Vulkan backend |
| `tools/` | capture/evidence utilities |
| `tests/` | regression suite |
| `docs/PHASE*.md` | historical phase records |

Historical phase records are intentionally not rewritten retroactively. Current status belongs in the operational documents.
