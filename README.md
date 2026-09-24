# Need for Speed: SHIFT — Decompilation & Resource IR

Инструментальный проект для поэтапной реконструкции форматов, зависимостей и runtime-границ **Need for Speed: SHIFT** с прицелом на воспроизводимый Android renderer.

> **Текущий статус:** mainline развивается через **phase 136** — импортёр умеет распаковывать MEB непосредственно на диск, а supplied 1.02 corpus дал массовое доказательство `MEB 460 -> D3D9 Type 4 / D3DCOLOR, Usage 6, Channel 0`. RenderCommand, VS→PS reference, skinning, external samplers, cubemap decode и machine-readable declaration evidence образуют единый исследовательский конвейер.

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
    python bmw_golden_gate.py evidence/bmw_m3_e36_kit00_body_loda.golden.json draw_packets.json
    python tools/analyze_meb_evidence_bundle.py shift_meb_evidence.zip -o meb_corpus.json

### D3D9 runtime evidence

Для реального memory dump:

    python shift_importer.py capture-d3d9-memory-declaration dump.bin 0x12340000 declaration-memory.json --offset 0x200 --length 0x200

SHIFT.D3D9MemoryDeclarationEvidence/1 сохраняет endianness, виртуальный адрес начала/конца slice, исходный размер dump, SHA-256 исходника и slice, точные raw bytes и декодированный Stream/Offset/Type/Method/Usage/UsageIndex. Из slice автоматически выделяется declaration array до точного D3DDECL_END-sentinel. Отсутствие sentinel остаётся partial; hash/provenance не считается подтверждением подлинности внешнего dump.

Цепочка может принимать этот отчёт напрямую:

    python shift_importer.py validate-d3d9-declaration-chain         type-profile.json stream-topology.json stream-record.json canonicalizer.json         declaration-chain.json --pe-evidence pe-evidence.json         --runtime-memory-evidence declaration-memory.json

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

Для больших corpus bundle анализ выполняется потоково: `tools/analyze_meb_evidence_bundle.py` читает `resources.jsonl` построчно и не загружает весь JSONL в RAM. Collector `tools/collect_meb_evidence.py` складывает распакованные `.meb` на диск в `<output-stem>_extracted/`; каталог можно переопределить через `--extract-dir`.

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


## Phase 72 — source-backed COLOR evidence

Полный `SHIFT.exe.c` добавил новый уровень доказательств для `COLOR0/1`: оригинальный
renderer содержит packed-color helper `FUN_008310c0`, который собирает RGBA float4 в
`0xAARRGGBB`; на little-endian Windows это соответствует BGRA bytes. Этот helper также
участвует в vertex-buffer conversion path `FUN_00854e70`.

Это сужает пространство гипотез, но не закрывает ABI полностью: связь именно MEB 460/461
с `D3DCOLOR` ещё должна быть доказана отдельным declaration evidence. Поэтому runtime
по-прежнему не выбирает candidate автоматически.

## Phase 73 — RenderCommand ↔ GLES parity

Для skinned draw добавлен отдельный cross-backend gate `SHIFT.GLES31SkinningParity/1`.
Он сравнивает итоговый `RenderCommand/1` с GLES ABI по locations/formats, четырём
influences, SkinPose и bind-palette. Для матриц используется deterministic SHA-256,
поэтому backend не может незаметно пересобрать другую pose-палитру.

Любое расхождение остаётся machine-readable blocker; готовность RenderCommand и
GLES contract не считается эквивалентной без этого parity check.

## Phase 82 — direct PE image resolver

Phase 82 adds `source-d3d9-pe-evidence`, a pure-Python PE32/PE32+ resolver that maps the recovered Ghidra virtual addresses into file offsets and inspects the D3D9 lookup-table regions directly when they are file-backed. It can also dereference the 17 `PTR_DAT_00b901d0` entries to printable ASCII strings. Loader-initialized/BSS bytes remain explicitly unavailable; MEB 460/461 mapping is still not selected automatically.

## Phase 87 — D3D9 Stream grouping topology

