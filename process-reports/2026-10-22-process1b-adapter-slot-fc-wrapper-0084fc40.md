# Process 1 — adapter primary slot +0xFC / retail wrapper 0x0084FC40

**Дата:** 2026-10-22. **Исходник доказательств:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Hash заново проверен на `SHIFT.exe`. Оригинальные инструкции независимо сверены через `objdump -D -Mintel -w`. DWORD первичной vtable прочитан напрямую из PE `.rdata`. Внешний D3D9 API-контракт используется только для квалифицированной классификации интерфейсного вызова и направления параметра.

**Объём:** исключительно `0x0084FC40–0x0084FC5B` и короткий доказанный constructor/device-pointer путь. Без повторного анализа соседнего `+0xF8`, без глобального vtable/caller/setter sweep, изменений исходников/runtime/P-code, renderer, guest-state forcing и без replay. Предыдущий проверенный отчёт по `+0xF8` принят как входной контекст. Метаданные фактического времени доставки сообщения (`startedAt`) непосредственно не доступны; время доставки и точную UTC-границу 12-минутного интервала здесь не выдумываем.

## Вывод

Оригинальная retail `.rdata` содержит `DWORD[0x00B1BCA4] = 0x0084FC40` (bytes `40 FC 84 00`), то есть primary adapter vtable `0x00B1BBA8+0xFC` действительно указывает на данный wrapper.

**Byte-grounded поведение:** `0x0084FC40` получает указатель adapter из `[EBP+8]`, загружает underlying device `D = DWORD[adapter+8]`, получает его *отдельную динамическую* vtable `V = DWORD[D]`, передаёт `D` и один неизменённый второй стековый аргумент в `DWORD[V+0xFC]`, затем возвращает неизменённый `EAX`. Два входных DWORD очищает `RET 8`. Единственный исходящий вызов `CALL EAX` по адресу `0x0084FC56`.

**API-level identification:** при ранее доказанном происхождении `D` из `IDirect3D9::CreateDevice` этот вызов совместим с `IDirect3DDevice9::GetClipStatus(D3DCLIPSTATUS9 *pClipStatus)`, возвращающим `HRESULT`; это интерфейсный слот **63** (offset `0xFC`). Из спецификации следует **выходное** направление `pClipStatus`; оно **не** читается как атрибут типа или `[out]` из PE opcode. См. официальную документацию Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/d3d9helper/nf-d3d9helper-idirect3ddevice9-getclipstatus и интерфейсный порядок: https://github.com/elishacloud/DirectX-Wrappers/blob/master/d3d9/IDirect3DDevice9Ex.h . Реальный адрес COM реализации не определён в original retail PE.

## 1. Exact ABI and control flow

Функция не содержит условных ветвей; весь block приведён в Appendix A без пропусков. Используется стековый receiver, а **не входной ECX=this**. Входной frame после `PUSH EBP; MOV EBP,ESP`:

| Stack | Retail byte-derived meaning | API-level name |
|---|---|---|
| `[EBP+0x08]` | adapter pointer | wrapper receiver |
| `[EBP+0x0C]` | второй неизменённый 32-bit аргумент | `D3DCLIPSTATUS9 *pClipStatus`, output по API |

Инструкция за инструкцией:

1. `0x0084FC40: PUSH EBP`, `0x0084FC41: MOV EBP,ESP`.
2. `0x0084FC43: EAX=[EBP+8]` — adapter. `0x0084FC46: EAX=[EAX+8]` — `D`.
3. `0x0084FC49: EDX=[EBP+0xC]` — указатель (по API); **никакой проверки или разыменования** этого аргумента в wrapper.
4. `0x0084FC4C: ECX=[D]` — динамическая device vtable `V`.
5. `0x0084FC4E: PUSH EDX` — передать caller argument, затем `0x0084FC4F: PUSH EAX` — COM receiver `D`. Внутри вызываемого метода после процессорного push адреса возврата ожидаемый кадр: `[ESP+4]=D`, `[ESP+8]=pClipStatus`.
6. `0x0084FC50: EAX=DWORD[V+0xFC]`, `0x0084FC56: CALL EAX` — единственный вызов в block.
7. `0x0084FC58: POP EBP`, `0x0084FC59: RET 8` (три байта инструкции занимают VA `0x0084FC59–0x0084FC5B`). Wrapper выполняет callee cleanup **8 байт своих первоначальных аргументов**. Вызываемый COM stdcall также снимает **свои отдельные 8 байт**; это не двойная очистка одного стека.

