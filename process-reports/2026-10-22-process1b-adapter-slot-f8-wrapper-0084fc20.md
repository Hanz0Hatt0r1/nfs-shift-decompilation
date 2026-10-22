# Process 1 — bounded retail adapter +0xF8: 0x0084FC20

**Дата анализа:** 2026-10-22. **Бинарник:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **Проверенный SHA-256 оригинального `SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Границы:** только один adapter wrapper `0x0084FC20–0x0084FC3B`, его исходный ABI, ближайшие constructor/device-provenance bytes и одно соседнее vtable-значение для следующей задачи. Предыдущий +0xEC отчёт принят как установленная основа, повторно не анализируется. Использованы первоначальный PE (повторный `sha256sum`, `objdump -D -M intel -w`, `objdump -s`) и публичная сигнатура D3D9 API **лишь для определения имени интерфейсного метода**. Никакого replay, изменения кода, runtime/P-code, renderer или guest state. Нет доказательств выполнения этого блока в каком-либо runtime replay.

**Время доставки:** точная отметка user-message `startedAt` не доступна в предоставленных мне метаданных; не выдаётся предполагаемая UTC отметка за полученную. Публикация выполнена в рамках данного turn.

## Итог

В обычной ранее доказанной цепочке инициализации primary adapter vptr равен `0x00B1BBA8`. **PE .rdata `DWORD[0x00B1BCA0]=0x0084FC20`**. Функция `0x0084FC20` читает `D=DWORD[adapter+8]`, `V=DWORD[D]`, отправляет **один** неизменённый аргумент `[EBP+0x0C]` вместе с `D` (COM receiver) в `DWORD[V+0xF8]`, а затем возвращает результат `EAX` без изменения посредством `RET 8`.

**API-level identity (provenance + ABI + interface order):** `IDirect3DDevice9::SetClipStatus(const D3DCLIPSTATUS9 *pClipStatus)`, COM slot index **62** (`0xF8 / 4`). Это квалифицированная идентификация интерфейса, не прямой named PE import и не статически известный адрес реализации COM метода. Официальная сигнатура: https://learn.microsoft.com/en-us/windows/win32/api/d3d9helper/nf-d3d9helper-idirect3ddevice9-setclipstatus ; независимая декларация интерфейса с порядком слотов: https://github.com/elishacloud/DirectX-Wrappers/blob/master/d3d9/IDirect3DDevice9Ex.h .

## 1. Оригинальная таблица: конкретный adapter virtual dispatch

В `.rdata`, оригинальные little-endian DWORD:

```text
Primary adapter vptr = 0x00B1BBA8
VA 0x00B1BC9C [+0xF4]: F0 FB 84 00 → 0x0084FBF0
VA 0x00B1BCA0 [+0xF8]: 20 FC 84 00 → 0x0084FC20
VA 0x00B1BCA4 [+0xFC]: 40 FC 84 00 → 0x0084FC40
```

В original PE constructor `0x00850100` по `0x00850109` записывает `DWORD[adapter]=0x00B1BBA8`; по `0x0085010F` записывает supplied device pointer в `DWORD[adapter+8]`. Подтверждённая native цепочка создания интерфейса: `0x0083304D–0x0083306C` загружает COM virtual `+0x40` из исходного `[wrapper+8]` и вызывает его с формой `IDirect3D9::CreateDevice` (device output через local `EDI`); `0x00833095–0x0083309E` забирает `[EDI]` и подаёт его `0x0084E2C0`, который по `0x0084E2DD` записывает `DWORD[adapter+8]=EAX`. `0x008330B7` публикует `[wrapper+0x478]=wrapper+0x1F7C` для embedded adapter. Это доказывает **тип pointer в обычном constructor пути**, но не фактическую identity произвольного runtime receiver или отсутствие подмены vptr.

Различаются два уровня: `adapter.vptr+0xF8` в фиксированной retail `.rdata` ведёт к **0x0084FC20**; `device.vptr+0xF8` внутри неё ведёт к **реализации внешнего IDirect3DDevice9**, адрес которой из original PE не извлекается. Нельзя смешивать эти vtable.

## 2. Точный x86 stack ABI и value-flow

Entry function `0x0084FC20` использует **два аргумента на стеке**; не требует входного `ECX=this`:

| Вход после `PUSH EBP / MOV EBP,ESP` | Значение | Использование |
|---|---|---|
| `[EBP+0x08]` | **adapter pointer** | `0x0084FC23` загружается в EAX, по `0x0084FC26` разыменовывается `[adapter+8]` |
| `[EBP+0x0C]` | **pClipStatus** по API-идентификации; PE доказывает только один без изменений переданный DWORD | `0x0084FC29` грузит в EDX, `0x0084FC2E` передаёт `PUSH EDX` |

Последовательность без пропусков:
1. `0x0084FC20–0x0084FC21`: сохранить caller EBP и установить frame.
2. `0x0084FC23: EAX=[EBP+8]` (adapter), `0x0084FC26: EAX=[EAX+8]` → underlying `D`.
3. `0x0084FC29: EDX=[EBP+0xC]` → передаваемый DWORD.
4. `0x0084FC2C: ECX=[D]` → dynamic device vptr `V`.
5. `0x0084FC2E: PUSH EDX`, затем `0x0084FC2F: PUSH EAX`. У COM callee на входе: `[ESP+4]=D`, `[ESP+8]=pClipStatus` (после аппаратного push return address).
6. `0x0084FC30: EAX=[V+0xF8]`, `0x0084FC36: CALL EAX`: единственный CALL в функции.
7. `0x0084FC38: POP EBP; 0x0084FC39: RET 8` (machine instruction занимает байты `0x0084FC39–0x0084FC3B`). Adapter wrapper снимает свои **8 bytes**, а COM callee снимает **свои отдельные 8 bytes**, если соблюдает стандартный COM stdcall. Никакого двойного освобождения того же кадра нет.

**Возврат:** ни теста EAX, ни `HRESULT` sign/equality branch, ни нормализации к Boolean. После `CALL EAX` инструкции не меняют EAX. Поэтому status/device result прозрачно возвращается вызывающему adapter caller; по D3D9 ABI это `HRESULT`, но реальный код/результат underlying implementation из retail байт не наблюдаем. `EBP` сохраняется; `EAX/ECX/EDX` используются как volatile; `EBX/ESI/EDI` этой функцией не затрагиваются. Нулевых проверок receiver, device и parameter в wrapper нет. Только **один** исполняемый путь/эпилог, ветвлений нет.

## 3. Метод по достаточному provenance, а не по одному offset

*Original PE:* `device=DWORD[adapter+8]`; constructed through confirmed CreateDevice object path; `F=DWORD[DWORD[device]+0xF8]`; на stack переданы `device` и **ровно один указателеподобный DWORD**.
*External API ABI:* `IDirect3DDevice9` имеет интерфейсный индекс **62**, `SetClipStatus(const D3DCLIPSTATUS9*)` с ровно **одним** explicit аргументом, возвращающий HRESULT. Рядом по интерфейсному порядку идут `EndStateBlock` (61) и `GetClipStatus` (63). Это соответствует функции без дополнительных конвертаций.
*Inference boundary:* машинные байты сами не содержат символа `SetClipStatus`, не проверяют тип/содержимое `D3DCLIPSTATUS9`, не раскрывают адрес динамического COM method и не показывают, был ли он вызван в Linux guest P-code. Таким образом доказан conditional structurally correct forwarding через device slot, а **API имя выведено по установленному типу объекта, сигнатуре и спецификации**.

## 4. Bounded side effects and exclusions

Точный target `0x0084FC20–0x0084FC3B` имеет **ноль инструкций записи в память adapter**: отсутствуют `MOV [adapter+offset],...` и другие adapter field stores. Он **не читает и не пишет `BYTE[adapter+4]`**, не трогает dirty flags или cache. Не вызывает BeginStateBlock (`device.vptr+0xF0`) либо EndStateBlock (`device.vptr+0xF4`), не вызывает adapter slot `+0xF0` и не содержит DrawPrimitive/DrawIndexedPrimitive/UP call или прямого D3D9 Draw import. Единственный исходящий виртуальный вызов — `device.vptr+0xF8`, API идентифицированный как `SetClipStatus`, *не Draw*.

Вызванный COM метод по API **может менять clip status самого device** и возвращать HRESULT; это является **семантикой внешнего интерфейса**, а не доказанной записью исходного PE кода. Допускаемые alias/bad pointer/internal D3D side effects не исследовались и не дают доказанный write adapter+4. Нет оснований выводить, что функция когда-либо реально исполнялась.

## 5. Evidence tiers

**PE-byte proven:** original SHA-256; exact 11 machine-instruction entries and 28-byte target function, vtable DWORD `[0x00B1BCA0]=0x0084FC20`; two wrapper stack args `[EBP+8]` и `[EBP+0xC]`; `D=[adapter+8]`, `V=[D]`, `F=[V+0xF8]`, exact reverse PUSH order, unmodified EAX after indirect call, final `RET 8`, no writes in own body, no Draw*/Begin/End operations within function. Prior PE constructor provenance is reused with locally verified anchor disassembly.

**API inference:** `IDirect3DDevice9::SetClipStatus(const D3DCLIPSTATUS9*)`, slot index 62, HRESULT, based on CreateDevice-proven object and correct one-param COM forwarding. Not a named retail PE import.

**Runtime:** user-provided earlier bounded v757 replay traced *different* selected Begin/End/Draw targets and reported zero events. There are **no v757 measurements of `0x0084FC20`** supplied. No replay, no guest execution, no runtime modification or claim of launching game in this task. Nothing in the observed P-code counts proves this method entered or succeeded.

**Unresolved:** actual runtime COM function pointer/value, caller-provided pClipStatus contents, HRESULT value, adapter vptr/pointer at runtime, callers/aliases outside this single-function scope. No global vtable/caller or setter audit.

## 6. Exactly one next evidence-backed target

**`0x0084FC40`** — adjacent primary adapter slot **`+0xFC`**, fixed PE .rdata `DWORD[0x00B1BCA4]=0x0084FC40` (bytes `40 FC 84 00`). Original bytes show explicit adapter stack receiver and one forwarded argument to **`device.vptr+0xFC`**. A separate bounded assignment can verify its complete ABI and distinguish API `GetClipStatus` from SetClipStatus using the source/shape, without broadening this task. **No other next target is requested or proposed.**

## Appendix A — complete, byte-exact GNU retail objdump 0x0084FC20–0x0084FC3B

```asm
0084fc20: 55                    push   ebp
0084fc21: 8b ec                 mov    ebp,esp
0084fc23: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084fc26: 8b 40 08              mov    eax,DWORD PTR [eax+0x8]
0084fc29: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084fc2c: 8b 08                 mov    ecx,DWORD PTR [eax]
0084fc2e: 52                    push   edx
0084fc2f: 50                    push   eax
0084fc30: 8b 81 f8 00 00 00     mov    eax,DWORD PTR [ecx+0xf8]
0084fc36: ff d0                 call   eax
0084fc38: 5d                    pop    ebp
0084fc39: c2 08 00              ret    0x8
```

## Appendix B — narrow original PE provenance bytes

```asm
00850109: c7 06 a8 bb b1 00     mov DWORD PTR [esi],0xb1bba8
0085010f: 89 46 08              mov DWORD PTR [esi+0x8],eax
00850176: c6 46 04 00           mov BYTE PTR [esi+0x4],0x0

