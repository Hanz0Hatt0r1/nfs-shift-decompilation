# Process 1 — retail DrawIndexedPrimitive forwarder 0x0084FD60

**Дата:** 2026-10-22. **Target:** один retail function block `0x0084FD60–0x0084FD9E`.  
**Идентичность PE:** Need for Speed SHIFT PC retail 1.02; PE32 x86; ImageBase `0x00400000`.  
**SHA-256 оригинального `SHIFT.exe`, проверено повторным вычислением:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Основания:** оригинальные приложенные `/mnt/data/SHIFT.exe` и `SHIFT_objdump_full.txt`; самостоятельный `objdump -D -M intel -w --start-address=0x84fd60 --stop-address=0x84fd9f SHIFT.exe`, байтовое чтение PE `.rdata`, исходные v753 факты из условия. Использован прежний отчёт как контекст producer path, **без повторного анализа 0x00852760**. Прямого 실행ения v753 в этой задаче не было. Никаких code/runtime/P-code/renderer/field edits и PR.

## Результат и предел доказательства

**Результат по retail bytes:** `0x0084FD60` — adapter method, который при `BYTE [adapter+4]!=0` вызывает helper `0x0084F000(adapter)`, затем **без проверки его return** всегда считывает `device=DWORD[adapter+8]`, формирует семь стековых DWORD (COM this + шесть неизменённых параметров), и вызывает `DWORD[DWORD[device]+0x148]` по **0x0084FD98**. Последующий код не модифицирует EAX и завершает `RET 0x1C`.

**Конечный метод подтверждается сочетанием трёх независимых оснований:**
1. **Доказанный origin интерфейса**: `0x0083304D–0x0083306C` вызывает слот `+0x40` у `[wrapper+8]` в форме **IDirect3D9::CreateDevice**, сохраняя результат в output pointer; `0x00833095` загружает `device=DWORD[EDI]` и `0x0083309E` передаёт его в `0x0084E2C0`, где `0x0084E2DD` пишет `DWORD[adapter+8]=device`.
2. **Реальная adapter vtable:** `0x0083252A–0x00832541` вызывает `0x00850100` для встроенного `wrapper+0x1F7C`; при `0x00850109` записывается `[adapter]=0x00B1BBA8`. Данные PE по адресу **0x00B1BCF0 = 0x00B1BBA8+0x148** содержат DWORD **0x0084FD60**. Успешная инициализация устройства в `0x008330B1–0x008330B7` публикует `[wrapper+0x478]=wrapper+0x1F7C`, а `0x008330D0` выставляет byte `[wrapper+0x5E8]=1`. Getter `0x0082E110` при ненулевом флаге возвращает `[wrapper+0x478]`; это конкретный путь к adapter, а не предположение по смещению.
3. **Контракт конечного COM-вызова:** в стандартном интерфейсе `IDirect3DDevice9` индекс **82**, byte offset **0x148**, — `DrawIndexedPrimitive`; шесть аргументов на стеке точно соответствуют сигнатуре `D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT`. Указатель на vtable берётся с объекта устройства, созданного через CreateDevice, не с произвольного объекта с похожим слотом.

**Поэтому это доказанный условный статический маршрут к guest COM `IDirect3DDevice9::DrawIndexedPrimitive`.** Это не статический импорт `DrawIndexedPrimitive` из PE import address table: метод вызывается через COM vtable; PE импортирует `d3d9.dll!Direct3DCreate9` и `D3DPERF_*` отдельно. Не доказаны непосредственный вызов устройства в v753, host bridge/translation, выполнение Draw после UI gate, либо результирующая геометрия в конкретном кадре.

## Точный ABI / stack frame

**Adapter method:** callee-cleanup x86 stack ABI, **семь DWORD**: `adapter` plus six arguments. У функции нет входных ECX/EDX-аргументов. Prologue `push EBP; mov EBP,ESP; push ESI` сохраняет EBP/ESI; локальных переменных не выделяется. Входные stack offsets:

| До вызова: offset относительно EBP | Original parameter | Forwarding callsite |
|---|---|---|
| **[EBP+0x08]** | adapter pointer, custom `this` | `0x0084FD64` → ESI; **не** forwarded как underlying COM this |
| **[EBP+0x0C]** | `PrimitiveType` (D3DPRIMITIVETYPE) | `0x0084FD8D–0x0084FD90` |
| **[EBP+0x10]** | `BaseVertexIndex` (INT) | `0x0084FD89–0x0084FD8C` |
| **[EBP+0x14]** | `MinVertexIndex` (UINT) | `0x0084FD85–0x0084FD88` |
| **[EBP+0x18]** | `NumVertices` (UINT) | `0x0084FD81–0x0084FD84` |
| **[EBP+0x1C]** | `startIndex` (UINT) | `0x0084FD7D–0x0084FD80` |
| **[EBP+0x20]** | `primCount` (UINT) | `0x0084FD74–0x0084FD7C` |

