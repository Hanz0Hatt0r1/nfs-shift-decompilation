# Process 2 — v743 retail no-Draw frontier: import-entry против packet-capture boundary

**Дата:** 2026-10-22. **Статус:** source/evidence review; **без изменений P1 runtime, renderer или guest**, без PR.  
**Исходный PE:** retail SHIFT.exe PC 1.02 SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Метод:** сопоставление сведений v743, предоставленных пользователем, с ранее сохранёнными отчётами и фактическим кодом GitHub; повторный поиск DIP sites, декомпиляция и повторный replay **не выполнялись**. Упомянутая пользователем capture-backend ревизия `f4147f33` не была в этом ревью независимо извлечена как git-ref: вывод о точном билде опирается на предоставленную атрибуцию, а семантика проверена по доступным файлам `work/retail-runtime-d3d9-capture` и Process 2 capture branch.

## Итог

**`guest_draw_translation=false` — в просмотренной P2 renderer implementation постоянный литерал JSON, не счётчик и не результат проверки входящих Draw/packet.** По одному этому полю нельзя выбрать между «retail не вызвал DIP», «вошёл в import-handler, но не прошёл guard checks», «handler передал packet capture adapter, но нет Vulkan draw translation». Более того, в `Runtime::record(..., guest_d3d9_frame, ...)` ветка guest D3D9 frame намеренно не испускает `vkCmdDrawIndexed`: там комментарий `Guest draw calls are not translated yet; present the queued clear.`

**v743 подтверждает работающий P-code host-frame-loop с D3D9 CreateDevice/Clear/Present, но не даёт сам по себе доказательства ни входа в гостевой DrawIndexedPrimitive, ни его отсутствия.** Для разграничения нужен один прицельный import-entry trace **перед** P1 guard checks с return address и семью raw DWORD аргументами; в том же прогоне проверяется существующий capture output. Это один следующий шаг, описанный в конце.

## 1. Факты v743, предоставленные Process 1

| Показатель | v743 и доказательная граница |
|---|---|
| Исполняемая программа | именно retail `SHIFT.exe` через recompiled P-code runtime; не нативный Windows/Direct3D9 процесс |
| Проверка входа | Up press/release отправлены guest window `0x01000000` |
| Window message path | `GetMessageW → TranslateMessage → DispatchMessageW → WndProc 0x0040D040`; для `WM_KEYDOWN=0x0100`, `WM_KEYUP=0x0101`, `VK_UP=0x26` выполняется `DefWindowProcW` и доказанная P1 нулевая default-ветвь |
| Финальный статус | `host-frame-loop`, `blocker=null`, exit `0`, validation errors `0` |
| Host/threads | 360 rendered host frames; snapshot main guest thread function `0x0082FAF0`; 4 worker threads waiting |
| Device | retail `CreateDevice` attempt и успешный callback; HRESULT `0x00000000` |
| D3D9 requests | 1129 `Clear`, 1127 `Present` |
| Vulkan host submissions | 360 `Clear`, 360 `Present` |
| Other reported fields | `guest_draw_translation=false`, `material_draws=0`, `world_transform_draws=0`, `affine_world_transform_draws=0` |

Сравнение с v742 дано пользователем как «исполнено больше retail-кода; v743 — новая host-frame-loop точка». Мы не располагаем исходными per-call/Draw-event trace v742/v743 для подтверждения более узкой причинной связи. Dispatch/function counts — **телеметрия, не доказательство вызова Draw**. Возвращение нуля из `DefWindowProcW` означает обработку сообщений по наблюдавшейся default-ветви, **не** доказательство изменения game/input state. `0x0082FAF0` — текущая функция одного snapshot, не установленная draw-ветка.

## 2. Что действительно означает поле guest_draw_translation=false: проверка P2 source

На `work/retail-runtime-d3d9-capture`, файл [native_runtime/src/shift_runtime.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/shift_runtime.cpp):

