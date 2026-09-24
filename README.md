# Need for Speed: SHIFT — Decompilation & Resource IR

Инструментальный проект для поэтапной реконструкции форматов, зависимостей и runtime-границ **Need for Speed: SHIFT** с прицелом на воспроизводимый Android renderer.

> **Текущий статус:** mainline развивается через **phase 71** — command-level skinned reference. RenderCommand, VS→PS reference, skinning, external samplers и cubemap decode уже образуют единый исследовательский конвейер.

Проект не пытается сразу переписать игру. Он строит проверяемый конвейер:

    Original BFF/resources
            │
            ▼
       Import / Decode
            │
            ▼
     Neutral IR + blobs
            │
            ├── MEB / VHF / BMT / FX / FXO / DDS
            │
            ▼
     Resource + Shader Linking
            │
            ▼
     DrawBinding → StaticDraw / SkinnedDraw
            │
            ▼
     RenderResources + RenderCommand
            │
            ├── Desktop reference renderer
            └── GLES 3.1 backend
                     │
                     ▼
              future Android runtime

## Главная идея

Цель — получить **детерминированное, evidence-driven представление данных SHIFT**, которое можно массово импортировать, проверять регрессионными тестами, воспроизводить вне оригинального runtime и постепенно переносить на Android/GLES.

> **Неподтверждённая семантика не угадывается.**

Неоднозначные поля остаются `inferred`, `ambiguous` или `unknown`; runtime boundary возвращает machine-readable blocker.

## Текущий статус

| Слой | Статус | Что есть сейчас |
|---|:---:|---|
| BFF / XMem / LZX | ✅ | v3 entries, ranges, raw/zlib/XMem+LZX, native backend |
| Resource IR | ✅ | manifest, SHA-256, content-addressed blobs, dependency graph |
| Reflection / BML / XML | ✅ | typed parsing, inheritance, BML blocks, generic XML tree |
| BMT / FX / FXO | ✅ | material graph, shader params, sampler mapping, CTAB metadata |
| MEB geometry | ✅ | vertices, indices, UVs, normals, tangents, skin streams, ABI metadata |
| Shader IR | ✅ | SHIFT.ShaderProgram/1, D3D9 register/operand decoding, typed reflection |
| GLSL ES 3.1 | ✅ | generated stages + optional compile/link validation |
| RenderCommand | ✅ | vertex setup, constants, resources, readiness gate |
| Desktop reference | 🟢 | geometry, textured materials, multi-sampler, VS→PS semantic linkage |
| Cubemaps | ✅ | ReferenceCubeTexture/1, samplerCube, complete DDS cubemap decode |
| Skinning | 🟢 | explicit SkinPose, CPU LBS reference, GLES ABI, skin inputs |
| Android runtime | ⏳ | после стабилизации reference pipeline |

## Проверенные MEB semantics

| MEB property | Semantic | Представление |
|---:|---|---|
| 200 | POSITION0 | FLOAT32x3 |
| 220 | NORMAL0 | FLOAT32x3 |
| 240 | TANGENT0 | FLOAT32x3 |
| 250 | BINORMAL0 | FLOAT32x3 |
| 130–134 | TEXCOORD0–4 | FLOAT32x2 |
| 230–234 | TEXCOORD0–4 family | FLOAT32x3 UVW |
| — | TEXCOORD5 | **shader-proven, MEB source unresolved** |
| 310 | BLENDWEIGHT0 | FLOAT32x4 |
| 580 | BLENDINDICES0 | UINT8x4 |
| 460 / 461 | COLOR0 / COLOR1 | **ambiguous** |

`COLOR0/1` сознательно остаются заблокированными там, где выбор D3D9 declaration или RGBA/BGRA byte order влияет на результат.

## Shader reference

FXO bytecode переводится в neutral `SHIFT.ShaderProgram/1` и используется двумя путями: generated GLSL ES 3.1 и строгий desktop software oracle.

Уже поддержаны:

- arithmetic / vector operations;
- dot / cross / normalize;
- CMP / LRP / scalar math;
- TEX / TEXLDD / TEXLDL reference path;
- DSX / DSY;
- bounded structured control flow;
- D3D9 a0-relative constant addressing;
- material constant payload → deterministic c-register banks;
- VS→PS linkage по `(usage,index)`.

Неподдержанные opcode/resource forms не отбрасываются молча: они становятся явным `unsupported` или `error` состоянием.

## Material и render contracts

Основные нейтральные схемы образуют цепочку:

    RenderBinding/1
          │
          ├── StaticDraw/1
          └── SkinnedDraw/1
                    │
                    ▼
             RenderCommand/1
                    │
              ┌─────┴─────┐
              ▼           ▼
      RenderResources   ShaderProgram
              │           │
              └─────┬─────┘
                    ▼
           desktop reference