От `0x0084FC56` до выхода нет операции над EAX: **HRESULT passthrough** при API-интерпретации. Wrapper не проверяет успешность, знак или равенство нулю, не преобразует результат к bool и не обрабатывает HRESULT. Фактическое runtime значение EAX и точный target EIP неизвестны. Функция сохраняет EBP, не использует невольатильные EBX/ESI/EDI, меняет volatile EAX/ECX/EDX. Нет локального stack allocation, null checks, проверки валидности outputPointer, обработки HRESULT или conditional branch.

## 2. Bounded pointer + vtable provenance

PE-primary vtable (отдельная от COM device vtable):

```text
adapter primary vptr: 0x00B1BBA8
.rdata VA 0x00B1BCA0 (+0xF8): 20 FC 84 00  => 0x0084FC20
.rdata VA 0x00B1BCA4 (+0xFC): 40 FC 84 00  => 0x0084FC40
.rdata VA 0x00B1BCA8 (+0x100): 00 E8 84 00 => 0x0084E800
```

На обычном constructor пути retail `0x00850100`:
- `0x00850109: MOV DWORD[adapter],0x00B1BBA8`.
- `0x0085010F: MOV DWORD[adapter+8],EAX`, где EAX является supplied device pointer этого constructor.
- `0x00850176: MOV BYTE[adapter+4],0` — **только контекст создания объекта**, не побочный эффект wrapper `0x0084FC40`.

В ранее доказанном пути инициализации `0x0083304D–0x0083306C` виртуальный вызов на объекте `IDirect3D9` через `+0x40` согласован с `CreateDevice`; на success path `0x00833095` читает `[EDI]` с созданным device pointer, `0x00833097–0x0083309E` передаёт его helper `0x0084E2C0` для embedded adapter `wrapper+0x1F7C`, а `0x0084E2DD` сохраняет pointer как `[adapter+8]`. `0x008330B7` публикует `wrapper+0x1F7C` в `[wrapper+0x478]`. Таким образом receiver `D` в текущем wrapper имеет установленное **IDirect3DDevice9 object provenance**, а не просто случайный offset `+8`.

Первый виртуальный lookup `adapter.vptr+0xFC` (вызов этой wrapper функции) фиксирован original retail `.rdata`; второй lookup **`device.vptr+0xFC`** (внутри wrapper) использует указатель vtable объекта, созданного внешним D3D9. **Не** утверждается, что оба lookup имеют один и тот же function pointer. Вторая таблица и точный runtime EIP её метода могут зависеть от конкретного D3D9 implementation и не разрешены статически.

API-классификация опирается одновременно на proven COM interface source, offset index 63, **один explicit stack pointer-shaped argument** и порядок GetClipStatus сразу после SetClipStatus в стандартном интерфейсе. **Направление [out], тип D3DCLIPSTATUS9 и значение HRESULT — API specification/inference, а не буквально записанная сигнатура PE.**

## 3. Bounded effects and exclusions

