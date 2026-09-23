# SHIFT importer — verified run results

Дата обновления: 2026-09-24
Последний полный CI baseline: 2026-09-23, Python **193 passed / 2 skipped**; post-merge `main` CI for phase 44 также successful.

## BFF/XMem

- Базовый набор `Dir.zip`: 15 BFF, 4,115 записей.
- Полная декомпрессия всех 4,115 ресурсов: **4,115 OK / 0 failed**.
- Native C++ XMem/LZX проверен сравнением с Python decoder на 37 реальных потоках из разных BFF.
- Native XMem/LZX отдельная golden regression: `AI.bff / ai/alpental_drift.aia.xml`, 4,194 → 66,246 bytes, byte-identical с эталоном.
- Native backend использует 4-byte zero look-ahead, необходимый для совместимости с референсной LZX битовой моделью.
- Native backend в Python importer включается только через `SHIFT_LZX_NATIVE=1`; по умолчанию остаётся pure-Python fallback.

## Format layer

Проверены и реализованы:

- BFF v3 / Type 0 / Type 1 / Type 2 XMem-LZX
- DDS metadata
- Reflection XML
- BMLY/BML
- BMT material graph
- HLSL/Fx source inventory (`.fx/.fxh`)
- MEB → `MGEO`
- CSM → `CMES`
- VHF/CAR → `SHIFT.VHFScene`
- SGB → `SHIFT.SGB` top-level chunk index
- loose LOD XML parser
- generic XML resources

## Geometry / collision samples

- Alpental `grid1_02.meb`: 4 vertices / 2 triangles.
- BMW M3 cockpit MEB sample: 17 vertices / 13 triangles.
- Camaro cockpit MEB sample: 341 vertices / 401 triangles.
- Alpental skin MEB sample: 144 vertices, 8 vertex properties, skeleton 19 bones.
- Nordschleife `nordschleife07.360.csm`: 363 vertices / 629 triangles / 1,887 indices, all indices valid.

## Vehicle render graph

Для BMW M3 E92 Cockpit + BMW Z4 M Cockpit + Camaro Cockpit + RENDER:

- 614 selected graph nodes
- 1,442 dependency edges
- 1,442 resolved
- 0 unresolved
- legacy aliases resolved: `.mtx → .bmt`, `.fx → .fxh`

## Full base Android IR

`base_ir_full/`:

- 15 archives
- 3,942 converted resources
- 0 failed
- 1,563 DDS textures
- 592 FXO shader binaries preserved as raw IR
- 26 MEB → MGEO
- 2 CSM → CMES
- 1,742 JSON analyses
- 2,172 raw payload outputs

## Full track IR

`track_ir_full_native/`:

- 15 archives
- 3,323 selected resources
- 3,323 converted
- 0 failed
- 26 MEB → MGEO
- 2 CSM → CMES
- 1,563 DDS preserved
- 19 BMT analyses
- 103 source shader analyses

Размер полного IR большой и намеренно не входит в release source archive.

## Tests

- Python CI: **193 passed, 2 skipped**
- Native C++ IR reader test: passed
- Native C++ LZX golden test: passed

## Implemented runtime-oriented boundaries

- SHIFT.VertexLayout/1: explicit ABI evidence states and semantic collision reporting.
- SHIFT.MaterialBinding/1: deterministic FXO selection plus linked SHIFT.LinkedShaderPair/1.
- SHIFT.LinkedShaderPair/1: semantic VS/PS varying locations and VertexLayout input locations.
- SHIFT.StaticDraw/1: vertex ABI, submesh range, texture and uniform readiness blockers.
- SHIFT.DrawPacket/1 and SHIFT.RenderBinding/1: canonical packet construction with attached StaticDraw contract.
- Desktop reference renderer: deterministic DrawPacket-to-StaticDraw raster path with submesh range handling, direct RenderCommand execution, SHA-256 golden output, UV0 texture reference sampling and CLI execution.
- Skinning: explicit SkinPose/1, CPU reference, GLES 3.1 ABI and bind-pose equivalence check.
- RenderCommand/1: strict submission validation, explicit GLES vertex setup, linked shader validation, sampler-state propagation and multi-texture register collision checks.
- Texture reference: DDS DXT1/DXT3/DXT5 and common 32-bit masked decode, address/filter sampling and textured RenderCommand CLI.
- BAB evidence tooling: corpus fingerprinting and byte-level payload comparison without keyframe grammar guessing.

## Current remaining RE/runtime layers

Это ещё не готовый APK и не законченный игровой runtime. Остались:

- глубокий semantic decode `FXO` → GLES/Vulkan shader IR;
- semantic scene assembly для SGB (`NODE/FLAT/SUMM`, beyond chunk indexing);
- `IMB` animation semantics;
- consolidation vehicle/track physics into runtime data model;
- runtime replacement of PhysX 2.x and integration with Android rendering/input/audio;
- scene streaming, memory budgets, LOD and complete gameplay state.