Phase 87 records the constructor-side topology behind the declaration ABI. `FUN_00854e70` receives per-element arrays for Stream, Type ordinal, Usage ordinal and Channel, groups elements by Stream using a `0x14`-byte per-stream group, stores pointers to the shared 8-byte declaration records, and accumulates per-stream byte size through `DAT_00b8eef0[Type]`. No MEB property ID is inferred from this chain.

## Phase 86 — D3D9 Type semantic validation profile

Phase 86 adds `d3d9_type_profile.py`: a deterministic profile for Type codes `0..16` with expected source-component counts and packed element byte sizes. `validate-d3d9-type-profile` compares these expectations to a phase-81 raw-memory evidence report and distinguishes `match`, `mismatch`, and `partial`/unavailable data. The profile is explicitly a validation oracle; it does not synthesize missing table bytes or resolve MEB 460/461 linkage.

## Phase 85 — D3D9 Type layout tables

Phase 85 records the source-backed runtime semantics of the Type layout tables. The declaration `Type` byte at `record +4` indexes `DAT_00b8eef0` for the element byte size used in offset accumulation, allocations and copies, and indexes `DAT_00b8ef38` for component counts used when reading source vertex data. The two bases are separated by `0x48` bytes, giving an 18-DWORD layout hint that includes sentinel Type `0x11`; initializer values remain opaque.

## Phase 84 — D3D9 declaration canonicalizer evidence

Phase 84 formalizes `FUN_00830f80`, the declaration canonicalizer/interning path. Its comparison loop checks both WORD fields and all four trailing BYTE fields of the same 8-byte record, so the complete `Stream/Offset/Type/Method/Usage/UsageIndex` tuple participates in declaration identity. The report remains source-backed and does not assign MEB properties 460/461 to a Type ordinal.

## Phase 83 — STREAM declaration record semantics

Phase 83 formalizes the 8-byte declaration records built by `FUN_008587e0`: type code at byte `+4`, usage code at `+6`, and Channel at `+7`, with 4-byte pointers to records stored in the owning array. The report ties XML `Type`/`Usage`/`Channel` parsing to those exact record fields while keeping the MEB 460/461 mapping unresolved.

## Phase 81 — raw D3D9 memory table decoder

Phase 81 adds `source-d3d9-memory-evidence`: a raw loaded-memory decoder for the opaque D3D9 tables. It extracts little-endian DWORD entries at the recovered addresses, 17 type-name pointers, and optionally the channel-table layout hint. Pointer dereferences are decoded only when they resolve to printable bytes inside the supplied memory window; otherwise the report stays unresolved. This prepares the missing declaration-table bytes without selecting an ABI automatically.

## Phase 80 — D3D9 usage semantics

Phase 80 records the recovered XML STREAM Usage domain `0..8` and its source-visible names. The source explicitly maps usage code `6` to `Colour`; usage code `3` remains tied to opaque `DAT_00b1d188` instead of being guessed. This closes the usage-name half of the COLOR chain while `MEB 460/461 -> Type ordinal` remains unresolved.

## Phase 79 — D3D9 lookup-table shape evidence

Phase 79 adds `source-d3d9-table-evidence`, which records the recoverable shape and indexing rules of the opaque D3D9 type/usage tables: `DAT_00b90088` is accessed as 4-byte entries, its adjacent symbol span is 0x50 bytes (20 DWORD slots as a layout hint), `DAT_00b900d8` spans 0x44 bytes (17 DWORD slots as a layout hint), and the XML loader searches exactly 17 type ordinals before feeding the selected ordinal to `FUN_00853c20`. The initializer bytes themselves remain opaque, and `MEB 460/461 -> type` remains not-proven.

## Phase 78 — D3D9 primitive type semantics

Phase 78 adds a reusable source-evidence layer for the recovered FUN_00854e70 declaration switch. All 17 type codes 0..16 are observed, their D3D9 declaration names are recorded, and exact conversion behavior is preserved. Type code 4 is source-backed as the packed-color path, while MEB 460/461 -> type code 4 remains unresolved.

