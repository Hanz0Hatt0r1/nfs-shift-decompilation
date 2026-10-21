# Process 2 — v668 D3D9 no-Draw runtime-frontier review

Дата: 2026-10-21. Тип работы: независимый evidence/code review, **без изменений runtime, renderer, Win32 compatibility и P-code**.

## Короткий вердикт

**v668 не показывает ни одного входа в выбранные D3D9 `Draw*` методы и поэтому не доказывает ошибку Process 2 renderer/translation.** Самая близкая проверяемая граница сейчас **до** `IDirect3DDevice9::DrawIndexedPrimitive` handler и его P2 packet callback: либо гостевой путь в данном P-code replay не вызывает `Draw*`, либо выбранное импортное трассирование не охватило фактический путь вызова. Ошибка P2 callback после входа в handler не может ретроспективно удалить запись о входе в метод.

**Рекомендация: не начинать новые изменения D3D9/Vulkan renderer только из-за v668.** Сначала P1 должен показать хотя бы один достоверный `Draw*` import-entry и исход его dispatch. Известная downstream P2 работа — подключение/проверка packet capture и последующая Vulkan draw translation — становится измеримой *после* этой границы; её существование не объясняет отсутствие Draw.

## Полное данное v668 evidence: что установлено, а что нет

Источник: retail PE32 PC SHIFT.exe 1.02, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`; фактическая исполняющая среда — **recompiled guest P-code runtime с загруженным retail PE, НЕ native Windows SHIFT.exe**.

| Метрика | Значение / правильная интерпретация |
| --- | --- |
| host frames requested/rendered | 360 / 360; внешний host-frame цикл, не доказательство игры/меню/гонки |
| status, exit, blocker | `host-frame-loop`, `exit=0`, `blocker=null` |
| P-code dispatches / unique functions | 1,734,402 / 4,728; не число guest draw и не рендер-доказательство |
| main-thread function | `0x00835590`; снимок одного момента, без вывода о причинности |
| waiting workers | 5; не доказательство причины no-Draw |
| validation_errors | 0; не подтверждение Vulkan retail draw |
| Clear requests / submissions | 1,108 / 360 |
| Present requests / submissions | 1,107 / 360; `pending presents=747` |
| rendering flags | `guest_draw_translation=false`, `retail_rendering_proven=false` |
| полный локальный call-trace | SHA-256 `9630914c79a0816f453580f0bc884480df3f2f144cf158e4e735a7887a41cf37`; 5,573 `call-trace-entry` записей |

Вызовы выбирались по **точным именам** `IDirect3D9::CreateDevice` и `IDirect3DDevice9::{DrawPrimitive, DrawIndexedPrimitive, DrawPrimitiveUP, DrawIndexedPrimitiveUP, CreateVertexBuffer, CreateIndexBuffer, CreateTexture, BeginScene, EndScene, Clear, Present, SetTexture, SetVertexDeclaration, SetStreamSource, SetIndices, SetVertexShader, SetPixelShader, SetRenderTarget}`.

**Распределение всех 5,573 записей по выбранным методам:**

| Импорт | Entry records |
| --- | ---: |
| Clear | 1,108 |
| SetRenderTarget | 1,107 |
| BeginScene | 1,107 |
| EndScene | 1,107 |
| Present | 1,107 |
| CreateVertexBuffer | 17 |
| CreateIndexBuffer | 16 |
| CreateTexture | 1 |
| CreateDevice | 1 |
| SetPixelShader | 1 |
| SetVertexShader | 1 |
| **DrawPrimitive / DrawIndexedPrimitive / DrawPrimitiveUP / DrawIndexedPrimitiveUP** | **0 / 0 / 0 / 0** |
| **SetTexture / SetVertexDeclaration / SetStreamSource / SetIndices** | **0 / 0 / 0 / 0** |
| **Итого** | **5,573** |

Это **полный предоставленный локальный trace для выбранных имён**, а не выборка по dispatch counters. Сильный позитивный факт: instrumented import-entry фиксирует scene/clear/present/render-target и часть resource-creation. Отрицательный факт: выбранные `Draw*` и некоторые state-setting импорты отсутствуют **в этой трассе**. Отсутствие записей не является доказательством, что вообще ни в каком другом P-code execution path, hook alias, renderer или native retail исполнении нет draw; и не определяет, почему guest не пришёл в выбранный метод.

Наблюдения `BeginScene`, `EndScene`, `Clear`, `Present` и 360 host submissions **не являются** доказательством успешного guest scene rendering; pending presents и packet/callback/sampler readiness не позволяют приписывать кадрам игровое содержимое.

## Exact source boundary в GitHub

Проверены актуальные GitHub refs **`work/retail-runtime-d3d9-capture`** (P1 PR [#2140](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2140), head при ревью `c22de47d9c633f6a88d6fb0437e3bd2312c8ec4f`) и P2 branches/PR. Основной кодовый файл P1: [`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp); API: `native_runtime/include/shift_recompiled_pcode_module.hpp`.

