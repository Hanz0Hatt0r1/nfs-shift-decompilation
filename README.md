# Need for Speed: SHIFT — Decompilation & Resource IR

<p align="center">
  <strong>Evidence-driven reconstruction of the SHIFT resource and rendering pipeline</strong><br>
  <sub>BFF → IR → VHF/MEB/BMT/DDS → FX/FXO → RenderCommand → D3D9 runtime evidence → reference renderer → Android/GLES</sub>
</p>

<p align="center">
  <a href="https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions">CI</a> ·
  <a href="ROADMAP.md">Roadmap</a> ·
  <a href="VERTEX_ABI_STATUS.md">Vertex ABI</a> ·
  <a href="REFERENCE_RENDERER_STATUS.md">Reference Renderer</a> ·
  <a href="SHADER_BACKEND_STATUS.md">Shader Backend</a> ·
  <a href="SKINNING_STATUS.md">Skinning</a>
</p>

> **Current mainline: Phase 247.**
>
> The project has progressed from format parsing to a real BMW M3 E36 vertical slice: retail BFF resources can be reconstructed through VHF/MEB/BMT/DDS, real BMW shader evidence is available from `RENDER.bff`, runtime D3D9 capture records declarations/shaders/constants/textures, and the captured VS/PS can be executed offline through the reference renderer.
>
> **Current external gate:** obtain one real retail D3D9 capture containing the target BMW M3 body draw and prove the same-instance chain from MEB resource → declaration → indexed draw → VS/PS → constants → sampler resources.
>
> **Draw-local runtime proof:** `SHIFT.D3D9RuntimeBindingEvidence/1` now freezes declaration, stream, index, shader, constant and texture state at each `DrawIndexedPrimitive` boundary. The strict same-instance gate consumes these snapshots rather than the final state of the whole frame.

> **Draw-local shader join:** runtime shader selection, parity and the render contract now consume the same `(frame, draw_index)` snapshot. Frame-level shader state is retained only for compatibility with legacy reports that have no snapshots.

> **Versioned draw state:** `SHIFT.D3D9DrawStateSnapshot/1` adds normalized active stream/texture bindings and latest constant-register state to each exact draw boundary; malformed snapshots are blocked from proof.
> **Capture preflight:** BMW paint candidates now expose snapshot schema validity, active texture stages and populated constant-state stages; `ready` also requires complete declaration/VS/PS/stream/index state on the proven draw.
>
> **Runtime hard gates:** exact MEB SHA identity, draw/snapshot alignment and BMW capture preflight are now mandatory before runtime render execution.

> **Capture provenance:** `SHIFT.D3D9RuntimeCaptureManifest/1` fingerprints the capture artifact and checks event-stream continuity while keeping authenticity explicitly unverified.

> **PE Usage mapping:** `SHIFT.PEImageEvidence/1` can now decode the recovered Usage table and emit `SHIFT.D3D9UsageMap/1`; numeric Usage is now decoded from the supplied retail SHIFT.exe PE image.

> **BMW M3 test scene:** `tests/scenes/bmw_m3_e36_kit00_test_scene.json` pins the supplied `BMW_M3_E36.bff` to KIT00/LODA and four deterministic 1600×900 geometry-preview views; the screenshot bundle is kept external to the repository.


>
> **BMW capture preflight:** `SHIFT.BMWRuntimeCapturePreflight/1` locates exact target-MEB and paint-range draw candidates before shader execution; it is diagnostic and does not replace the strict same-instance gate.

> **Linux/Vulkan direction:** Phase 203 establishes Linux as the primary renderer lab. Vulkan is the native backend target, while the software reference renderer remains the deterministic oracle.

> **SHIFT.exe PE evidence:** `SHIFT.MEBD3D9DescriptorTripleEvidence/1` is now joined into the main color bridge. Exact MEB descriptors `[4,6,0]`/`[4,6,1]` plus the source-backed Type-4 packed-color path resolve the static color declaration to D3D9 Type 4 (`D3DCOLOR`, BGRA memory / RGBA shader order); runtime same-instance proof remains separate.

---

## Mission

This project reconstructs the **observable formats, contracts, dependencies and runtime boundaries** of *Need for Speed: SHIFT* as deterministic, machine-readable intermediate representations.