## Phase 77 — CPrimitiveType source anchors

Phase 77 recovers original Win CPrimitiveType.cpp line numbers from decompiler diagnostic calls and records the mapping to exact decompiled source lines. This gives a stable bridge back to the original source logic while keeping the COLOR0/1 ABI unresolved.

## Phase 76 — type-table reference census

Phase 76 adds a complete source callsite census for FUN_00853c20 and records all embedded CPrimitiveType.cpp source-path references with exact source lines. The report now distinguishes an actively consumed opaque type table from an accidental symbol match while keeping MEB 460/461 -> D3D9 type unresolved.

## Phase 75 — source type-table chain evidence

Phase 75 adds source-line tracking and the recovered declaration type-table chain to source-d3d9-evidence: FUN_00853c20 -> DAT_00b90088, XML Type lookup through PTR_DAT_00b901d0, XML Usage/Channel, and the XML Colour stream family. This is stronger provenance for the original declaration path, but it still does not prove MEB 460/461 -> D3D9 type, so selection=not-selected remains authoritative.

## Phase 74 — source-d3d9-evidence

В проект добавлен `d3d9_source_evidence.py` и команда
`python shift_importer.py source-d3d9-evidence SHIFT.exe.c evidence.json`.

Она фиксирует source-level observations из recovered `SHIFT.exe.c`: packed-color
helper `FUN_008310c0`, vertex declaration/conversion path `FUN_00854e70` и
`STREAM` parser с `Type/Usage/Channel`. При этом точная связь MEB 460/461 с type 4
не повышается до verified без содержимого соответствующих глобальных таблиц.

## Phase 88 — declaration topology consistency

Phase 88 closes the source-evidence gap between individual D3D9 declaration records and their per-stream grouping. The recovered FUN_00854e70 path is now represented as SHIFT.D3D9StreamTopologyEvidence/1: Stream selects a 0x14-byte group, generated declaration records are retained through a per-stream pointer array, and the resolved Type indexes DAT_00b8eef0 for byte-size accumulation. The evidence layer accepts the recovered decompiler variants without assigning MEB property ids.

The PE evidence resolver is also aligned with the phase-85 source addresses: Type element-size data comes from DAT_00b8eef0 and component-count data from DAT_00b8ef38, each with the recovered 18-entry/sentinel layout. The resolver remains evidence-only and does not infer MEB-to-Type mapping.


## Phase 89 — PE Type-table semantic validation

The PE evidence path now decodes the file-backed Type element-size and source-component tables and runs them through SHIFT.D3D9TypeProfile/1. A real executable can therefore produce `match`, `mismatch`, or `partial` evidence for the recovered 17 Type ordinals without hardcoding runtime table bytes. MEB 460/461 linkage remains independent and is not inferred by this validator.

## Phase 90 — D3D9 declaration evidence chain

Добавлен `SHIFT.D3D9DeclarationChainEvidence/1`, который не переинтерпретирует исходник, а проверяет согласованность уже извлечённых доказательств:

    PE Type tables
          │
          ▼
    Type profile validation
          │
          ▼
    FUN_00854e70 — STREAM grouping
          │
          ▼
    FUN_008587e0 — 8-byte declaration record
          │
          ▼
    FUN_00830f80 — full-record canonicalization

Chain-report требует подтверждения каждого звена и возвращает `not-proven`, если хотя бы одно звено отсутствует или противоречит ожидаемой ABI-форме. Отдельно сохраняются границы доказательств: реальный runtime memory dump и экземпляр runtime declaration пока не предоставлены, а MEB 460/461 → D3D9 Type ordinal остаётся `not-proven`.

CLI:

    python shift_importer.py validate-d3d9-declaration-chain \\
        type-profile.json stream-topology.json stream-record.json canonicalizer.json \\
        declaration-chain.json --pe-evidence pe-evidence.json

## Phase 91 — raw D3D9 declaration instance