1. **Образование COM method traps**: в `d3d9_create_device` (приблизительно строки 6186–6240) таблица из 119 методов включает все четыре `Draw*`: `DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`. Каждому созданному guest vtable slot сопоставляется `d3d9.dll!IDirect3DDevice9::<method>` через `allocate_dynamic_import_stub`. Следовательно, наличие имен в vtable **не** означает, что guest их вызвал.
2. **Trace фиксируется до handler**: `dispatch(uint64_t target)` (около строк 1630–1647) при найденном `import_traps` имени немедленно вызывает `record_guest_call_trace(target, name)`, **перед** цепочкой `if (name == ...)` и вызовом API handler. `record_guest_call_trace` (около строк 1319–1345) фильтрует по выбранным import_name/target/caller и имеет `kGuestCallTraceLimit`; есть `guest_call_trace_truncated`. Для выбранного import name, при включённой трассе, покрытии hook и отсутствии усечения событие уже должно существовать прежде любого P2 действия. `SHIFT_TRACE_GUEST_CALL_IMPORTS` задаёт выбранные имена (около строк 879+).
3. **P1 dispatcher реализует именно indexed variant**: около строки 1957 `if (name == "d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive") return d3d9_device_draw_indexed_primitive();`. В этом import switch нет обработчиков для `DrawPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`, хотя vtable slots существуют. Это *потенциальный P1 compatibility gap, только если guest действительно входит в один из них*; v668 не показывает ни один такой вход.
4. **P1 handler сначала проверяет guest state**: `d3d9_device_draw_indexed_primitive()` (около строк 7015–7299) читает семь stack arguments, проверяет `guest_device`, `scene_active`, `primitive_type ∈ [2..6]`, bound index buffer, затем `draw_indexed_primitive != nullptr` (иначе возвращает `D3DERR_NOTAVAILABLE`). Только после этих guard checks он собирает `RecompiledGuestD3d9DrawIndexedPrimitivePacket`, проверяет остальные resource/state bindings и **синхронно** вызывает `guest_d3d9_adapter_info.draw_indexed_primitive(...)` (около строк 7287–7290); callback false также ведёт к `D3DERR_NOTAVAILABLE`. **Любой отказ этих guard или downstream callback происходит ПОСЛЕ import-entry**. Поэтому **не способен объяснить отсутствие `DrawIndexedPrimitive` entry в v668**.
5. **P2 capture wrapper существует, но работает post-callback**: `native_vulkan/src/d3d9_packet_capture_adapter.cpp` (P2 PR [#2143](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143)): `install()` назначает `draw_indexed_primitive_callback` (приблизительно строка 409); callback (около строк 529–535) вызывает `capture_draw(packet, error)`, затем `forward_draw`. Это сериализация уже сформированного packet. DXT3 support flag/cpu texture conversion из [P2 PR #2144](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2144) не образуют guest `Draw*` вызовов.
6. **Проверенная текущая wiring граница**: `native_runtime/src/shift_runtime.cpp::Runtime::recompiled_d3d9_adapter_info()` (около строк 2143–2245) назначает create/buffer/clear/present callback, но не default live `draw_indexed_primitive` callback. При наличии `SHIFT_D3D9_PACKET_CAPTURE_DIR` устанавливается P2 `D3d9PacketCaptureAdapter::install(adapter_info, error)`, создающий capture draw callback; если переменная отсутствует, callback остаётся null. Даже при включённом wrapper `forward_draw` возвращает true при пустом downstream draw callback (P2 файл, строки 941–943) — **capture callback/dispatch не равен Vulkan `vkQueueSubmit` draw**. Это **реальный латентный P2 live-upload/draw consumer/integration gap**, но он проявился бы лишь после guest DrawIndexedPrimitive entry и потому **не является установленной причиной v668 no-Draw**. В самом v668 evidence значение `SHIFT_D3D9_PACKET_CAPTURE_DIR` не сообщено; не утверждаем, что wrapper был установлен.

Итог на уровне причинной цепочки:

```text
P-code guest call through IDirect3DDevice9 Draw* vtable slot
     -> import_traps match
     -> selected call-trace-entry emitted                 [v668: НЕТ]
     -> P1 indexed-only handler and guest state checks    [v668: не достигнут]
     -> RecompiledGuestD3d9DrawIndexedPrimitivePacket
     -> P2 draw_indexed_primitive capture callback        [v668: не достигнут]
     -> optional downstream Vulkan draw submission        [v668: не доказан]
```

## Что является гипотезой, а не диагнозом

- **Guest не дошёл до draw-содержащей ветки** за 360 host frames (включая возможные UI/session/scheduler/worker dependencies) — совместимо с данными, но конкретную ошибку scheduler, lock, scene-state или shader code v668 **не доказывает**. `main_thread_current_function=0x00835590` и `worker_waiting_count=5` являются только snapshot.
- **Trace coverage/alias**: выбранные имена могли не соответствовать фактическому вызванному path/stub; фильтр import_name может не увидеть call, не проходящий через тот `import_traps` маршрут. В самом источнике есть флаг `guest_call_trace_truncated`; supplied evidence не приводит его значение. Поэтому формулировка no-Draw ограничивается *5,573 selected call-trace-entry records*, а не всеми потенциальными вызовами за пределами этого механизма.
- **Отсутствие bound index buffer, invalid scene или null callback** могло бы сделать DIP неуспешным **после DrawIndexedPrimitive entry**, но **не может убрать его entry**. Эти состояния не являются объяснением данного нуля.
- **Несовместимость Vulkan pipeline/texture/DXT3** также наступила бы после получения draw packet; нет доказанной failed translation, failed upload, SPIR-V compile, descriptor binding или `vkQueueSubmit` для retail draw.
- Отсутствие `SetTexture`, `SetVertexDeclaration`, `SetStreamSource`, `SetIndices` в selected records согласуется с ранней фазой рендера, но из него одного нельзя доказать отсутствие текущих bindings или причину ветвления.

## Минимальный следующий эксперимент и распределение ответственности

**Следующее действие (P1 — trace, без renderer edits):** на сопоставимой P-code replay конфигурации подтвердить, что выбранные exact импортные имена `d3d9.dll!IDirect3DDevice9::{DrawPrimitive,DrawIndexedPrimitive,DrawPrimitiveUP,DrawIndexedPrimitiveUP}` соответствуют созданным `IDirect3DDevice9` vtable stub targets, и записать `guest_call_trace_truncated=false` вместе с одним из следующих минимальных исходов:

1. **Есть первый `DrawIndexedPrimitive` call-trace-entry**: сохранить `import_name`, import stub/target, `caller`, `thread_id`, `dispatch_count`, `esp_entry`, семь DWORD arguments (device + 6 DIP args), `scene_active`, index buffer binding; затем один бит/поле `P1_handler_entered`, `callback_invoked`, `HRESULT`/reject reason. Если отказ раньше callback — P1 D3D9 guest compatibility task. Если callback вызван, но не сериализован/сабмичен — **конкретная P2 integration/translation task**, дополняем packet identity+resources и native Vulkan validation.
2. **Есть первый другой `Draw*` entry**: сохранить имя и args, HRESULT/unhandled-import failure. Это в первую очередь P1 задача реализации/маршрутизации соответствующего D3D9 handler (сейчас есть только indexed handler), а не недостаток Vulkan packet builder.
3. **Нет `Draw*` entry при доказанном покрытии traps и отсутствии усечения**: frontier остаётся upstream P1 guest execution/control flow; минимальный следующий trace — один ближайший guest callsite/ветка, которая должна привести к Draw, и её predicate/branch evidence. Не добавлять новые Vulkan способы draw наугад.

**P2 готовая точка handoff:** после позитивного **реального** P1 DIP packet (с destination P2 callback) проверить callback admission, exact shader/stream/IB/texture/sampler/surface state, DXT3/DDS byte provenance если он используется, SVTP/Vulkan bundle и фактическую native submission/validation. Это минимальная новая P2 задача с проверяемым acceptance criterion: packet received → capture/bundle accepted → `vkQueueSubmit` draw → GPU validation outcome. Пока такого event нет, **новых renderer изменений по v668 не рекомендовано**.

## Ограничения и audit trail

- Одна конфигурация recompiled guest P-code, **360 host frames**, ограниченный импортный trace; не native Windows SHIFT.exe.
- Позитивные значения host frames, `exit=0`, `validation_errors=0`, число dispatches, Clear/Present callbacks и host submissions **не доказывают запуск игрового меню, гонки, gameplay или retail image rendering**.
- Нет raw локального runtime log/file access в этом GitHub-only review; агрегаты и SHA-256 v668 получены из полного evidence, предоставленного заказчиком. Нет заявления, что raw log перечитан из GitHub.
- Код прочитан в GitHub, но его версия не доказана бит-в-бит тождественной исполнявшейся v668 сборке. Поэтому source-based control-flow conclusion ограничен проверенным PR head.
- Исполняемый код не изменён. Данный отчёт — единственный новый файл этой задачи.

### GitHub refs

- P1 source [`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp), [header](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/include/shift_recompiled_pcode_module.hpp), [wiring](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/shift_runtime.cpp).
- P2 [packet adapter](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp); [PR #2143](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143); [PR #2144](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2144).