The long-term target is a renderer that consumes this reconstructed IR without depending on the original game runtime, with a Linux/Vulkan renderer as the primary native target; Android is deferred until the decompilation and desktop/runtime boundary are substantially complete.

### Core rule

> **Do not guess undocumented semantics when evidence can be collected instead.**

Weak or unresolved behavior remains explicitly marked as `unknown`, `inferred`, `ambiguous`, `unsupported` or `blocked`.

---

## Architecture

```text
                    RETAIL SHIFT DATA
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
       BFF / XMem / LZX          SHIFT.exe evidence
             │                         │
             └────────────┬────────────┘
                          ▼
                     Resource IR
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
   VHF / BAS / BAB     MEB / BMT / DDS     FX / FXO
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
                Resource + Shader Linking
                          │
                          ▼
                    DrawBinding
                          │
                          ▼
                    RenderCommand
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
          Desktop oracle       GLES 3.1 ABI
                 │                 │
                 └────────┬────────┘
                          ▼
                 Vulkan runtime

             Android runtime (later)

             PARALLEL RUNTIME EVIDENCE
                          │
                 Windows D3D9 capture
                          ▼
                    versioned JSONL
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   declarations       VS / PS           SetTexture
   streams / index    constants         resource types
        └─────────────────┼─────────────────┘
                          ▼
                  same-instance gates
                          ▼
                 BMW runtime contract
                          ▼
                exact shader execution
```

---

## Current status

| Area | Status | Capability |
|---|:---:|---|
| BFF / XMem / LZX | ✅ | v3 entries, ranges, raw/zlib/XMem+LZX and native backend |
| Resource IR | ✅ | manifests, SHA-256 identities, blobs and dependency graphs |
| Reflection / BML / XML | ✅ | typed parsing, inheritance and generic XML trees |
| VHF vehicle hierarchy | ✅ | real BMW M3 hierarchy and deterministic KIT/LOD assembly |
| BAS skeleton | ✅ | hierarchy and transforms |
| BAB bone tables | ✅ | bone table parsing and conservative opaque-tail handling |
| BAB animation | 🟡 | runtime channel grammar reconstructed; clip/pose integration remains |
| MEB geometry | ✅ | real geometry, descriptors, UVs, normals, tangents and skin streams |
| COLOR0 | ✅ | MEB 460 → D3D9 Type 4 bridge is evidence-backed |
| COLOR1 | 🟡 | property 461 was absent from the supplied 1.02 corpus |
| BMT / material | ✅ | real BMW material extraction and contract validation |
| FX / FXO | ✅ | real `bodywork.fx` corpus and exact permutation selection |
| Shader IR | ✅ | D3D9 bytecode → `SHIFT.ShaderProgram/1` |
| GLSL ES 3.1 | 🟢 | generated stages + optional compile/link validation |
| RenderCommand | ✅ | resources, constants, vertex ABI, readiness and blockers |
| Desktop renderer | 🟢 | geometry, textures, multi-sampler, cube maps, VS→PS linkage and captured shader execution |
| Skinning | 🟢 | explicit SkinPose, CPU LBS oracle and GLES ABI |
| D3D9 runtime capture | 🟢 | declarations, streams, indices, shaders, constants, textures and resource descriptors |
| BMW post-capture pipeline | 🟢 | one-command evidence → shader selection → render contract → offline render |
| Android runtime | ⏳ | follows stabilization of the desktop/runtime boundary |
| Gameplay systems | ⏳ | deliberately later |

---

# BMW M3 E36 vertical slice

The current proof vehicle is the real BMW M3 E36 asset.

```text
BMW_M3_E36.bff
   │
   ├── VHF → hierarchy / transforms
   ├── MEB → geometry / vertex ABI
   ├── BMT → material / sampler references
   └── DDS → texture payloads

RENDER.bff
   │
   └── bodywork.fx / FXO corpus
             │
             ▼
       exact VS/PS permutation
             │
             ▼
       RenderCommand / runtime contract
```

A compact golden manifest identifies the selected body MEB, primitive range, material alias and shader permutation so a future image checkpoint remains attributable to exact source data.