В полном `0x0084FC40–0x0084FC5B`:
- **0 прямых записей в память через adapter**; нет даже чтения `BYTE[adapter+4]`.
- **0 cache или dirty-state записей**, нет обращений к массивам состояния, flags или queue.
- **0** вызовов primary adapter `+0xF0`, device `BeginStateBlock` через `+0xF0`, `EndStateBlock` через `+0xF4`, а также **0** Draw* вызовов или guest imports. Синтаксически присутствует **только одна** инструкция CALL, с device slot `+0xFC`.
- По контракту `GetClipStatus` может **записать результат** через предоставленный `pClipStatus` (выходной параметр). Эта запись не является явной retail PE инструкцией данного wrapper и не демонстрируется runtime trace.
- Если caller специально передаст outputPointer, alias которого пересекается с `adapter+4`, downstream write-through теоретически способен изменить память adapter. **Такой alias не установлен**, поэтому корректная формулировка — «нет доказанной записи `BYTE[adapter+4]` на bounded receiver-proven path», а не универсальное отсутствие любого возможного alias-based write.

Не рассмотрены никакие сторонние caller sites, глобальные adapters, guest-state значения, COM internal effects и значения output buffers в момент выполнения. Ни одно «отсутствие» из этого раздела не переносится на всё приложение.

## 4. Evidence tiers: original PE / external API / runtime

**Proven by original PE bytes:** файл с точным SHA-256; vtable slot adapter `0x00B1BCA4→0x0084FC40`; 12 инструкций полного target; adapter→device→device.vptr→virtual slot `+0xFC`; порядок `PUSH EDX; PUSH EAX`; `RET 8`; одна ветка, отсутствие собственных stores и неизменённый EAX после call; короткие constructor/device publication anchors.

**API-level inference, externally corroborated:** D3D9 device index 63 corresponds to `GetClipStatus(D3DCLIPSTATUS9*)`, `HRESULT`, parameter marked `[out]` by Microsoft Learn. Это обоснованное имя интерфейсного метода, не статически названная точка PE и не декомпилированный body внешнего COM object.

**Runtime:** никто не заявляет новый replay или запуск игры. Ранее пользователь передавал ограниченные v757 P-code negative observations лишь по выбранным Begin/End/Draw targets; для **`0x0084FC40`** измерений в них нет. Нельзя извлекать из тех trace observations сведения о количестве вызовов этого wrapper либо о GetClipStatus/HRESULT.

**Unresolved:** фактический вход в функцию, значение COM output-pointer в момент вызова, его alias/validity, динамический device.vptr, реальный адрес метода и его HRESULT / содержимое выходной структуры. Запрос не санкционирует глобальный sweep.

## 5. Exactly one next evidence-backed target

**`0x0084E800`** — следующий **первичный adapter vtable slot `+0x100`**, проверен оригинальным PE `DWORD[0x00B1BCA8]=0x0084E800`. Его первые байты показывают проверку `BYTE[adapter+4]` и обращение к собственному cached-object pointer массиву; альтернативная ветка использует **`underlyingDevice.vptr+0x100`**. Это ровно один локальный следующий target для отдельного анализа read/cache/API provenance. Его полная семантика **не расследовалась в этой задаче**.

## Appendix A — полный оригинальный target block, PE bytes

```asm
0084fc40: 55                    push   ebp
0084fc41: 8b ec                 mov    ebp,esp
0084fc43: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084fc46: 8b 40 08              mov    eax,DWORD PTR [eax+0x8]
0084fc49: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084fc4c: 8b 08                 mov    ecx,DWORD PTR [eax]
0084fc4e: 52                    push   edx
0084fc4f: 50                    push   eax
0084fc50: 8b 81 fc 00 00 00     mov    eax,DWORD PTR [ecx+0xfc]
0084fc56: ff d0                 call   eax
0084fc58: 5d                    pop    ebp
0084fc59: c2 08 00              ret    0x8
```

## Appendix B — полный original constructor block (provenance context, without re-audit)