Добавлен `SHIFT.D3D9DeclarationInstanceEvidence/1` для декодирования реального буфера 8-байтных declaration records. Декодер расшифровывает `Stream/Offset/Type/Method/Usage/UsageIndex`, сверяет Type с recovered profile, выделяет `D3DDECLTYPE_UNUSED` (`0x11`), обнаруживает ненулевой Method и нецелый буфер. Никакие Usage или MEB 460/461 значения не синтезируются.

CLI:

    python shift_importer.py decode-d3d9-declaration declaration.bin declaration.json --count 32

## Phase 92 — declaration instance in the full chain

`validate-d3d9-declaration-chain` теперь принимает `--declaration-instance`. При переданном отчёте `SHIFT.D3D9DeclarationInstanceEvidence/1` chain добавляет отдельный обязательный check: instance должен быть полным, иметь stride 8 и сохранять подтверждённую D3DVERTEXELEMENT9-shaped форму. Несовпадение runtime instance блокирует итог `observed`; отсутствие instance сохраняет source-only режим без ложного утверждения runtime proof.


## Phase 93 — declaration instance integrity

Instance decoder теперь распознаёт полный `D3DDECL_END`-образный sentinel (`Stream=0xffff, Offset=0, Type=0x11, Method=0, Usage=0, UsageIndex=0`) отдельно от обычных элементов. Общая chain дополнительно fail-closed при несоответствии stride/shape даже если входной report ошибочно помечен `match`. Это подготовка к обработке реальных memory dumps без изменения MEB-части.


## Phase 94 — runtime memory declaration evidence

Добавлен SHIFT.D3D9MemoryDeclarationEvidence/1 — адресно-квалифицированный слой для реальных loaded-memory dump. Он фиксирует base address, slice offset, абсолютный диапазон, little-endian ABI, SHA-256 полного dump и выбранного slice, точные raw bytes и декодированный declaration instance.

Из slice автоматически выделяется массив до точного D3DDECL_END (ffff 0000 11000000). Байты после sentinel сохраняются как post_sentinel_bytes, поэтому широкий memory window не смешивается с самим declaration array. Некратный 8-byte диапазон, отсутствующий sentinel или неконсистентный record дают partial/mismatch, а недостоверность происхождения внешнего dump явно остаётся not-authenticated.

validate-d3d9-declaration-chain теперь принимает --runtime-memory-evidence и fail-closed перепроверяет формат, little-endian, диапазон, длину/raw bytes, SHA-256 slice и вложенный declaration instance. MEB 460/461 → D3D9 Type ordinal по-прежнему not-proven.


## Phase 95 — runtime declaration layout

Добавлен SHIFT.D3D9RuntimeDeclarationLayoutEvidence/1. Для фактического declaration instance validator группирует элементы по Stream и проверяет source-backed invariant из STREAM builder: первый Offset каждого Stream равен нулю, а следующий Offset равен предыдущему Offset плюс packed size его Type.

Результат сохраняет per-Stream element count, итоговый byte size, final Offset и Type codes, а несовпадение становится явным mismatch. Exact D3DDECL_END по-прежнему отделяет declaration array от любых последующих bytes. Этот слой усиливает runtime consistency, но не устанавливает MEB 460/461 → Type.


## Phase 96 — source provenance coherence

Declaration chain теперь умеет проверять согласованность provenance для source-backed звеньев. Когда evidence reports содержат SHA-256 исходного SHIFT.exe.c, chain требует совпадения sha256, размера и количества строк, а также имени исходного файла; конфликт становится blocker. Старые минимальные reports без hash сохраняют прежний режим, но новый guard включается автоматически, как только provenance предоставлен.


## Phase 97 — D3D9 declaration bind API

Добавлен SHIFT.D3D9ApiBindEvidence/1. Полный SHIFT.exe.c теперь анализируется на отдельном runtime boundary wrapper FUN_0082e510: он кеширует текущую declaration pointer и выполняет COM-vtable dispatch по смещению 0x15c. Для IDirect3DDevice9 это vtable slot 87, соответствующий SetVertexDeclaration. Source evidence и внешний API ordering теперь соединены в отдельный machine-readable слой.