- **Строка 5440:** генерация JSON всегда пишет `<< ", \"guest_draw_translation\": false},\n"`. Условия, draw-count или packet-count в выражении отсутствуют; это **не результат диагностики**.
- **Строки 4009–4012:** `if (guest_d3d9_frame) { /* Guest draw calls are not translated yet; present the queued clear. */ } else if (material_mode) { ... }`. `vkCmdDrawIndexed`, видимый в material path (примерно 4037), не выполняется в guest D3D9 frame path.
- **Строки 4584–4589:** `material_draws` печатается из `material_geometry.size()`; `world_transform_draws` и `affine_world_transform_draws` считаются при обходе `material_geometry`, а не из retail `RecompiledGuestD3d9DrawIndexedPrimitivePacket`. Их нули не являются значением `guest DIP call count`.
- **Строки 2152–2155, 4104–4128, 5430–5440:** Clear/Present requests и host submissions — отдельные счётчики/путь; `vkQueueSubmit` clear/present не доказывает ни `DrawIndexedPrimitive` import-entry, ни GPU render по guest packet.
- **Строки 2188–2284:** `Runtime::recompiled_d3d9_adapter_info()` задаёт callbacks create-device, textures, vertex/index buffers, clear, present. **Прямого default live draw callback нет.** Если `SHIFT_D3D9_PACKET_CAPTURE_DIR` задан, `D3d9PacketCaptureAdapter::install(adapter_info, error)` устанавливает capture wrapper, включая draw callback; это не Vulkan draw consumer.

Проверенный P2 [native_vulkan/src/d3d9_packet_capture_adapter.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp):

- `install`, примерно строки 380–409: запоминает `downstream_ = adapter`, включает managed DXT3/DXT5 capture и заменяет `adapter.draw_indexed_primitive` на `draw_indexed_primitive_callback`.
- `draw_indexed_primitive_callback`, строки 528–535: при не достигнутом лимите вызывает `capture_draw(packet,error)`; при ошибке возвращает `false`; далее `forward_draw(packet,error)`.
- `forward_draw`, строки 940–943: `if (!downstream_.draw_indexed_primitive) return true;`. Поэтому packet может **успешно захватываться и успешно завершить D3D9 callback**, но **не передаваться в Vulkan draw path**. Пустой downstream — не «packet был отброшен до capture»; это текущая отсутствие live consumer после capture.
- `capture_draw` формирует snapshot для packet при подходящем `version`, VB/IB/textures и других проверках. Если callback вызван, но snapshot не создан, надо различать P1 guard reject, capture validation reject, draw limit, ошибки I/O и неверный путь директории. Отсутствие файла само по себе не показывает, что retail method не вызывался.

**Вердикт по вопросу A/B:** `guest_draw_translation=false` означает только «перевод guest draw в native renderer не реализован/не включён по текущему guest-frame пути и флаг в отчёте записан как false». Он **не кодирует** ни «retail draw call не было», ни «bridge получил и отверг packet». Эти случаи до отдельного event-log неразличимы.

## 3. Точная последовательность P1 → P2 и возможные точки остановки

Рассмотрен [native_runtime/src/recompiled_pcode_module.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp), blob `970c5ac90313e63dc52c781a86598c2a0b3a1ce6` на момент ревью:

1. `dispatch(uint64_t target)` **строки 2049–2064** ищет `import_id_traps` / `import_traps`. При match имени импортной функции вызывает `record_guest_call_trace(target,name)` **до** handler. Следовательно, callback/P2 renderer после handler не способен «стереть» уже собранный import-entry.
2. `dispatch` **2457–2458** маршрутизирует `d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive` в `d3d9_device_draw_indexed_primitive()`. Этот P1 handler определён примерно **7659–7942**.
3. `d3d9_device_draw_indexed_primitive()`, **7662–7666**, читает семь DWORD в порядке `device (this), primitive_type, base_vertex_index, min_vertex_index, num_vertices, start_index, primitive_count`. `read_stack_argument(i)`, **3786–3799**, читает `ESP+4+i*4`; `[ESP]` — guest return address.
4. Ещё **до** packet/P2 callback, **7667–7684**: проверки device, `scene_active`, `primitive_type` (2…6), bound index buffer, установленного draw callback; дальше проверяются ресурсы, shaders, locked buffers и mip data. Возможны возвраты `D3DERR_INVALIDCALL`/`D3DERR_NOTAVAILABLE` до P2 вызова.
5. При успешной сборке `RecompiledGuestD3d9DrawIndexedPrimitivePacket` проходит вызов `guest_d3d9_adapter_info.draw_indexed_primitive(...)` **7931–7937**. При false возвращается `D3DERR_NOTAVAILABLE`, при success увеличивается `indexed_draw_count` и возвращается HRESULT 0 (**7939–7941**).
6. Путь packet adapter: `capture_draw` → `forward_draw` (опциональный downstream). Ни тот, ни другой не означает, что P2 emitted `vkCmdDrawIndexed` в guest frame.