---

## Evidence model

### Resource provenance

Important resources carry:

- archive identity;
- resource path/index;
- decoded SHA-256;
- exact byte ranges where relevant;
- parser/schema version;
- source provenance.

### MEB vertex ABI

Known mappings include:

| Property | Semantic | Representation |
|---:|---|---|
| 200 | POSITION0 | FLOAT32x3 |
| 220 | NORMAL0 | FLOAT32x3 |
| 240 | TANGENT0 | FLOAT32x3 |
| 250 | BINORMAL0 | FLOAT32x3 |
| 130–134 | TEXCOORD0–4 | FLOAT32x2 |
| 230–234 | TEXCOORD0–4 family | FLOAT32x3 UVW |
| 310 | BLENDWEIGHT0 | FLOAT32x4 |
| 580 | BLENDINDICES0 | UINT8x4 |
| 460 | COLOR0 | D3D9 Type 4 bridge |
| 461 | COLOR1 | not positively observed in supplied 1.02 corpus |
| — | TEXCOORD5 | shader-proven; MEB source mapping unresolved |

MEB property descriptors retain the exact on-disk 12-byte descriptor records.

### D3D9 declaration lifecycle

The recovered source evidence models:

```text
MEB descriptor triple
      ↓
Type / Usage / Channel
      ↓
D3DVERTEXELEMENT9-shaped record
      ↓
canonicalization
      ↓
CreateVertexDeclaration
      ↓
SetVertexDeclaration
      ↓
SetStreamSource / SetIndices
      ↓
indexed draw
```

Static executable evidence and runtime evidence are kept separate. A generic declaration observation is not promoted to same-instance proof.

---

# Runtime D3D9 capture

The Windows producer records the state needed to close the BMW runtime gate:

- frame/object identity;
- vertex declarations;
- stream/index bindings;
- VS/PS creation and binding;
- shader byte identity;
- shader constants;
- `SetTexture` bindings;
- resource descriptors;
- indexed draw ranges;
- optional texture surface snapshots;
- optional `Present` backbuffer screenshots.

The capture is versioned and schema-validated before semantic analysis.

### Build

On Windows:

```powershell
cmake -S native_capture -B native_capture/build -A Win32
cmake --build native_capture/build --config Release
```

Place the resulting `d3d9.dll` beside the test SHIFT executable.

Enable capture:

```powershell
set SHIFT_D3D9_CAPTURE=C:\path\shift_m3_capture.jsonl
```

Optional backbuffer capture:

```powershell
set SHIFT_D3D9_CAPTURE_SCREENSHOT=1
set SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY=30
set SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR=C:\path\capture\
```

---

# BMW runtime capture preflight

Для быстрой проверки внешнего capture без запуска полного render pipeline:

```bash
python bmw_runtime_capture_preflight.py \
  runtime_binding.json \
  runtime_capture_preflight.json \
  --resource-sha256 960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c
```

Команда по умолчанию проверяет exact retail M3 MEB SHA, ищет target-MEB draw и документированные paint ranges. Результат
диагностический и не заменяет strict same-instance gate.

# One-command BMW post-capture pipeline

Once a real runtime JSONL trace exists:

```bash
python bmw_post_capture_pipeline.py \
  BMW_M3_E36.bff \
  RENDER.bff \
  shift_m3_capture.jsonl \
  out/bmw_runtime
```

The pipeline preserves each boundary:

```text
BFF
 │
 ├── real MaterialBinding
 ├── exact target MEB
 └── runtime JSONL
          │
          ▼
   runtime evidence
          │
          ▼
 exact VS/PS selection
          │
          ▼
 runtime RenderContract
          │
          ▼
 captured-shader offline render
```

Typical output:

```text
out/bmw_runtime/
├── material_binding.json
├── mesh.json
├── runtime_binding.json
├── runtime_shader_selection.json
├── runtime_render_contract.json
├── shader_render_result.json
├── bmw_m3_e36_shader_executed.ppm
└── pipeline_result.json
```

A blocked stage still writes its report. The command exits non-zero when evidence is insufficient; it never fabricates a ready render.

---

# Offline tools

### Inspect / validate / extract