```asm
00850100: 55                    push   ebp
00850101: 8b ec                 mov    ebp,esp
00850103: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00850106: 56                    push   esi
00850107: 8b f1                 mov    esi,ecx
00850109: c7 06 a8 bb b1 00     mov    DWORD PTR [esi],0xb1bba8
0085010f: 89 46 08              mov    DWORD PTR [esi+0x8],eax
00850112: e8 d9 9f bb ff        call   0x40a0f0
00850117: 33 c9                 xor    ecx,ecx
00850119: 89 86 e0 19 00 00     mov    DWORD PTR [esi+0x19e0],eax
0085011f: ba 08 00 00 00        mov    edx,0x8
00850124: f7 e2                 mul    edx
00850126: 0f 90 c1              seto   cl
00850129: f7 d9                 neg    ecx
0085012b: 0b c8                 or     ecx,eax
0085012d: 51                    push   ecx
0085012e: e8 8d 67 03 00        call   0x8868c0
00850133: 89 86 dc 19 00 00     mov    DWORD PTR [esi+0x19dc],eax
00850139: c7 00 20 00 00 00     mov    DWORD PTR [eax],0x20
0085013f: 8b 86 dc 19 00 00     mov    eax,DWORD PTR [esi+0x19dc]
00850145: c7 40 08 10 00 00 00  mov    DWORD PTR [eax+0x8],0x10
0085014c: 8b 8e dc 19 00 00     mov    ecx,DWORD PTR [esi+0x19dc]
00850152: c7 41 10 30 00 00 00  mov    DWORD PTR [ecx+0x10],0x30
00850159: 8b 96 dc 19 00 00     mov    edx,DWORD PTR [esi+0x19dc]
0085015f: c7 42 18 08 00 00 00  mov    DWORD PTR [edx+0x18],0x8
00850166: 8b 86 dc 19 00 00     mov    eax,DWORD PTR [esi+0x19dc]
0085016c: c7 40 20 38 00 00 00  mov    DWORD PTR [eax+0x20],0x38
00850173: 83 c4 04              add    esp,0x4
00850176: c6 46 04 00           mov    BYTE PTR [esi+0x4],0x0
0085017a: 8b c6                 mov    eax,esi
0085017c: 5e                    pop    esi
0085017d: 5d                    pop    ebp
0085017e: c2 04 00              ret    0x4
```

## Appendix C — узкий direct device-provenance anchor и следующий слот (без анализа новой функции)

```asm
0083304d: 8b 46 08              mov    eax,DWORD PTR [esi+0x8]
00833050: 8b 10                 mov    edx,DWORD PTR [eax]
00833052: 8b 52 40              mov    edx,DWORD PTR [edx+0x40]
00833055: 57                    push   edi
00833056: 8d 8e 7c 04 00 00     lea    ecx,[esi+0x47c]
0083305c: 51                    push   ecx
0083305d: 8b 4d fc              mov    ecx,DWORD PTR [ebp-0x4]
00833060: 6a 50                 push   0x50
00833062: 51                    push   ecx
00833063: 8b 4e 18              mov    ecx,DWORD PTR [esi+0x18]
00833066: 51                    push   ecx
00833067: 8b 4e 14              mov    ecx,DWORD PTR [esi+0x14]
0083306a: 51                    push   ecx
0083306b: 50                    push   eax
0083306c: ff d2                 call   edx
00833095: 8b 17                 mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea    ecx,[esi+0x1f7c]
0083309d: 52                    push   edx
0083309e: e8 1d b2 01 00        call   0x84e2c0
0084e2dd: 89 46 08              mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov    DWORD PTR [esi+0x478],eax
```

```asm
0084e800: 55                    push   ebp
0084e801: 8b ec                 mov    ebp,esp
0084e803: 56                    push   esi
0084e804: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0084e807: 80 7e 04 00           cmp    BYTE PTR [esi+0x4],0x0
0084e80b: 74 31                 je     0x84e83e
```

**Report only.** Никаких файлов кода, runtime, P2, renderer, guest state или PR не изменено. 