Declaration chain принимает этот report как optional gate и включает его source provenance в общий snapshot coherence. Это закрывает путь declaration object → D3D9 bind call, но не закрывает MEB 460/461 → Type.


## Phase 98 — D3D9 render API boundary

Добавлен SHIFT.D3D9RenderApiBoundaryEvidence/1. Source evidence теперь фиксирует полный setup boundary для mesh primitive: declaration через slot 87 / 0x15c, vertex stream через slot 100 / 0x190, index buffer через slot 104 / 0x1a0 и indexed draw через slot 82 / 0x148. В recovered C эти вызовы наблюдаются через соответствующие wrappers и render-path ordering.

CLI:

    python shift_importer.py source-d3d9-render-api-boundary SHIFT.exe.c render-api.json

Declaration chain может принять этот report как дополнительный gate через --render-api-evidence. API mapping отделён от MEB property mapping; 460/461 → Type остаётся not-proven.


## Phase 99 — D3D9 declaration creation

Добавлен SHIFT.D3D9DeclarationCreateEvidence/1. FUN_00830f80 теперь формализован как source-backed creation boundary: canonicalizer выделяет buffer размера element_count * 8 + 8, копирует туда declaration-record bytes и передаёт buffer через IDirect3DDevice9 slot 86 (0x158), то есть CreateVertexDeclaration.

CLI:

    python shift_importer.py source-d3d9-declaration-create-evidence SHIFT.exe.c declaration-create.json

Это замыкает source-side путь 8-byte declaration records → CreateVertexDeclaration → declaration object, который затем используется Phase 97 для SetVertexDeclaration. MEB 460/461 → Type остаётся not-proven.


## Phase 100 — declaration count boundary

Добавлен SHIFT.D3D9DeclarationCountEvidence/1. FUN_0082ea90 считает 8-byte declaration records по первому WORD Stream и останавливается при Stream >= 0xff; затем FUN_00830f80 использует count для buffer size count * 8 + 8. Exact D3DDECL_END fields эта source-логика не проверяет, поэтому report отдельно оставляет связь stop rule → exact end sentinel как not-proven.

CLI:

    python shift_importer.py source-d3d9-declaration-count-evidence SHIFT.exe.c declaration-count.json


## Phase 101 — exact D3DDECL_END producer

Добавлен SHIFT.D3D9DeclarationSentinelEvidence/1. В FUN_008587e0 исходник явно записывает все шесть полей последнего 8-byte record: Stream=0xffff, Offset=0, Type=0x11, Method=0, Usage=0, UsageIndex=0. Это прямое source-доказательство точной формы D3DDECL_END; граница уже обнаруживается runtime decoder, а теперь также подтверждена producer-side.

CLI:

    python shift_importer.py source-d3d9-declaration-sentinel-evidence SHIFT.exe.c declaration-sentinel.json


## Phase 102 — runtime/source sentinel coherence

Declaration chain теперь сравнивает фактический D3DDECL_END из runtime memory evidence с source-proven producer из FUN_008587e0. Проверяются все шесть полей sentinel и согласованность end_sentinel_index с размером declaration array. Повреждение любого значения становится mismatch/not-proven.

CLI-цепочка:

    python shift_importer.py validate-d3d9-declaration-chain \
        type-profile.json stream-topology.json stream-record.json canonicalizer.json \
        declaration-chain.json \
        --runtime-memory-evidence declaration-memory.json \
        --declaration-sentinel-evidence declaration-sentinel.json


Phase 102 follow-up hardens the D3DDECL_END source matcher against Ghidra temporary-variable renaming. The uploaded SHIFT.exe.c uses local_14 for the sentinel record index, and the matcher now validates the field expressions without depending on a synthetic variable name.


## Phase 103 — D3D9 declaration lifecycle call chain