Поэтому логически существует **как минимум три**, а не две, диагностические категории:

| Доказательство | Корректный вывод |
|---|---|
| В правильно покрытом bounded run **нет** DIP import-entry, trace enabled, **не truncated** | Нет DIP-входа **через покрытый P1 import trap** в этом прогоне. Исключение alias/untrapped пути требует отдельного доказательства. |
| DIP import-entry есть, но нет принятого packet/capture | Guest действительно вызвал DIP; блокировка **между import-entry и snapshot**: guard/state, callback отсутствует или отклонение capture. По одному нулю `guest_draw_translation` различить их нельзя. |
| DIP import-entry + принятый capture packet, но host guest-frame без `vkCmdDrawIndexed` | **P1→P2 packet delivery доказана**, отсутствие native guest draw — подтверждённый downstream renderer-integration gap. Нулевой `guest_draw_translation` будет таким же, как в первых двух случаях. |

## 4. Совместимость с сохранёнными process-reports и очередь

Сохранённые источники в этой же ветке:

- [Process 2 — v668 no-draw frontier](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-21-process2-v668-no-draw-frontier.md): в выбранном bounded P1 import-trace были CreateDevice/CreateTexture, scene, Clear/Present, но **0** выбранных четырёх `Draw*` import-entry. Это утверждение **об v668 и покрытии его фильтра**, а не переносимый факт о v743.
- [Process 2 — v719 boundary](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process2-dxt3-v719-boundary.md): v719 завершился на managed-DXT3 texture boundary; DXT3 capture capability в P2 не доказывала успешного retail draw. В v743 CreateDevice, Clear, Present и loop достигнуты; это новый milestone, но без draw import-trace категория Draw остаётся неподтверждённой.
- [Process 2 — полный retail DIP static analysis](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process2-retail-drawindexedprimitive.md): 32 статических косвенных кандидата. `0x0083BBC6` находится в `0x0083BB40–0x0083BBFF`, ожидаемый фиксированный набор `(Type=6, Base=0, Min=0, NumVertices=4, StartIndex=0, PrimCount=2)`; `0x0084FD98` — forwarding из `0x0084FD60–0x0084FD9F` с шестью аргументами из стековых параметров вызывающего кода. **Статические адреса не являются runtime reachability.**
- [Process 1 — display queue producer/consumer](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-21-process1-display-queue-producer.md): v692 фиксировал реальную `0x00835590 → 0x00831380` обработку и `*EDX=0x3f800000`, затем `0x005E1D50` с `EAX=0` и локальное пропускание `0x008352F0` на измеренном пути; no selected Draw*. Не переносить per-run count/ветви на v743.
- [Process 1 — 0x008353E0](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process1-function-008353e0.md): `0x00835590` связан с очередью на `renderer+0x1E80`; `0x008352F0` с аргументами `ECX=renderer, EDX=5, [EBP+8]=item` удаляет запись/регистрацию типа 5 через список `renderer+0x1F20`. **Это не идентифицированный DrawIndexedPrimitive путь**. У разных прогонов (например v692 и v734) различались локальные условия; их смешение недопустимо.

**Новая v743 диспетчеризация клавиш в default WndProc не доказывает**, что очередь `0x00835590` достигла кандидата `0x0083BBC6` или forwarding `0x0084FD98`. Гипотеза «queue callback → DIP» остаётся неустановленной до trace с общими `return_address/caller/stack`, показывающей фактическую цепочку. Снимок main thread `0x0082FAF0` и число worker threads эту цепочку не устанавливают.

## 5. Ровно один следующий шаг Process 2

**Один повторяемый диагностический прогон v743-equivalent: единственная точка инструментирования — P1 `dispatch()` при matched import `d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive` (`record_guest_call_trace` на строках 2052–2064, _до_ вызова `d3d9_device_draw_indexed_primitive`); оставить уже рабочий DXT3 packet capture включённым.** Изменение P1 исходников для этого шага **не требуется**, механизм существует.

Задать переменные для того же retail SHA и того же Up press/release сценария (команду запуска самого P1 harness взять из v743; здесь её нет, не выдумывать):

