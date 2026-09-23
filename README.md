# SHIFT Universal Resource Importer

Этапный reverse-engineering/import tool для Need for Speed: SHIFT. Цель проекта — один универсальный конвейер, который работает с оригинальными BFF и их ресурсами, а не набор ручных конвертеров для каждой машины.

## Уже реализовано

- BFF v3: таблица записей, имена, смещения, типы и целостность диапазонов.
- Native C++ XMem/LZX backend для массовой декомпрессии; включается через `SHIFT_LZX_NATIVE=1`, с pure-Python fallback по умолчанию.
- Type 0: raw.
- Type 1: zlib.
- Type 2: SHIFT/XMem + LZX с сохранением LZX-состояния между блоками.
- Автоматическая классификация по пути, расширению и сигнатуре.
- SHA-256 и dependency hints.
- Content-addressed package (`blobs/<sha256>`).
- Типизированный разбор `Reflection XML`: классы, наследование, типы свойств, вложенные `Fct`-массивы.
- Разбор `BMLY`/`BML`: блоки `HEAD/ELMT/ATTR/COLL/NUMB/BOOL/STRS` и строковый индекс.
- Разбор `BMT`: дерево материала, shader params, числовые/boolean/строковые значения и ссылки на DDS.
- HLSL inventory: includes, techniques, samplers и глобальные параметры.
- Generic XML tree для VHF/CPT/VUD/ENX/SPE/TRD/NEW и других XML-подобных ресурсов.
- DDS metadata.

## Команды

```bash
python shift_importer.py inspect VEHICLES.bff
python shift_importer.py manifest /path/to/Dir/ manifest.json --decode
python shift_importer.py validate /path/to/Dir --report validation.json
python shift_importer.py extract /path/to/Dir extracted/
python shift_importer.py package /path/to/Dir shift_assets/
python shift_importer.py analyze-resource VEHICLES.bff vehicles/ferrari_599/ferrari_599.cdp --output ferrari.json
python shift_importer.py analyze-resource GUI.bff gui/hud/hud_drift_gauge.bmt --output material.json
python shift_importer.py analyze-dir /path/to/Dir format_reports/ --ext .bmt .fx .fxh .meb .csm .xml .lod .vud .cpt
python shift_importer.py convert-meb Alpental.bff grid1_02.mgeo --resource tracks/alpental/grid1_02.meb
python shift_importer.py convert-csm TRACKS.bff nord.cmesh --resource tracks/nordschleife07/physics/nordschleife07.360.csm
python shift_importer.py graph /path/to/bffs graph.json --ext .cpt .vhf .meb .bmt .dds .fx .fxh
python shift_importer.py build-ir /path/to/bffs android_ir/
python draw_packets.py android_ir/../format_reports/resource_analysis.json draw_packets.json
# native XMem/LZX
SHIFT_LZX_NATIVE=1 python shift_importer.py build-ir /path/to/bffs android_ir_native/
```

`analyze-resource` создаёт единый JSON с исходным BFF-entry, SHA-256, категорией, dependency hints и результатом форматного анализа.

## Android intermediate representation

Оригинальный BFF не должен становиться форматом Android runtime. Импортёр сохраняет исходные данные в content-addressed blobs и строит над ними нейтральные представления:

```text
shift_assets/
  blobs/<sha256>
  manifest.json
  path_map.json
  stats.json
  analysis/
    materials/*.json
    reflection/*.json
    bml/*.json
    shaders/*.json
```

На стороне Android планируется читать уже это IR и использовать отдельные native-конвертеры для geometry/scene/physics. То есть `BFF -> Android` выполняется массово по типу ресурса и зависимостям, без hardcode имени автомобиля.

## Статус конвертеров

**Готово/достаточно для IR:** BFF/XMem, DDS metadata, Reflection XML, BML index, BMT material graph, HLSL metadata, MEB geometry, CSM collision geometry, XML scene/data, dependency graph и автоматический `build-ir`.

**Текущий слой:** FXO/D3D9 shader bytecode → нейтральный `SHIFT.ShaderProgram/1` → первый GLSL ES 3.1 backend. Добавлены register/operand decoding, арифметические операции, texture ops, derivatives и базовый structured control flow.\n\n**Следующий слой:** exact sampler-state binding; semantic vertex/pixel linkage; MGEO/VHF transform semantics; затем IMB skeletal geometry/animation, SGB scenegraph и перенос физики с PhysX 2.x на Android-native collision/dynamics.\n\n`draw_packets.py` builds `SHIFT.DrawPacket/1` from `resource_analysis.json`; texture slots are marked `material-order-inferred` until the exact D3D9/BMT sampler mapping is recovered.

`.meb` является компонентом видимой геометрии SHIFT, а `.bmt` содержит материал и связанные shader/texture данные; независимые инструменты моддинга SHIFT подтверждают, что модельные `.meb` и материальные `.bmt` работают совместно. Поэтому следующий этап должен связывать их через VHF/material references, а не конвертировать файлы изолированно.