Для material constants используется `SHIFT.MaterialConstantPayload/1` с 16-byte register slots и deterministic byte offsets.

Renderer-global resources передаются явно по `sN`. Для `environmentMap → s3` существует отдельный cube-resource contract; обычный 2D image не подменяет cube map.

## Skinning

Skinning разделён на независимые уровни:

1. **BindSkeleton** — точная привязка BAB/BAS к MEB skeleton.
2. **SkinPose** — явная matrix palette в `SHIFT.SkinPose/1`.
3. **CPU reference** — deterministic linear-blend skinning.
4. **GLES ABI** — std140 palette + BLENDWEIGHT0/BLENDINDICES0.
5. **Animation decoding** — отдельная задача; opaque BAB tail не интерпретируется без evidence.

Phase 60 добавил `SHIFT.SkinnedMeshReference/1`, phase 61 подключил его к desktop reference renderer, phase 62 — к embedded VS→PS execution, phase 63 — к `RenderCommand/1`, phase 64 вывел тот же skin payload в GLES 3.1 ABI, а phase 65 добавил явные extended semantic streams для shader inputs.

## Быстрый старт

### Импорт

    python shift_importer.py inspect VEHICLES.bff
    python shift_importer.py manifest /path/to/Dir/ manifest.json --decode
    python shift_importer.py validate /path/to/Dir --report validation.json
    python shift_importer.py extract /path/to/Dir extracted/
    python shift_importer.py package /path/to/Dir shift_assets/

### Анализ

    python shift_importer.py analyze-resource VEHICLES.bff cars/bmw_m3_e36/body.meb --output body.json
    python shift_importer.py analyze-resource GUI.bff gui/hud/hud.bmt --output material.json
    python shift_importer.py analyze-dir /path/to/Dir reports/ --ext .bmt .fx .fxh .meb .bab .bas .csm .xml .lod .vud .cpt
    python shift_importer.py graph /path/to/bffs graph.json

### Построение IR

    python shift_importer.py build-ir /path/to/bffs android_ir/
    SHIFT_LZX_NATIVE=1 python shift_importer.py build-ir /path/to/bffs android_ir_native/

### Render reference

    python draw_packets.py resource_analysis.json draw_packets.json
    python reference_renderer.py command.json --render-command --textured --shader-reference --mesh mesh.json --texture body.dds --output body.ppm
    python shift_importer.py color-evidence 460 color.bin color-evidence.json
    python shift_importer.py color-evidence 460 color.bin color-evidence.json --expected-rgba expected.rgba
    python shift_importer.py color-evidence 460 meb.json color-evidence.json --mesh-json
    python shift_importer.py color-evidence-resource VEHICLES.bff cars/bmw_m3_e36/body.meb 460 body-color-evidence.json
    python shift_importer.py color-evidence-corpus evidence/ color-corpus.json
    python shift_importer.py color-evidence-bff-corpus /path/to/bffs color-bff-corpus.json

Дополнительные bindings:

    # material sampler sN
    --texture-binding 1=specular.dds

    # renderer-global 2D sampler sN
    --external-texture-binding 0=shadow.dds

    # renderer-global cube sampler sN
    --external-cube-face 3=px=env_px.dds
    --external-cube-face 3=nx=env_nx.dds
    --external-cube-face 3=py=env_py.dds
    --external-cube-face 3=ny=env_ny.dds
    --external-cube-face 3=pz=env_pz.dds
    --external-cube-face 3=nz=env_nz.dds

## Структура IR

    shift_assets/
    ├── blobs/
    │   └── <sha256>
    ├── manifest.json
    ├── path_map.json
    ├── stats.json
    └── analysis/
        ├── materials/
        ├── reflection/
        ├── shaders/
        ├── bml/
        └── ...

Android runtime не должен читать BFF напрямую. Импортёр заранее строит neutral IR, а runtime получает подготовленные ресурсы и контракты.

## Тестирование

CI запускает полный Python suite и отдельную native regression:

    python -m pytest -q

    cmake -S native_ir -B native_ir/build -DCMAKE_BUILD_TYPE=Release
    cmake --build native_ir/build --parallel
    ./native_ir/build/test_ir <mgeo-fixture> <cmesh-fixture>

При наличии `glslangValidator` pipeline также проверяет compile/link generated GLSL ES 3.1 stages.

## Roadmap

    BFF → IR
       ├── Geometry
       ├── Material
       ├── Shader
       └── Skeleton / Animation
                 │
                 ▼
          RenderCommand
                 │
          ┌──────┴──────┐
          ▼             ▼
   Desktop reference  Android/GLES

Ближайшие задачи:

- **Phase 61** — skinned draw проходит через desktop reference rasterizer после explicit SkinPose.
- **Phase 62** — transformed skinned mesh проходит через embedded VS→PS reference path.
- **Phase 63** — SkinnedDraw нормализуется в общий RenderCommand/1 ABI.
- **Phase 64** — RenderCommand напрямую подаёт SkinPose/palette в GLES 3.1 ABI.
- **Phase 65+** — связать этот путь с реальным material permutation и shader-driven skin render.
- Доказать `COLOR0/1` type + channel order.
- Расширить real BMW shader coverage: remaining varyings, opcodes и control flow.
- Довести material/light/blend semantics до воспроизводимого golden render.
- Расшифровать BAB animation payload по corpus + byte-diff evidence.
- После стабилизации vehicle path перейти к SGB/track assembly.
- Затем — Android runtime.

Для `COLOR0/1` evidence utility принимает сырой 4-byte stream, MEB JSON (`--mesh-json`) или реальный `.meb` внутри `.bff` (`color-evidence-resource`). `color-evidence-corpus` агрегирует несколько отчётов и показывает межсемпловую стабильность кандидатов, но итог всегда остаётся `not-selected`.

Подробный план находится в [ROADMAP.md](ROADMAP.md).

## Документация по слоям

| Документ | Назначение |
|---|---|
| [ROADMAP.md](ROADMAP.md) | единый план реализации |
| [docs/RENDER_PIPELINE_STATUS.md](docs/RENDER_PIPELINE_STATUS.md) | render/link/reference pipeline |
| [REFERENCE_RENDERER_STATUS.md](REFERENCE_RENDERER_STATUS.md) | desktop reference |
| [SHADER_BACKEND_STATUS.md](SHADER_BACKEND_STATUS.md) | D3D9 → ShaderProgram → GLSL |
| [VERTEX_ABI_STATUS.md](VERTEX_ABI_STATUS.md) | MEB vertex semantics |
| [SKINNING_STATUS.md](SKINNING_STATUS.md) | skeleton, pose, skinning |
| [TEXTURE_RENDER_STATUS.md](TEXTURE_RENDER_STATUS.md) | DDS / sampler / cubemap |
| [docs/SKINNED_DRAW_STATUS.md](docs/SKINNED_DRAW_STATUS.md) | SkinnedDraw contract |

## Evidence policy

Проект ставит воспроизводимость выше «красивого» результата:

- parser output не считается verified только потому, что он синтаксически правдоподобен;
- ambiguous fields не выбираются по file order или удобству;
- runtime contracts должны содержать явные blockers;
- каждая новая ABI-гипотеза должна получать позитивный и негативный regression case.

Особенно осторожно обрабатываются D3D9 vertex declarations, COLOR0/1 packing, shader permutation selection, renderer-global resources и BAB animation grammar.

## Данные и лицензирование

Код предназначен для исследовательского reverse engineering и tooling. Оригинальные игровые данные в репозиторий не включаются.


The neutral renderer contract now has a common submission shape for skinned draws. `build_skinned_render_command()` carries explicit SkinPose and bind-palette data alongside the existing vertex/material/resource validation. This is the handoff point for the future GLES skinning backend.


## Phase 64: RenderCommand → GLES skinning ABI

`skinning_glsl.py` now exposes a direct `SHIFT.RenderCommand/1` → `SHIFT.GLES31Skinning/1` adapter. The Android-facing layer can consume the same SkinPose, bone count and vertex locations that were validated by the neutral render command, without depending on the importer or the original SkinnedDraw builder.


## Phase 68: COLOR evidence directly from BFF/MEB

Для реальных архивов добавлена команда `color-evidence-resource`: она извлекает указанный `.meb` из `.bff`, читает `colors`/`colors2` и строит тот же `SHIFT.ColorABIEvidence/1`. Это убирает ручной шаг `convert-meb --format json`; выбор `RGBA/BGRA` остаётся исключительно evidence-driven.

Пример:

    python shift_importer.py color-evidence-resource VEHICLES.bff cars/bmw_m3_e36/body.meb 460 body-color-evidence.json


## Phase 70: COLOR evidence over the BFF corpus

`color-evidence-bff-corpus` scans one BFF or a directory of BFF archives, decodes every `.meb` containing property 460/461 and aggregates the resulting evidence with archive/resource provenance. This is the canonical batch workflow for the unresolved COLOR ABI.


## Phase 71: Skinned RenderCommand reference

Desktop reference теперь умеет принимать готовый `SHIFT.RenderCommand/1` skinned draw и пройти всю локальную цепочку `SkinPose → SkinnedMeshReference → embedded VS → semantic linkage → PS → raster`. Это делает `RenderCommand/1` реальной точкой входа для cross-backend verification, а не только метаданными для GLES.
