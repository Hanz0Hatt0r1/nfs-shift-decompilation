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
