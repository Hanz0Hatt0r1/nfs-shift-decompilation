# Process 2 — v763: managed-DXT3 startup gate закрыт; retail draw ingress ещё не доказан

Дата: 2026-10-22. Тип: evidence-backed review PR #2145 / PR #2144 и bounded v763. **Решение: (2) — новых обоснованных P2 renderer changes до первого retail guest Draw не вносить; зафиксировать минимальный входной контракт от P1.** Это не утверждение, что вся работа над renderer закончена. P1-owned код не менялся. Повторный static DIP/no-bypass поиск и новый retail replay не проводились.

## 1. Доказательства и границы v763

Сообщённый Process 1 integration run:
- Retail: оригинальный PC 1.02 PE32 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Интегрированный runtime binary SHA-256 `545c9eadd76f7183b64e8a8dd12a51a88c480b31f857b76ed01af170626f1f3f`, P1 checkout + PR #2145; те же game-data и cumulative v659 P-code manifest.
- `SHIFT_D3D9_PACKET_CAPTURE_DIR` явно **unset**. Граница 360 host frames: `host-frame-loop`, exit `0`, `blocker=null`, `validation_errors=0`.
- `unsupported D3D9 managed texture description` **не повторился**.
- Выбраны четыре Draw/DrawUP import names и target-фильтр `0x004692E0, 0x0045C000, 0x004052B0, 0x004049D0, 0x0045B530`. Guest call trace не усечён, `events=[]`.
- `guest_draw_translation=false`, `retail_rendering_proven=false`; файлов packet capture нет.

Эти факты являются **предоставленными P1 runtime observations**, не повторно измеренными здесь. При полном указанном покрытии отрицательная трасса означает **ни одного выбранного import/target event в этом bounded прогоне**. Это не доказательство отсутствия всех мыслимых guest graphics вызовов. Отсутствие packet capture файлов при **unset** capture variable не является дополнительным самостоятельным отрицательным свидетельством: wrapper не устанавливается. 360 host frames, число P-code dispatches и Vulkan Clear/Present не являются доказательством retail menu/gameplay/draw.

## 2. PR #2145: только CPU-backed managed-DXT3 capability gate