Порядок PUSH — **от последнего параметра к первому**: `[+0x20], [+0x1C], [+0x18], [+0x14], [+0x10], [+0x0C]`, затем `push EAX`, где EAX=`[adapter+8]`. Таким образом underlying method получает `[ESP+4]=device`, после него шесть параметров в **том же порядке и с теми же 32-битовыми значениями**, что у adapter caller. Никаких пересчётов PrimitiveType, индексов, вершин или количества примитивов здесь нет.

После `CALL EAX` с адреса `0x0084FD98` код состоит только из `POP ESI; POP EBP; RET 0x1C` (`0x0084FD9A–0x0084FD9E`): underlying `HRESULT` в EAX протягивается к исходному caller **без теста/нормализации/трансформации**. `RET 0x1C` убирает 28 байт (adapter + 6 DWORD); underlying COM stdcall также использует callee cleanup своих семи аргументов. Если underlying call returns normally, нет другого выхода, а ветвь на `0x0084FD74` объединяет оба значения флага.

Ни одно поле `adapter+4` или `adapter+8` не записывается **в самом** 0x0084FD60; `0x0084F000` может иметь свои side effects, поэтому утверждение о неизменности adapter в целом не следует делать.

## Условный helper 0x0084F000

`0x0084FD67`: **`CMP BYTE [ESI+4],0`**. `0x0084FD6B: JE 0x0084FD74` обходит helper при равенстве нулю. Иначе `0x0084FD6D: mov ECX,ESI`; `0x0084FD6F: CALL 0x0084F000` (без stack parameters). `0x0084FD74` — общий продолженный поток; **внешний DrawIndexedPrimitive вызов не зависит от EAX helper**.

В начале `0x0084F000`: `0x0084F00A: test BYTE [adapter+0x19D8],4`, `0x0084F011: mov EBX,[adapter+8]`; внутри есть обращения к сравнительным/кэшированным массивам состояния и calls device slots `+0x104` (0x0084F044), `+0x114` (0x0084F0BC), `+0x1AC` (0x0084F105), `+0x170` (0x0084F12B) при соответствующих условиях. Это обосновывает роль **state/cache synchronization helper** как интерпретацию по структуре обращений, но точное имя и полный side-effect set этой большой функции не восстанавливались в данном bounded задании. Ни сам флаг `adapter+4`, ни этот helper не доказывают самостоятельный DrawIndexedPrimitive: основной forwarder вызывает устройство **после** helper.

В initializer `0x00850100` по `0x00850176` `BYTE [adapter+4]=0`; когда/почему флаг станет ненулевым — вне этой задачи, не значит, что такое невозможно.

## Static caller witness и конкретный пример параметров

Для **одного** реального участка `0x00851730` (в предыдущем отчёте рассмотрен шире), `0x0085174C–0x00851752` загружает global wrapper `[0x00C26058]` и вызывает `0x0082E110`; continuing path сохраняет returned adapter в EDI. На `0x00851B4A–0x00851B5F`:

```asm
00851b4a: 8b 07                 mov eax,DWORD PTR [edi]
00851b4c: 8b 88 48 01 00 00     mov ecx,DWORD PTR [eax+0x148]
00851b52: 6a 02                 push 0x2
00851b54: 6a 00                 push 0x0
00851b56: 6a 04                 push 0x4
00851b58: 6a 00                 push 0x0
00851b5a: 6a 00                 push 0x0
00851b5c: 6a 04                 push 0x4
00851b5e: 57                    push edi
00851b5f: ff d1                 call ecx
```

При **adapter.vptr=0x00B1BBA8**, это вызывает `0x0084FD60` с `PrimitiveType=4 (triangle list)`, `BaseVertexIndex=0`, `MinVertexIndex=0`, `NumVertices=4`, `startIndex=0`, `primCount=2`. Этот пример **не является** фиксированной сигнатурой/константами для всех других callers forwarder и **не является runtime hit v753**. В полном линейном objdump **0 direct `CALL rel32` в 0x0084FD60**; функция достигается через vtable, так что отсутствие прямых calls ожидаемо и не аргумент о недостижимости.

## Replay feasibility и v753 baseline

В текущей прикреплённой рабочей среде проверены только `/mnt/data/SHIFT.exe`, `/mnt/data/SHIFT_objdump_full.txt` и его `.gz` копия. Исполняемый **`shift_runtime`**, полный v753 manifest, game-data set v661, скрипт запуска и v753 original JSON здесь **не доступны**; команда `which shift_runtime` не находит binary, проверка локальных путей `/mnt/data`, `/home/oai/share`, `/home/oai/code` не находит v753 input bundle. **Поэтому replay заново не запускался, и новый след не генерировался.** Нельзя создавать фиктивное `events=[]` или выдавать пользовательский baseline за собственный повторный прогон.