```bash
python shift_importer.py inspect VEHICLES.bff
python shift_importer.py manifest /path/to/Dir/ manifest.json --decode
python shift_importer.py validate /path/to/Dir --report validation.json
python shift_importer.py extract /path/to/Dir extracted/
```

### Build IR

```bash
python shift_importer.py build-ir /path/to/bffs android_ir/
SHIFT_LZX_NATIVE=1 python shift_importer.py build-ir /path/to/bffs android_ir_native/
```

### Real BMW MEB render

```bash
python bff_meb_render.py \
  BMW_M3_E36.bff \
  vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb \
  out/bmw_m3_e36_body.ppm \
  --mesh-json out/bmw_m3_e36_body.mesh.json
```

### Real BMW VHF assembly

```bash
python bff_vehicle_render.py \
  BMW_M3_E36.bff \
  vehicles/bmw_m3_e36/bmw_m3_e36.vhf \
  out/bmw_m3_e36_kit00_vehicle.ppm \
  --mesh-json out/bmw_m3_e36_kit00_vehicle.mesh.json
```

### VHF material preview

```bash
python vhf_material_preview.py \
  BMW_M3_E36.bff \
  vehicles/bmw_m3_e36/bmw_m3_e36.vhf \
  out/bmw_m3_e36_kit00_material.ppm \
  --material-resource vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt \
  --scene-json out/bmw_m3_e36_kit00_material.json
```

This is intentionally a texture-only checkpoint; it does not claim final `bodywork.fx` semantics.

### Split BFF shader probe

```bash
python bmw_split_bff_shader_probe.py \
  BMW_M3_E36.bff \
  out/bmw_m3_e36_shader_probe.json \
  --supplemental-bff RENDER.bff
```

### RENDER.bff evidence

```bash
python shift_importer.py render-bff-evidence \
  BMW_M3_E36.bff RENDER.bff \
  out/bmw_m3_e36_render_bff_evidence.json \
  --supplemental-bff BMW_M3_E36_Cockpit.bff
```

---

# MEB evidence corpus

The evidence collector packages the exact bytes needed for reverse-engineering without copying full retail archives:

```bash
python3 tools/collect_meb_evidence.py \
  "/path/to/Need for Speed Shift" \
  --source "/path/to/SHIFT.exe.c" \
  -o shift_meb_evidence.zip
```

The supplied 1.02 corpus records:

- **70,370** parsed MEB resources;
- **1,834** BFF archives;
- property **460** in every observed resource;
- exact descriptor **[4, 6, 0]** for the observed 460 property;
- byte-identical decoded/raw color payloads;
- no positive property **461** resource in that corpus.

The large evidence bundle is intentionally kept outside Git; compact aggregate findings and hashes are sufficient for repository regression.

---

# Shader and render architecture

FXO bytecode becomes neutral `SHIFT.ShaderProgram/1` data and feeds both the desktop oracle and GLES backend.

Supported reference execution includes:

- arithmetic/vector operations;
- dot/cross/normalize;
- CMP/LRP and scalar math;
- TEX/TEXLDD/TEXLDL;
- DSX/DSY;
- bounded control flow;
- D3D9 relative constant addressing;
- deterministic material c-register banks;
- VS→PS semantic linkage;
- sampler2D and samplerCube resources.

Unsupported forms remain explicit blockers.

The render ABI is:

```text
RenderBinding/1
   ├── StaticDraw/1
   └── SkinnedDraw/1
            │
            ▼
      RenderCommand/1
            │
      ┌─────┴─────┐
      ▼           ▼
 RenderResources  ShaderProgram
      │           │
      └─────┬─────┘
            ▼
     desktop reference
```

`SHIFT.MaterialConstantPayload/1` carries deterministic 16-byte D3D9-style c-register slots.

External resources are explicit: `s0` shadow-map evidence requires a 2D resource; `s3` environment-map evidence requires a cube resource.

---

# Skinning

Skinning is deliberately separated from animation decoding:

1. **BindSkeleton** — BAB/BAS ↔ MEB linkage.
2. **SkinPose** — explicit matrix palette.
3. **CPU reference** — deterministic linear-blend skinning.
4. **GLES ABI** — palette + BLENDWEIGHT0/BLENDINDICES0.
5. **Animation decoding** — separate evidence problem.