[PR #2145 — Process 2: enable CPU-backed managed DXT3 in live runtime without capture](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2145):
- Head: `de0737734af2138bf9852436c276e64091aeabee`, base: P1 branch `89a019991f53885d85f85ae572b34bfd18d6ef77`; на момент проверки PR **open/unmerged**.
- [`native_runtime/src/shift_runtime.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/de0737734af2138bf9852436c276e64091aeabee/native_runtime/src/shift_runtime.cpp): `Runtime::recompiled_d3d9_adapter_info()` вызывает `enable_guest_managed_dxt3_capability(adapter_info)` **до** проверки `SHIFT_D3D9_PACKET_CAPTURE_DIR`.
- [`shift_vulkan_d3d9_managed_texture_capability.hpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/de0737734af2138bf9852436c276e64091aeabee/native_vulkan/include/shift_vulkan_d3d9_managed_texture_capability.hpp): функция устанавливает **только** `adapter.supports_dxt3_texture=true`. Нет Vulkan BC2 image creation/upload, guest shader binding, draw command, изменения capture callback или DXT5 live claim.
- В P1 [`recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/89a019991f53885d85f85ae572b34bfd18d6ef77/native_runtime/src/recompiled_pcode_module.cpp) managed texture ветвь `usage=0` / `pool=D3DPOOL_MANAGED` проверяет capability и хранит compressed mip bytes в guest RAM; live `create_texture` backend callback используется отдельно для default-pool render target texture. Следовательно, принятие guest-managed DXT3 **не подразумевает поддержку native Vulkan DXT3 sampling**.
- [P2 CTest](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39702353712) `shift_vulkan_d3d9_live_managed_dxt3_capability`: **1/1 passed**. [Linux Vulkan CI](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39702353656): **success**, retail-startup-regression **skipped**. Успех **именно интегрированного без-capture startup** дополнительно предоставлен новым v763 runtime результатом, не из CI.
- **Вывод:** v763 подтверждает снятие именно прежнего managed DXT3 CreateTexture startup gate без capture. Не показывает DXT3 texture sampling, реальный принятый draw packet, Vulkan draw или gameplay.

## 3. PR #2144: независимая synthetic texture-consumer проверка уже выполнена

[PR #2144 — correct DXT3 BC2 decode and verify Vulkan RGBA8 packet resource path](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2144): head `3e6b6eb4a3d9c32dddd51a6b998ac4f0ed0e8dbe`, base `f4be2e7ccff2fa2c578c86581ef1ea6702b0eda7`; на момент проверки **open/unmerged**, не часть автоматически доказанной интеграции v763.

- [`src/render/texture_reference.py`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/3e6b6eb4a3d9c32dddd51a6b998ac4f0ed0e8dbe/src/render/texture_reference.py) исправляет BC2/DXT3 и BC3/DXT5 цветовую палитру: всегда four-color interpolation, включая `color0 <= color1`; DXT1 three-color/transparent semantics сохраняются.
- [`tests/test_texture_reference.py`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/3e6b6eb4a3d9c32dddd51a6b998ac4f0ed0e8dbe/tests/test_texture_reference.py) проверяет BC2/BC3 интерполяцию, alpha и DXT1 transparent mode.
- [`tests/test_vulkan_d3d9_capture_bundle.py`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/3e6b6eb4a3d9c32dddd51a6b998ac4f0ed0e8dbe/tests/test_vulkan_d3d9_capture_bundle.py) проверяет **синтетический** retail-shaped DXT3 `512x512`, block pitch `2048`, 262144 compressed bytes, один mip, DDS→RGBA8/SVTP/1 и fail-closed truncation. Это воспроизводит *размеры*, не retail texel bytes и не факт D3D9 binding.
- GitHub checks на head: `python`, `native`, `vulkan-smoke` **success**; retail-startup-regression **skipped**. Эти результаты подтверждают synthetic/offline workflow, но **не** реальный retail Vulkan submit, parity с игрой, ни доступность исходной DXT3 текстуры v763.

## 4. Что известно о текущем P2 runtime renderer и зачем нужна новая входная информация

В [`native_runtime/src/shift_runtime.cpp` из PR #2145](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/de0737734af2138bf9852436c276e64091aeabee/native_runtime/src/shift_runtime.cpp) `Runtime::record()` при `guest_d3d9_frame` оставляет пустую draw-ветвь с комментарием `Guest draw calls are not translated yet; present the queued clear.`; Vulkan `vkCmdDrawIndexed` относится к **другим** material/non-guest путям. `guest_draw_translation=false` сериализуется как постоянный литерал, не runtime count/packet status.

[P2 packet capture adapter](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process2-dxt3-capture-capability-20261021/native_vulkan/src/d3d9_packet_capture_adapter.cpp) принимает `RecompiledGuestD3d9DrawIndexedPrimitivePacket` через `draw_indexed_primitive_callback`, затем `capture_draw` и optional `forward_draw`. `capture_draw` проверяет index/vertex buffer initialization и bound resource identity, vertex declaration, VS/PS и tokens; на успешной записи формирует `draw_<device>_<sequence>/capture.jsonl`, `buffers/` и `textures/`, с `draw_indexed_primitive` event, включая шесть Draw параметров, состояния и реальные bound DDS snapshots. Гостевой draw вход всё ещё не доказан, поэтому нельзя утверждать, что renderer принял или отверг такой packet.

**Обоснованный scope сейчас:** существующий PR #2144 уже закрыл известный независимый synthetic BC2 decode/transcode тест. Новый Vulkan pipeline, DXT3 packet consumer либо изменение render state до первого настоящего packet нельзя адресно проверить на retail-причинности без догадок об active draw resources. Даже если добавить новую synthetic fixture, это расширит synthetic coverage, **не закроет подтверждённый v763 runtime frontier**. Поэтому **нового P2 renderer-code PR сейчас нет**; это bounded engineering priority, а не запрет будущей независимой работы.

## 5. Точный минимальный evidence handoff от Process 1 — один реальный guest draw

**Поставить P1 задачу предоставить один положительный retail `IDirect3DDevice9::DrawIndexedPrimitive` event и сопоставленный принятый `RecompiledGuestD3d9DrawIndexedPrimitivePacket` версии 1** на том же SHA retail PE, с включённым capture adapter при самом прогоне. Для проверки **именно DXT3 renderer path** в одном packet должен быть активный sampled texture stage с `format=0x33545844` (DXT3/BC2), и приложены реальные mip bytes с SHA-256. Если первый найденный draw не использует DXT3, сохранить его для общего draw-ingress frontier, не объявляя DXT3 проверенным.

Одно минимальное передаваемое P2 evidence bundle:
1. **P1 import-entry + результат:** `import_name`, `thread_id`, `caller`, **guest `return_address` для восстановления callsite**, `ESP_entry`, `[ESP+0..0x1C]` (return address, device/`this`, primitive_type, signed base_vertex, min_vertex, num_vertices, start_index, primitive_count), `guest_call_trace_enabled=true` / `guest_call_trace_truncated=false`, и `HRESULT`/отказ плюс признак `P1 handler→P2 draw callback invoked`. Указать, что это *фактически наблюдённые* значения, не статическая гипотеза.
2. **Callback/packet acceptance:** `packet.version=1`, `guest_device`, `sequence`, шесть Draw аргументов; факт вызова `draw_indexed_primitive_callback`, `capture_draw` success/failure, `forward_draw` success/failure и error. Если P1 вызвал DIP, но отверг packet до callback, предоставить reject stage, HRESULT и resource/scene state: это будет upstream P1/compatibility blocker, не P2 image bug.
3. **Если packet принят — ровно один полный native capture snapshot**: `draw_<device>_<sequence>/capture.jsonl` с `draw_indexed_primitive` event и соответствующие `buffers/*.bin` (IB и все используемые VB), vertex declaration, VS/PS tokens + constants, sampler/render states, viewport, render target/depth/clear state и `textures/*.dds` для реально bound stages. Для DXT3 указать `stage`, `width/height`, `levels`, `pitch`, `format=0x33545844`, `pool`, payload SHA-256 и фактические compressed mip bytes, **не synthetic replacement**. При отсутствии содержательных bound ресурсов не конструировать fixture и не объявлять retail renderer доказанным.

Успех handoff = один положительный DIP import entry, подтверждённый P2 callback/packet snapshot и проверяемая последовательность реальных resource bytes. Только после этого P2 имеет конкретный вход для admission/BC2 decode/transcode/SVTP, Vulkan texture binding + submission и validation без смешения synthetic и retail. Отдельные host-frame/dispatch counts не заменяют этот пакет.

## Вердикт и ownership

- **PR #2145:** startup managed DXT3 capability gap **закрыт v763** в оговорённом bounded интеграционном прогоне, не gameplay/render.
- **PR #2144:** synthetic BC2/DXT3→RGBA8 texture path покрыт текущими тестами; реальный packet ещё не поступил.
- **Текущий блокер:** перед доказанным **P1 DrawIndexedPrimitive import-entry / callback packet ingress**. **Следующий владелец: P1** — дать один реальный положительный guest draw entry с минимальным сопоставленным packet/capture bundle; затем **P2** проводит admission/actual Vulkan validation. Не добавлять guest draws/state, не делать новое P2 renderer PR без нового наблюдаемого failure.