0083304d: 8b 46 08              mov eax,DWORD PTR [esi+0x8]
00833050: 8b 10                 mov edx,DWORD PTR [eax]
00833052: 8b 52 40              mov edx,DWORD PTR [edx+0x40]
00833055: 57                    push edi
00833056: 8d 8e 7c 04 00 00     lea ecx,[esi+0x47c]
0083305c: 51                    push ecx
0083305d: 8b 4d fc              mov ecx,DWORD PTR [ebp-0x4]
00833060: 6a 50                 push 0x50
00833062: 51                    push ecx
00833063: 8b 4e 18              mov ecx,DWORD PTR [esi+0x18]
00833066: 51                    push ecx
00833067: 8b 4e 14              mov ecx,DWORD PTR [esi+0x14]
0083306a: 51                    push ecx
0083306b: 50                    push eax
0083306c: ff d2                 call edx

00833095: 8b 17                 mov edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea ecx,[esi+0x1f7c]
0083309d: 52                    push edx
0083309e: e8 1d b2 01 00        call 0x84e2c0
0084e2dd: 89 46 08              mov DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov DWORD PTR [esi+0x478],eax
```

## Appendix C — original neighboring slot evidence, not additional analysis

```text
.rdata VA 0x00B1BCA0: 20 FC 84 00 → 0x0084FC20  (adapter slot +0xF8)
.rdata VA 0x00B1BCA4: 40 FC 84 00 → 0x0084FC40  (adapter slot +0xFC)
```

No changes to files outside this Markdown report. No P2 files, renderer, runtime, PR, or guest state changes.
