# Need for Speed: SHIFT — Decompilation & Resource IR

Инструментальный проект для поэтапной реконструкции форматов, зависимостей и runtime-границ **Need for Speed: SHIFT** с прицелом на воспроизводимый Android renderer.

> **Текущий статус:** mainline развивается через **phase 100** — source-backed D3D9 declaration chain теперь умеет включать проверку фактического declaration instance. RenderCommand, VS→PS reference, skinning, external samplers, cubemap decode и machine-readable declaration evidence образуют единый исследовательский конвейер.

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