This allows deformation to be proven without inventing a BAB animation grammar.

---

# Roadmap

## Milestone A — Close the BMW runtime evidence gate

**Immediate work**

1. Capture one real BMW M3 body frame.
2. Validate the capture schema.
3. Correlate the exact MEB resource, declaration and indexed draw in the same frame.
4. Correlate the exact VS/PS permutation with FXO.
5. Verify VS/PS constants against the material payload.
6. Verify `s0` / `s3` resource types and captured surfaces.
7. Run the post-capture pipeline.
8. Produce the first non-synthetic offline BMW render.
9. Compare it against the retail backbuffer.
10. Store a deterministic image/hash checkpoint.

**Exit:** one real M3 draw has a complete same-instance evidence chain and a reproducible reference image.

## Milestone B — Desktop renderer parity

- expand shader execution only when evidence requires it;
- resolve remaining lighting/blend/material semantics;
- validate sampler state and extended UV families;
- close TEXCOORD5 where evidence permits;
- add image-diff regression checkpoints.

**Exit:** deterministic reproduction of the selected retail draw within a defined image-diff tolerance.

## Milestone C — GLES 3.1 parity

- compile selected shader permutations;
- match RenderCommand attributes/resources/constants;
- run desktop-vs-GLES parity;
- package runtime-independent IR/shader resources;
- remove importer dependencies from the renderer boundary.

**Exit:** the same IR produces equivalent desktop and GLES output.

## Milestone D — Android renderer

- implement the renderer around the proven RenderCommand ABI;
- load content-addressed IR directly;
- reuse neutral shader/resource contracts;
- establish a real BMW smoke test;
- expand to scene composition after the vehicle path is stable.

**Exit:** packaged BMW M3 IR renders on Android without the original SHIFT runtime.

## Milestone E — Scene and gameplay

Only after the renderer boundary is stable:

- SGB scene semantics;
- tracks;
- camera;
- input;
- physics;
- audio;
- gameplay.

---

# Repository map

| Path | Role |
|---|---|
| `shift_importer.py` | Main CLI and evidence entry point |
| `bff_format.py` / BFF modules | BFF/XMem/LZX handling |
| `meb_format.py` | MEB parser and property provenance |
| `bmw_material_from_bff.py` | Real BMW material extraction |
| `bmw_golden_gate.py` | BMW evidence/render gate |
| `bmw_runtime_shader_select.py` | Exact runtime VS/PS selection |
| `bmw_runtime_render_contract.py` | Runtime readiness contract |
| `bmw_runtime_shader_render.py` | Captured shader offline execution |
| `bmw_post_capture_pipeline.py` | End-to-end post-capture pipeline |
| `d3d9_runtime_trace.py` | Runtime evidence ingestion |
| `native_capture/` | Windows D3D9 producer |
| `reference_renderer.py` | Desktop reference renderer |
| `static_draw.py` / `skinned_draw.py` | Draw contracts |
| `render_command.py` | Neutral submission ABI |
| `skinning*.py` | CPU/GLES skinning |
| `tools/` | Evidence/corpus/snapshot tooling |
| `tests/` | Regression tests |
| `docs/` | Phase-specific technical documentation |

---

# Documentation

Detailed status is intentionally split into focused documents:

- [Roadmap](ROADMAP.md)
- [Vertex ABI status](VERTEX_ABI_STATUS.md)
- [Reference renderer status](REFERENCE_RENDERER_STATUS.md)
- [Shader backend status](SHADER_BACKEND_STATUS.md)
- [Skinning status](SKINNING_STATUS.md)
- [Texture render status](TEXTURE_RENDER_STATUS.md)
- [Track scene status](TRACK_SCENE_STATUS.md)
- [Draw packet status](DRAW_PACKET_STATUS.md)
- [Upload contents](UPLOAD_CONTENTS.md)

---

# Testing

Full Python suite:

```bash
python -m pytest
```

Focused BMW runtime tests:

```bash
python -m pytest \
  tests/test_bmw_runtime_capture_pipeline.py \
  tests/test_bmw_post_capture_pipeline.py
```