**Только предоставленные пользователем данные v753:** 360 host frames, P-code host-frame-loop, no blocker, game data v661, manifest v659; trace включён и не усечён; targets: **0x00852760** и четыре Draw* guest targets (`DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`), **event count=0**; guest_draw_translation=false; 360 clear и 360 present submissions. **0x0084FD60 не включён в перечисленные v753 target addresses**: по v753 нет адресно-специфического измерения входов в forwarder. Наблюдение нулевых выбранных Draw* относится только к bounded trace указанного запуска и конфигурации; нет универсального вывода о невозможности draw.

### Read-only configuration for the next targeted replay, if identical inputs become available

Trace targets: `0x0084FD60` **and** four named guest Draw* targets. Filter forwarder entry to record `return-address/caller EIP`, `[ESP+4]` adapter, `BYTE[adapter+4]`, `DWORD[adapter+8]`, primary `DWORD[adapter]`, `DWORD[[adapter]+0x148]`, six DWORD at `[ESP+8..ESP+0x1C]` and optionally `DWORD[device]`/`DWORD[[device]+0x148]`, plus frame/dispatch ID and return EAX. No writes, no forcing gate, no changed renderer translation. At the moment of entry `EBP` is **not yet this function's frame**; offsets must be taken from the entry ESP or measured after `push ebp; mov ebp,esp`.

If entries=0 in a new controlled bounded run, report **only** that no forwarder entry was observed over that interval; any stronger reachability claim requires more evidence.

## Confidence ledger

**Proven original retail bytes:** exact 63-byte function, both branch paths and helper edge, ESI/EBP saves, adapter+4 comparison, underlying device pointer read at +8, six arguments preserved in reverse push order, device COM vptr+0x148 resolution at 0x0084FD98, EAX preservation, `RET 0x1C`; exact primary adapter vtable slot, embedded adapter construction, device pointer provenance through CreateDevice and 0x0084E2C0, example caller's parameter values.

**Supported by external ABI identification (not merely offset inference):** known COM `IDirect3DDevice9::DrawIndexedPrimitive` index82 with six parameters, corroborated by actual CreateDevice-provided pointer and call arity.

**Given dynamic evidence only:** v753 360-frame nontruncated trace of *other selected targets* with zero events. No new runtime vtable/adapter values and no newly captured forwarder caller/args.

**Unproven:** v753 adapter forwarder invocation, particular game-frame submissions, actual host-side D3D9 method behavior, full 0x0084F000 side effects, alternative device vtable implementation or dynamically swapped adapter class, general UI/menu causality. Static potential is not equivalent to actual execution.

## Complete original executable block 0x0084FD60–0x0084FD9E

Unabridged, machine bytes copied from independently verified `objdump -D -M intel -w` of original SHA-matching PE. `0x0084FD9F` onward = INT3 padding, not part of function.

```asm
0084fd60: 55                    push   ebp
0084fd61: 8b ec                 mov    ebp,esp
0084fd63: 56                    push   esi
0084fd64: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0084fd67: 80 7e 04 00           cmp    BYTE PTR [esi+0x4],0x0
0084fd6b: 74 07                 je     0x84fd74
0084fd6d: 8b ce                 mov    ecx,esi
0084fd6f: e8 8c f2 ff ff        call   0x84f000
0084fd74: 8b 55 20              mov    edx,DWORD PTR [ebp+0x20]
0084fd77: 8b 46 08              mov    eax,DWORD PTR [esi+0x8]
0084fd7a: 8b 08                 mov    ecx,DWORD PTR [eax]
0084fd7c: 52                    push   edx
0084fd7d: 8b 55 1c              mov    edx,DWORD PTR [ebp+0x1c]
0084fd80: 52                    push   edx
0084fd81: 8b 55 18              mov    edx,DWORD PTR [ebp+0x18]
0084fd84: 52                    push   edx
0084fd85: 8b 55 14              mov    edx,DWORD PTR [ebp+0x14]
0084fd88: 52                    push   edx
0084fd89: 8b 55 10              mov    edx,DWORD PTR [ebp+0x10]
0084fd8c: 52                    push   edx
0084fd8d: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084fd90: 52                    push   edx
0084fd91: 50                    push   eax
0084fd92: 8b 81 48 01 00 00     mov    eax,DWORD PTR [ecx+0x148]
0084fd98: ff d0                 call   eax
0084fd9a: 5e                    pop    esi
0084fd9b: 5d                    pop    ebp
0084fd9c: c2 1c 00              ret    0x1c
```

**Exactly one next bounded target:** `0x0084FD60` itself in a fresh targeted guest-call trace, with actual adapter/context/parameter capture as specified above. Do not reuse the v753 event count as a direct measurement of this function.