```sh
SHIFT_TRACE_GUEST_CALL_IMPORTS='d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive'
SHIFT_TRACE_GUEST_CALL_STACK_SLOTS='0,4,8,12,16,20,24,28'
SHIFT_D3D9_PACKET_CAPTURE_DIR='<fresh-existing-writeable-dir>'
```

Обозначения `SHIFT_TRACE_GUEST_CALL_IMPORTS`, `SHIFT_TRACE_GUEST_CALL_STACK_SLOTS` проверены по P1 `recompiled_pcode_module.cpp` **879–885, 948–949, 1524–1577, 1717–1719**; JSON поля `guest_call_trace`/`guest_call_trace_truncated` в P2 `shift_runtime.cpp` **422–520, 5450–5490**. **Важно:** значения `stack_slots` — offset от `ESP_entry`, не offset от `EBP`.

Ожидаемая атомарная запись `guest_call_trace` для каждого import-entry: `import_name`, `function` (dynamic import stub), `caller` (guest function), `thread_id`, `return_address`, `esp_entry`, `stack_slots` с восемью читаемыми DWORD (`[ESP+0]` return address, `[ESP+4]` device, `[ESP+8]` type, `[ESP+0xC]` signed base vertex, `[ESP+0x10]` min vertex, `[ESP+0x14]` vertex count, `[ESP+0x18]` start index, `[ESP+0x1C]` primitive count), `eax_return`/`completed`, `dispatch_count` только как идентификатор события. Проверить `guest_call_trace_enabled=true`, `guest_call_trace_truncated=false`, совпадение фильтра и границы 360 кадров. Положительный event сопоставить по времени/identity с `SHIFT_D3D9_PACKET_CAPTURE_DIR`, `draw_*/capture.jsonl` и ресурсными snapshot; только наличие принятого capture event доказывает переданный P2 packet.

**Приоритетный адресный discriminator:** `return_address==0x0083BBC8` соответствует `call edx` в `0x0083BBC6`, `return_address==0x0084FD9A` соответствует `call eax` в `0x0084FD98` (адрес _после_ двухбайтовой инструкции). Для других адресов — восстановить точный предшествующий CALL; не приписывать вызов этим двум кандидатам без совпадения адресов. `caller` — обычно **адрес содержащей функции**, не точный instruction EIP. При наличии event, но отсутствии capture: это не «retail Draw отсутствовал», а отдельная граница между P1 guards и P2 callback. При отсутствии event с полноценным покрытием/no truncation — зафиксировать bounded negative для этого import trap, **не** объявлять произвольные guest Draw* невозможными.

**Результат одного шага:** либо конкретный DIP import-entry с точным guest return address и шестью параметрами, с независимой проверкой принятого packet в capture; либо документированное отсутствие покрытого DIP import-entry в повторённом окне. Для связи с `0x00835590/0x008352F0` дополнительно нужна активная guest call ancestry; без неё эта связь не доказана. **Не вводить искусственный draw, не менять state/default-input ветвь, не добавлять новую реализацию Vulkan из одних host counters.**

## Контроль источников и ограничений

- P1 source: [native_runtime/src/recompiled_pcode_module.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp) (прочитан; blob `970c5ac90313e63dc52c781a86598c2a0b3a1ce6`).
- P2/native Vulkan host: [native_runtime/src/shift_runtime.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/shift_runtime.cpp) (прочитан; blob `4b4f7db5e3172d46bec809197c70232d8f4963c8`).
- Capture wrapper: [native_vulkan/src/d3d9_packet_capture_adapter.cpp](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp), в том числе DXT3 capability; семантика callback/forward проверена также по P1 базовому файлу.
- Технические выводы относятся к проверенному snapshot источников, не гарантируют byte-for-byte идентичность конкретной пользовательской P1/P2 сборки v743 (`f4147f33`).
- **Ни запись call-trace, ни успешный packet capture v743 не предоставлены.** Вывод остаётся строго ограниченным: v743 host loop прошёл, а guest-DIP entry и packet delivery не установлены.

---

## Дополнение Process 2 — v747/v748: проверка обхода draw ingress

**Дата:** 2026-10-22. **Основание:** новые bounded-наблюдения Process 1, предоставленные пользователем, и повторная проверка GitHub-кода; runtime/renderer не менялись, статические DIP sites повторно не искались.