The Windows D3D9 producer has a separate native/CI boundary.

---

# Development rules

1. **Evidence beats plausibility.**
2. **Provenance travels with data.**
3. **Ambiguity is a valid result.**
4. **Static and runtime evidence stay separate.**
5. **Gates fail closed.**
6. **The desktop renderer remains the deterministic oracle until GLES parity is established.**

---

# Asset policy

Retail archives and executable dumps are analysis inputs, not repository source code.

The repository should contain parsers, compact fixtures, deterministic evidence, hashes/provenance, generated checkpoints and documentation. Large retail payloads should remain outside Git unless redistribution is clearly permitted.

See [NOTICE.md](NOTICE.md).

<p align="center">
  <strong>Goal:</strong> turn verified SHIFT data into a reproducible renderer — one evidence-backed boundary at a time.
</p>


> **PE-backed COLOR ABI:** Phase 205 makes the exact SHIFT.exe Type/Usage table an optional input to the COLOR bridge. Type 4 is validated as RGBA32 / D3DCOLOR; Usage ordinal 6 is validated as Colour / numeric D3D9 Usage 10. The runtime same-instance declaration gate remains separate.


> **Vulkan headless checkpoint:** Phase 206 adds a real Linux Vulkan offscreen image submission path. It creates a device/queue, clears an R8G8B8A8 image, copies it through a staging buffer and emits a deterministic PPM without a window system. Shader and RenderCommand execution remain the next stages.


> **Vulkan graphics checkpoint:** Phase 207 adds an optional headless SPIR-V triangle pipeline. When `glslangValidator` is available, Linux can compile the shader pair, create a real Vulkan graphics pipeline and export an offscreen PPM. BMW RenderCommand integration is the next backend stage.

 
> **RenderCommand → Vulkan geometry:** Phase 208 introduces SHIFT.VulkanGeometryPacket/1. Python materializes a selected RenderCommand triangle-list into a native handoff; Vulkan consumes only that packet, uploads vertex/index buffers and performs a depth-tested offscreen draw. POSITION0 is the first supported attribute.


> **Vulkan VertexLayout v2:** Phase 209 carries multiple proven/inferred vertex attributes into the native packet and maps them to Vulkan formats. COLOR0 receives an explicit executable-backed BGRA→RGBA repack; unresolved COLOR1 remains deferred. The native geometry shader still consumes POSITION0 only.


> **Linux Vulkan runner:** Phase 210 adds vulkan_render_command.py, a one-command bridge from RenderBinding/1 to the native Vulkan geometry target. It supports prepare-only validation, packet hashing and optional PPM output without moving BFF/MEB parsing into C++.

 
> **Vulkan shader path:** Phase 211 adds GLSL 450 emission and optional Vulkan-targeted glslang compilation for LinkedShaderPair/1. Both GLSL ES 3.1 and Vulkan stage sources are retained; native Vulkan descriptor upload remains next.


> **Vulkan constant upload:** Phase 213 adds SHIFT.VulkanConstantPacket/1 and a native descriptor upload checkpoint. D3D9 c-register banks are kept separate: VS at binding 14 and PS at binding 15. Ambiguous stage mapping is fail-closed.

 
> **Vulkan textures:** Phase 214 adds SHIFT.VulkanTexturePacket/1 and a native RGBA8 image/sampler upload path. D3D9 sampler registers are preserved as Vulkan descriptor-set-1 bindings; set 0 remains dedicated to VS/PS constants.


> **Vulkan textures:** Phase 214 adds a real RGBA8 image/sampler descriptor path. D3D9 sampler registers are preserved as Vulkan set 1 bindings; set 0 remains reserved for VS/PS constants. The current smoke shader exercises s1.


> **Vulkan samplerCube:** Phase 215 adds a dedicated SHIFT.VulkanCubeTexturePacket/1 path for BMW environmentMap/s3. Six explicit RGBA8 faces are uploaded into a cube-compatible image and bound at Vulkan set 1/binding 3; actual BMW cube content/orientation remains a runtime evidence gate.