Добавлен SHIFT.D3D9DeclarationLifecycleEvidence/1. Source-анализ теперь фиксирует прямую цепочку: mesh construction → FUN_008587e0 → FUN_00830f80 → CreateVertexDeclaration, а render path → FUN_00854d30 → FUN_0082e510 → SetVertexDeclaration. Это объединяет ранее раздельные evidence reports в один статический lifecycle contract.

CLI:

    python shift_importer.py source-d3d9-declaration-lifecycle SHIFT.exe.c declaration-lifecycle.json

Report намеренно не утверждает конкретный runtime frame или конкретный mesh instance. MEB 460/461 → Type остаётся not-proven.


## Phase 104 — D3D9 binding arguments

Добавлен SHIFT.D3D9BindingArgsEvidence/1. Source-анализ фиксирует аргументы SetStreamSource: Stream из param_2, vertex-buffer из per-stream storage, OffsetInBytes=0 и Stride из stream-type getter. Для SetIndices фиксируется прямой forwarding восстановленного index-buffer pointer. Runtime resource identity остаётся отдельным boundary.

CLI:

    python shift_importer.py source-d3d9-binding-args SHIFT.exe.c binding-args.json

## Phase 105: conservative MEB 460/461 ↔ D3D9 color bridge

`d3d9_color_bridge_evidence.py` adds the missing evidence layer between the project's MEB COLOR0/COLOR1 storage contract and the recovered D3D9 declaration model. It records the current 4-byte normalized `u8x4` constraint for properties 460/461 and expresses the compatible D3D9 color candidates as numeric Type codes **4 (`D3DCOLOR`)** and **8 (`UBYTE4N`)**.

The bridge consumes `SHIFT.D3D9SourceVertexEvidence/1`: the recovered source proves the XML `Colour` stream family and a separate Type-4 packed-color path, but the source export does not expose a direct MEB-property-to-Type edge. The tool therefore keeps `meb_property_mapping.status = not-proven` even when a runtime declaration report contains a COLOR record.

Example:

    python d3d9_color_bridge_evidence.py meb.json source-d3d9.json color-bridge.json
    python d3d9_color_bridge_evidence.py meb.json source-d3d9.json color-bridge.json --runtime-report declaration.json --source-text SHIFT.exe.c

Runtime COLOR declaration observations are recorded separately from property identity. A future proof must correlate the same MEB payload, declaration record and render/bind path rather than selecting Type 4 from the packed-color helper alone.

## Phase 106: declaration-chain integration for MEB 460/461

The declaration-chain validator now accepts `SHIFT.MEBD3D9ColorBridgeEvidence/1`
through `--meb-color-bridge-evidence`. The new check verifies that both MEB
properties 460/461 are actually present with the expected 4-byte normalized
`u8x4` storage and that the bridge exposes exactly the D3D9 Type 4/8 candidate
set.

This is an evidence gate, not a Type selection gate: `meb_property_mapping`
must still be `not-proven`. A malformed or explicitly mismatched bridge blocks
the chain, while a coherent ambiguous bridge is recorded as an observed
constraint without changing the unresolved mapping.

## Phase 107: raw MEB property-descriptor provenance

The MEB reader now preserves each vertex-property descriptor as an exact on-disk 12-byte record: descriptor byte offset, the three little-endian DWORD words used by the current parser to construct the property id, and the raw hexadecimal bytes. The same data is exposed by mesh_summary().

For COLOR0/COLOR1 this records the binary origin of properties 460/461 instead of retaining only their semantic names. It is a prerequisite for correlating one actual .meb payload with a runtime declaration instance. It does not resolve D3D9 Type 4 versus Type 8, so the MEB property mapping remains not-proven.

## Phase 108: exact MEB COLOR resource provenance

The real-resource color evidence command now records the exact 12-byte MEB property descriptor and the exact COLOR payload range inside the decoded `.meb`. For property 460/461 it also emits the descriptor words/raw bytes, payload hex/SHA-256, and an explicit check that the decoded color stream is byte-identical to the payload range selected by the parser.

This makes a real `.bff` → `.meb` observation auditable down to byte offsets before attempting any MEB↔D3D9 identity inference. The Type mapping remains non-selective.