**v747-equivalent:** тот же retail PE SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`; 360 host frames; точный фильтр `SHIFT_TRACE_GUEST_CALL_IMPORTS=d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive`, stack slots `ESP+0..0x1c`; `guest_call_trace_enabled=true`, `guest_call_trace_truncated=false`, `events=[]`; capture directory пуст. **В этом окне отсутствует зарегистрированный DIP import-entry через выбранный P1 import trap.** Отсутствие любого graphics-вызова за пределами этого trap не доказано.

**v748:** отдельные 120 frames; выбраны `DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`, trace not truncated; capture directory пуст. Точный JSON ещё разбирается Process 1. **Пока нельзя утверждать, что все четыре import-entry имеют ноль событий** — требуется проверить точные entries и фильтры в готовом JSON. Нулевой capture это не заменяет.

### Может ли typed retail guest draw packet обойти четыре imports/adapter callback?

**В проверенной P1→P2 wiring — нет.** В [P1 модуле](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp), проверенный blob `e665872a9373f22aaa48353963761e52390f2732`, найдена ровно одна сборка `RecompiledGuestD3d9DrawIndexedPrimitivePacket` в `d3d9_device_draw_indexed_primitive()` (примерно 7714–7996) и ровно один вызов `guest_d3d9_adapter_info.draw_indexed_primitive(...)` (около 7986). В `dispatch()` (около 2075–2086) import-match вызывает `record_guest_call_trace` до API handler. Device vtable перечисляет все четыре метода, но **наличие vtable stub не равно вызову; typed packet builder реализован в DIP handler**, не в остальных трёх.

В [live Vulkan runtime](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/shift_runtime.cpp) (blob `b5b07dab90cca6ca023945b80c5386a8db8a544c`) `recompiled_d3d9_adapter_info()` устанавливает D3D9 packet capture только при непустом `SHIFT_D3D9_PACKET_CAPTURE_DIR`; иных live guest `draw_indexed_primitive` registrations нет. В [P2 capture adapter](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp) (blob `bb2d31abea1c48fe8220246fa8cb0000eed961ce`) `install()` устанавливает `adapter.draw_indexed_primitive = &draw_indexed_primitive_callback` (409), а `draw_indexed_primitive_callback` (529–535) — **единственная штатная точка входа typed packet в этот capture adapter**; затем `capture_draw` и `forward_draw`. `forward_draw` (941–943) возвращает success при null downstream draw callback, что не означает guest Vulkan draw. В guest frame branch runtime существует только clear/present, а `guest_draw_translation=false` в JSON является литералом. P2 ресурсная ветка `work/process2-dxt3-vulkan-resource-20261021` имеет тот же renderer blob `043ab2d7edb37ad756fbed57368e598961c15645`, что и `main`, и не показывает дополнительного live guest ingress.

**Оговорка:** отдельный P2 **offline replay** (например, PR #2139) может исполнять Vulkan bundle из сохранённого внешнего capture без текущего P-code import-entry. Это **не** доставка typed packet из v747/v748 в runtime capture/renderer в обход перечисленных callbacks. Синтетические fixture packets также не устанавливают runtime reachability. Вывод «нет обхода» ограничен проверенной wiring, не является математическим доказательством отсутствия неизвестного hook/alias.

**Текущая подтверждённая граница:** в v747 upstream **до P2 draw ingress** — ни одного зарегистрированного DIP import entry при выбранном фильтре без усечения. Пустая capture directory совместима с этим, но не доказывает отсутствие неохваченного stub или другой guest ветки. Связь очереди `0x00835590/0x008352F0` с `0x0083BBC6`/`0x0084FD98` динамически не установлена; host frames/dispatch counts не доказывают её.

### Ровно один следующий P2 instrumentation target — только после доказанного P1 import-entry

**`D3d9PacketCaptureAdapter::draw_indexed_primitive_callback`** ([код](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp), строки 529–535). Логировать **на входе до draw-limit и `capture_draw`** один event: `packet.guest_device`, `packet.sequence`, `primitive_type`, `base_vertex_index`, `min_vertex_index`, `num_vertices`, `start_index`, `primitive_count`; зафиксировать `capture_draw` attempted/result, `forward_draw` attempted/result и `error`, коррелировать с P1 import `return_address/callsite` и thread. Это разделяет (1) P1 handler не доставил packet, (2) P2 получил и отверг при capture, (3) P2 принял, но live Vulkan draw не реализован. **До положительного P1 import-entry P2 instrumentation не начинать.** Никаких guest-state изменений, искусственных draw или нового PR.