> **BMW Vulkan bundle:** Phase 216 packages one exact M3 RenderCommand submesh into geometry/constants/texture/cube handoffs and preserves Vulkan shader source plus hashes. It is preparation-only; native BMW material execution remains the next stage.

 
> **Native Vulkan bundle runner:** Phase 218 adds the C++ boundary that consumes geometry/constants/texture/cube packets from `SHIFT.BMWVulkanBundle/1` without parsing game archives. Arbitrary mixed sampler shader execution remains explicitly blocked until SPIR-V reflection is implemented.


> **SPIR-V reflection:** Phase 219 adds dependency-free descriptor reflection for native Vulkan execution, including set/binding, sampler2D/samplerCube and constant-buffer classification. This removes the main Phase 218 blocker for automatic mixed-resource pipeline construction.


> **Vulkan bundle interface gate:** Phase 220 validates reflected SPIR-V descriptors against the actual geometry/constants/2D/cube packets before native pipeline creation. Missing `sN` resources or unsupported descriptor interfaces are fail-closed.


> **BMW material → Vulkan:** Phase 222 adds an adapter from the existing real BMW material-slice report to `SHIFT.BMWVulkanBundle/1`, preserving exact M3 MEB identity, Vulkan shader sources and source provenance. No additional archive parser is introduced.


> **Linux Vulkan CI:** Phase 223 adds Ubuntu/Mesa automated coverage for native Vulkan, including a mixed-resource bundle with D3D9 c-register banks, sampler2D and samplerCube. The test is synthetic and does not replace the real BMW D3D9 same-instance gate.


> **Phase 230:** native Vulkan texture C++ now compiles without the literal newline corruption, and COLOR ABI promotion is guarded by the complete 460/461 descriptor pair plus source-backed Type-4 evidence.


> **Vulkan stage gate:** Phase 231 validates reflected SPIR-V descriptor stages before native execution: VS c14, PS c15, and fragment-only set-1 sampled textures for the current native executor.


> **Phase 234:** VertexLayout ABI status mapping is now immutable, eliminating cross-test/runtime mutation as a source of confidence-state drift.


> **Phase 235:** the existing DDS decoder now feeds the native Vulkan texture/cubemap packet builders with source and decoded-pixel provenance; real BMW resource selection remains a separate evidence-bound step.


> **Phase 236:** the DDS → Vulkan bridge now converts decoder/packet incompatibilities into explicit blocking reasons and preserves provenance instead of leaking exceptions.


> **Phase 239:** the real BMW material slice preserves exact DDS provenance, and the Vulkan adapter can extract only those material DDS entries from supplied BFFs, verify SHA-256, and feed them through the existing DDS→Vulkan bridge. `s0`/`s3` remain explicit external/runtime boundaries unless an exact DDS is supplied.


> **Phase 240:** the BMW material→DDS→Vulkan adapter now propagates extraction blockers even when no packet is produced and sanitizes temporary paths from persistent DDS provenance.


> **Phase 241:** Linux Vulkan CI now enters through the `BMWMaterialSliceVulkan/1` adapter, retaining the mixed sampler2D/samplerCube/constants native smoke. Exact BFF DDS extraction remains separately tested through the Phase 239/240 provenance path.


> **Phase 242:** the material→DDS→Vulkan adapter recomputes final readiness from blocking reasons, and synthetic DDS fixtures now encode `caps`/`caps2` at their actual header offsets.


> **Phase 244:** `BMWMaterialSliceVulkan/1` now exposes the exact DDS bridge result directly at top level, matching the nested bundle report.


> **Phase 246:** the Vulkan runner now validates the sampler sidecar's format and SHA-256 binding to `textures.svtp` before native execution; legacy bundles without the sidecar remain compatible.


## BAB animation runtime reconstruction

Phase 247 adds a source-backed decoder for the animation payload after the verified BAB header/bone table. It reconstructs runtime bank variants 0/1/2, channel types 0–9, per-channel metadata and the proven interpolation rules. The parser is evidence-driven: unresolved axis/order details and unconsumed bytes remain explicit blockers.

Run it on an extracted BAB resource with a runtime mode recovered from the source:

    python shift_importer.py bab-animation-runtime animation/example.bab out/example.bab.runtime.json --mode 0

This phase does not modify the renderer or RENDER.bff workflow.