## Phase 109: bind real MEB resource provenance to the color bridge

The MEB↔D3D9 color bridge can now consume one or more real BFF-backed COLOR evidence reports. For each supplied 460/461 report it verifies the bff-meb source kind, property descriptor identity, observed descriptor/payload ranges, decoded-stream-to-payload equality, and equality of the raw payload SHA-256 with the COLOR evidence hash.

This is a stronger resource-level property proof, but it still does not select D3D9 Type 4 or Type 8. Unknown resource property IDs are isolated as explicit errors rather than contaminating both color properties.

## Phase 110: exact MEB descriptor triple → D3D9 Type proof

The recovered binary mesh loader `FUN_00859800` consumes a 12-byte element triple as three DWORD values: `[Type ordinal, Usage ordinal, Channel]`. It resolves the first two through the D3D9 type/usage tables and copies the third into the declaration record's `UsageIndex` byte. The source also identifies this routine as `LoadBinaryMeshFromResource` and the surrounding resource code recognizes `.meb` files.

The new `meb_d3d9_descriptor_triple_evidence.py` compares that source-backed triple semantics with the exact descriptor words preserved by the MEB reader. Thus 460 (`[4,6,0]`) and 461 (`[4,6,1]`) can reach `match` only when both descriptors are actually present and exact, with the source loader/triple evidence intact. A wrong Type word yields `mismatch`; a missing descriptor yields `partial`; no decimal-ID-only inference is used.

CLI:

    python shift_importer.py meb-d3d9-descriptor-triple meb.json source-d3d9.json descriptor-triple.json

The resulting Type mapping is now evidence-backed at the descriptor/triple boundary: both properties resolve to D3D9 Type code 4 under the exact-match conditions. Channel 0/1 remains the COLOR0/COLOR1 distinction at the source triple level.

## Linux: сбор MEB-доказательств для 460/461

Для передачи игровых данных для reverse engineering не нужно вручную искать MEB внутри BFF. Запусти из корня репозитория:

    python3 tools/collect_meb_evidence.py "/путь/к/Need for Speed Shift" -o shift_meb_evidence.zip

Утилита рекурсивно сканирует `.bff` и отдельные `.meb`, разбирает все MEB, отбирает ресурсы с properties **460/461** и сохраняет в один ZIP только нужные доказательства: exact 12-byte property descriptors, exact color payloads, byte ranges, SHA-256, mesh/property metadata и provenance исходного BFF/ресурса. Полные игровые архивы в ZIP не копируются.

Дополнительно, если на той же машине есть загруженный Ghidra C dump:

    python3 tools/collect_meb_evidence.py "/путь/к/Need for Speed Shift" --source "/путь/к/SHIFT.exe.c" -o shift_meb_evidence.zip

После выполнения достаточно прислать `shift_meb_evidence.zip` и SHA-256 из последней строки консоли.

## Phase 117–118: BMW vertical slice

The project now contains a runtime D3D9 capture bridge and a deterministic BMW M3 golden-render gate. The runtime bridge keeps static Ghidra evidence separate from runtime-instance evidence; the golden gate prevents resource, primitive or shader-permutation drift from reaching the renderer unnoticed.

The selected BMW M3 E36 LODA asset is recorded in `evidence/bmw_m3_e36_kit00_body_loda.golden.json`. The next render milestone is an actual BMT -> FX -> FXO binding for one of its real primitives, followed by `RenderCommand/1`, GLES compile validation and a reproducible desktop image SHA-256.


## Phase 119: resource identity propagation

The renderer now carries decoded MEB SHA-256 identity through the render-facing packet, and the BMW golden gate fails closed when that identity is missing or mismatched. The next step is the first real BMT -> FX -> FXO -> RenderCommand -> desktop golden image for the selected M3 resource.


## Phase 120: exact BMW render slice

The render pipeline can now extract exactly the selected BMW M3 MEB from a generic `RenderBinding/1` using path + SHA-256 identity, carrying the corresponding `StaticDraw/1` and `RenderCommand/1` forward without reparsing resources. This prepares the first real end-to-end material render.