Полная валидация всех 15 базовых BFF уже прошла для архивов кроме крупного `TRACKS.bff`; проблема там пока только в скорости чистого Python LZX-декодера, а не в обнаруженной ошибке формата. Для production importer следующий шаг — native C/C++ LZX backend.

### BMT -> FX -> FXO material binding

Добавлен универсальный слой `material_linker.py`: он связывает BMT shaderparams с SamplerTexture из исходного HLSL/FX, переносит Min/Mag/Mip/Address/sRGB state и через D3DX9 CTAB восстанавливает фактические sampler registers. Для BMW M3 E36 проверено: diffuseTexture -> diffuseMap/s1, specularTexture -> specularMap/s2, scratchControlTexture -> scratchControlMap/s4; renderer-global environmentMap -> s3 и shadow sampler -> s0.

CTAB reflection теперь сохраняет typed constants и sampler register metadata в `shader_ir.py`. Следующий render-layer шаг — связать этот MaterialBinding с VHF/MEB primitive/material references и восстановить VS/PS pair + vertex semantic interface.


### VHF -> MEB -> BMT render-link stage

Добавлен `render_pipeline.py`, формирующий `SHIFT.RenderBinding/1`: VHF resource nodes связываются с MEB primitives, legacy `.mtx` автоматически разрешается в `.bmt`, VHF parent/matrix hierarchy превращается в world transforms, а BMT связывается с FX source и FXO permutations через `material_linker.py`. На следующем слое останется восстановить VS/PS pair и semantic vertex interface перед загрузкой DrawPacket в Android renderer.


### VS/PS semantic interface

Исправлена карта D3D9 `D3DDECLUSAGE`: `6=TANGENT`, `7=BINORMAL`, `10=COLOR`, `13=SAMPLE`. На реальных BMW M3 E36 FXO это устраняет прежнюю ложную интерпретацию `COLOR0` как `SAMPLE0`.

`shader_interface.py` теперь связывает vertex `oTn` и pixel `vn` по паре `(usage,index)`, а не по номеру регистра, и сопоставляет входы VS с атрибутами MEB. Подтверждённые MEB semantic mappings: `200=POSITION0`, `460=COLOR0`, `220=NORMAL0`, `240=TANGENT0`, `250=BINORMAL0`, `130..134=TEXCOORD0..4`, `310=BLENDWEIGHT0`, `580=BLENDINDICES0`. `230..234` используются как 3-компонентные UVW-каналы и сохраняются как TEXCOORD slots.

На наборе BMW M3 E36 + Cockpit: 1,707 FXO, 10,756 shader programs, 125 уникальных stage+IO signatures. Внутри FXO обнаружено 21,488 VS/PS candidate pairs; 13,909 пар имеют полное semantic-покрытие PS input declarations со стороны VS outputs. Например bodywork permutation связывает PS `TEXCOORD5/0/1` с VS `oT1/oT2/oT3` при разных register numbers — это подтверждает semantic linkage.

Следующий слой: точный vertex stream packing/type (D3DDECLTYPE) поверх этих semantics, затем окончательная VS/PS permutation привязка к BMT specialization flags и runtime `SHIFT.DrawPacket/1`.

### VS/PS semantic interface

Исправлена карта D3D9 `D3DDECLUSAGE`: `6=TANGENT`, `7=BINORMAL`, `10=COLOR`, `13=SAMPLE`. На реальных BMW M3 E36 FXO это устраняет прежнюю ложную интерпретацию `COLOR0` как `SAMPLE0`.

`shader_interface.py` теперь связывает vertex `oTn` и pixel `vn` по паре `(usage,index)`, а не по номеру регистра, и сопоставляет входы VS с атрибутами MEB. Подтверждённые MEB semantic mappings: `200=POSITION0`, `460=COLOR0`, `220=NORMAL0`, `240=TANGENT0`, `250=BINORMAL0`, `130..134=TEXCOORD0..4`, `310=BLENDWEIGHT0`, `580=BLENDINDICES0`. `230..234` используются как 3-компонентные UVW-каналы и сохраняются как TEXCOORD slots.

На наборе BMW M3 E36 + Cockpit: 1,707 FXO, 10,756 shader programs, 125 уникальных stage+IO signatures. Внутри FXO обнаружено 21,488 VS/PS candidate pairs; 13,909 пар имеют полное semantic-покрытие PS input declarations со стороны VS outputs. Например bodywork permutation связывает PS `TEXCOORD5/0/1` с VS `oT1/oT2/oT3` при разных register numbers — это подтверждает semantic linkage.

Следующий слой: точный vertex stream packing/type (D3DDECLTYPE) поверх этих semantics, затем окончательная VS/PS permutation привязка к BMT specialization flags и runtime `SHIFT.DrawPacket/1`.

## Renderer resource manager

`renderer_resources.py` exposes `SHIFT.RenderResources/1`, a content-addressed manifest for DDS resources, sampler states and material texture bindings. Texture identity is based on decoded-content SHA-256 when available; sampler identity is independent so different materials can reuse the same GPU texture with distinct sampling state. Optional compressed-texture capabilities are checked explicitly before a resource is marked GPU-ready.