## Phase 121: exact BMW material slice

The selected M3 resource can now be narrowed to one deterministic material draw before shader execution. This keeps failures local to one real primitive and makes the first BMW image hash attributable to an exact BMT/FX/FXO/render-command chain.


## Phase 122: BMW desktop reference render

A thin `SHIFT.BMWReferenceRender/1` adapter now turns the exact BMW material slice into a deterministic desktop PPM result while preserving the existing RenderCommand contract. This is the final execution bridge before the first real BMW image is recorded.


## Phase 123: shader permutation identity

Shader selections now carry a stable content-derived permutation identity independent of FXO blob offsets. This strengthens the BMW golden path so a `unique` shader selection is tied to a reproducible VS/PS byte pair rather than a heuristic score alone.


## Phase 124: D3D9 shader runtime lifecycle

The runtime evidence bridge now records VS/PS shader object creation and binding in addition to declaration/stream/index state. When both shader stages are available, it derives the same content-based permutation identity used by the offline material linker.


## Phase 125: BMW runtime shader join

The runtime bridge can now join a concrete D3D9 frame to the exact BMW material slice by shader permutation identity and MEB resource identity, then verify the pixel sampler contract. This narrows the remaining gap to constant/declaration parity and the first real shader-reference render.


## Phase 126: BMW runtime parity

The BMW runtime pipeline now has a final parity gate for shader constant registers and the currently evidenced D3D9 declaration subset. It remains fail-closed when the Usage mapping or declaration instance is unavailable.


## Phase 127: runtime shader constants

The runtime capture bridge now records floating-point shader constant writes. The BMW parity gate can compare captured values against `MaterialUniformBinding/1` and make missing values a hard blocker for the final golden path.


## Phase 128: BMW runtime golden gate

The runtime pipeline now has a single fail-closed gate that combines shader identity, exact MEB identity, sampler/constant parity, D3D9 declaration checks and RenderCommand readiness before a golden render is accepted.


## Phase 129: runtime trace integrity

The D3D9 capture pipeline now verifies ordered object lifecycle and complete draw state before a runtime frame can be promoted into the BMW golden path.


## Phase 130: exact BMW runtime draw correlation

The BMW runtime golden path now verifies the exact indexed draw range for the selected primitive, not only the MEB resource and shader state. This closes the submesh-attribution gap for the first real material render.


## Phase 131: BMW vertex-input parity

Runtime D3D9 declaration semantics are now checked against shader `DCL` semantics and the target `VertexLayout/1`. The golden gate can reject a draw when the captured declaration does not carry the expected Type/Usage/UsageIndex for the selected material inputs.


## Phase 132: BMW MEB descriptor parity

The selected BMW M3 golden path now preserves the full eight resource-level `[Type, Usage, Channel]` descriptor triples and checks their raw bytes. Runtime vertex-input parity uses these exact descriptors instead of an independent hardcoded property map.


## Phase 133: runtime Usage bridge

A machine-readable `SHIFT.MEBRuntimeUsageOrdinalBridge/1` now derives D3D9 Usage-byte mappings from exact same-resource declaration evidence instead of hardcoded assumptions. Ambiguous mappings remain blockers, and the bridge report can be passed directly to the BMW golden gate.


## Phase 134: runtime capture schema

The D3D9 capture ingestion path is now versioned and shape-validated before semantic analysis. `validate-d3d9-capture` rejects malformed declarations, shaders, stream bindings, draw ranges and shader-constant vectors before they enter the evidence pipeline.


## Phase 135: RenderCommand constant parity

The final renderer command now has an explicit c-register parity check against the material constant payload. This prevents a successful runtime capture from being paired with a drifted offline uniform upload contract.


## Phase 136: BMW M3 paint contract

The real BMW M3 paint material chain is now represented as a versioned machine-readable contract, including exact D3D9 sampler registers, texture identities, sampler state and specialization flags. It remains separate from runtime-instance evidence.
