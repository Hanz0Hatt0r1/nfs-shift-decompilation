# Process 1 — оригинальный SHIFT.exe под Wine: null pointer в indexed lookup 0x0083a006

**Дата:** 2026-10-21  
**Репозиторий:** `Hanz0Hatt0r1/nfs-shift-decompilation`  
**Ветка отчёта:** `work/process-reports`  
**Новый файл:** `process-reports/2026-10-21-process1-original-wine-apt-null-array.md`  
**Оригинальный образ:** `SHIFT.exe` PE32 x86 PC retail 1.02; SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Метод:** независимая проверка вставленного пользователем WineDbg evidence и **доступных GitHub evidence**. Локальный PE, Ghidra-проект, бинарные disassembly exports, процессы и логи вне GitHub не открывались. Runtime/renderer не менялись.

## 1. Executive finding и классификация

**Ближайший (immediate) blocker: подтверждённое нарушение инварианта инициализации/состояния используемого guest-объекта: null базовый указатель в `[inner+0x3c]` к моменту indexed read.** Инструкция оригинального PE по `0x0083a006` под Wine пытается прочитать `0x00000018`. Причина, почему указатель **не был заполнен до этого вызова**, для **данного оригинального Wine-исполнения** пока **не установлена**.

| Проверяемый класс причины | Вердикт по original Wine 11.17 |
| --- | --- |
| Данные / инициализация guest-объекта | **Подтверждён ближайший симптом:** поле `inner+0x3c` содержит `0`, затем используется как base без проверки. **Причина пропуска ожидаемой инициализации неизвестна.** |
| Win32 guest compatibility **recompiled runtime** | **Не непосредственный исполнитель этого Wine AV.** Отдельный v597 **доказывает для P-code replay** конкретный `D3DXCreateEffect` ASCII-input compatibility failure, но это не утверждение об API результате в оригинальном Wine запуске. |
| Wine / окружение | **Возможная upstream-причина, не доказана.** Оригинальный PE исполнялся под Wine 11.17; зависимости, результат D3DX effect, полнота данных и различия DLL надо сравнить в этом же прогоне. |
| Дефект retail x86 lookup-инструкции | **Не доказан.** Падение точно следует исходной арифметике адреса, но причина неправильного состояния и нативное Windows поведение неизвестны. |
| Статическая ошибка P-code трансляции | **Не объясняет этот оригинальный Wine fault:** fault исполнил original `SHIFT.exe`, не recompiled P-code. Совпадение low-memory адреса между независимыми путями подтверждает соответствие операции чтения, а не общую upstream-причину. |

**Итоговая дисциплина доказательств:** класс ближайшего отказа — **guest object initialization/state**; выбор из **Win32 compatibility / Wine environment / input data** для upstream **unresolved**. Не присваивать классу имя из названия GeckoFnl stack frames, соседних адресов или vtable pointer. Не заменять `0` каким-либо «правильным» адресом и не обходить fault.

## 2. Полный существенный evidence из запроса (original Wine)

### 2.1 Execution и границы

- **Исполнение:** нативный retail `SHIFT.exe` через **system Wine 11.17** на Linux x86_64, display `:1`. Это исполнение PE через Wine, **не recompiled P-code и не native Windows**.
- Retail PE и Bink загрузились; исполнение достигло **D3DX effect validation**. Это не устанавливает HRESULT именно интересующего `D3DXCreateEffect` и не подтверждает завершение effect/object initialization.
- Один Wine launch: `EXCEPTION_ACCESS_VIOLATION` `0xc0000005` при **read** по `EIP=0x0083a006`, fault address `0x00000018`; `EAX=0, ECX=0, EDX=0`. Frontend и race не подтверждены.
- SHA-256 non-debug Wine log: `a2367052d68569473e61b6202b5ab8dd8121422c43b95e8a0ca6633a52b7e102`.
- SHA-256 conditional debugger follow-up log: `11c9012acfb1f4e4b98f0bb4c660c765018bc444917c9888eb9cf17ebb8718f4`.
- Полные логи остаются **вне GitHub**; их хеши взяты из user evidence / сохранённой карточки, байты не проверялись заново.

### 2.2 Точный предоставленный x86 путь

~~~asm
0x0083a5c0: mov ecx, [ecx+0x50]
0x0083a5c3: jmp 0x0083a000
0x0083a000: mov ecx, [ecx+0x3c]
0x0083a003: lea eax, [edx+edx*8]
0x0083a006: mov eax, [ecx+eax*4+0x18]
0x0083a00a: ret
~~~

WineDbg GDB proxy остановил процесс **перед** faulting instruction по условному breakpoint:

~~~gdb
break *0x0083a006 if $ecx == 0
~~~

Caller: `0x0082c437: call eax`; return address `0x0082c439`.

Восстановленные слова stack:

~~~text
[ESP+0x00] = 0x0082c439
[ESP+0x04] = 0x0a916d70  // unresolved non-image return address
[ESP+0x08] = 0x0129fde4
[ESP+0x0c] = 0x00000002
~~~

В неполном символическом стеке встречаются GeckoFnl symbols `AptPrototype::GetSuperConstructor`, `AptValue::c_cih`, `AptCharacterTextInst::GetMaxScroll`, а также unresolved non-image addresses. **Это не подтверждённая цепочка C++ типов или точный layout указанного receiver.** Интерпретировать `0x0a916d70` как достоверный guest return site нельзя без unwind/code mapping.

### 2.3 Receiver / inner snapshot

| Сущность / поле | Значение |
| --- | --- |
| outer receiver | `0x0a686660` |
| предполагаемый vtable pointer, первое слово outer | `0x00b19e28` |
| адрес `outer+0x50` | `0x0a6866b0` |
| `[outer+0x50]` → inner | `0x0a686a20` |
| inner first DWORD | `0x00000000` |
| `[inner+0x20]` | `0x00000003` |
| **адрес `inner+0x3c`** | **`0x0a686a5c`** |
| **`[inner+0x3c]`** | **`0x00000000`** |
| guest `EDX` at stop | `0x00000000` |
| `ECX/EAX` at `0x0083a006` | `0x00000000` |
| faulting effective address | **`0x00000018`** |

**Не путать** `[outer+0x3c]` (также встречавшееся нулевым в прежнем частичном дампе) с фактически читаемым **`[inner+0x3c]`**. Lookup `0x0083a000` получает `ECX=inner` после thunk, затем переписывает `ECX` значением этого **inner** поля.

## 3. Точная минимальная x86 семантика и доказуемость

~~~text
ECX on thunk entry = 0x0a686660
ECX after [ECX+0x50] = 0x0a686a20
ECX after [ECX+0x3c] = 0x00000000
EAX after LEA = EDX*9 = 0
effective address at read = ECX + 4*EAX + 0x18
                          = 0 + 4*(9*0) + 0x18
                          = 0x00000018
~~~

В общем случае инструкция `0x0083a006` обращается по `base + 36*EDX + 0x18` (в 32-битной арифметике), где `base` берётся из `[inner+0x3c]`. Это **совместимо** с индексированным блоком 36-байтных элементов, но не устанавливает тип, число элементов, класс, владение или значение index. В показанном stop `EDX=0`, поэтому именно null base объясняет fault; `[inner+0x20]=3` не доказывает, что это длина массива или допустимый limit.

Инструкция `0x0083a5c3` — **JMP**, то есть переход thunk в lookup, не дополнительный вызов/стековая рамка. `RET` находится после faulting load и в данном пути не достигнут. Caller `call eax` — indirect, а его реально вычисленный target следует снять отдельно; один `return=0x0082c439` плюс observed thunk-путь подтверждают relevant chain, но не все incoming xrefs.

**Доказано:** fault не является лишь ошибкой диагностики P-code — оригинальный retail x86 код под Wine дошёл до чтения из `0x18`. **Не доказано:** наличие такого же null в native Windows, штатность значения inner+0x3c в общем случае, конкретная missing initializer branch для Wine, повреждение памяти, связь с scheduler, тип outer/inner, дефект exe либо виновность Wine DLL.

## 4. Дополнительные данные, независимо проверенные в GitHub

### 4.1 Original Wine evidence artifact

Сохранённая карточка [`evidence/retail_frontier_20261021/original_shift_wine_crash.json`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/original_shift_wine_crash.json) (Git blob `fbaccac1dadb5bc3c02522054a375b0f1e136a29`) повторяет SHA retail PE, exception `0xc0000005`, `EIP=0x0083a006`, read `0x18`, точные инструкции, guest stack, conditional breakpoint, receiver/inner snapshot, log SHA и ограничения. Это **сохранённый отчет наблюдения**, не raw Wine log.

### 4.2 P-code v594–v596 — оригинальный constructor *на другом guest instance*

GitHub [`process1_pcode_frontier_v594_v596.json`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/process1_pcode_frontier_v594_v596.json) (blob `255867dba4dac079f54b52218d053064fa29ba96`) сообщает:

- Retail constructor entry `0x00839f30`, reported callsite `0x0083dc65`.
- Точная отмеченная store-инструкция: **`0x00839f4c: mov [esi+0x3c], ebx`**, при `EBX=0`.
- В P-code v594, last-writer provenance: guest field `0x2429c48c` = `0x2429c450 + 0x3c`, writer `0x00839f30`, thread `0x000b088e`, dispatch **8,147,314**, value `0`. Этот store соответствует исходной retail-инструкции; поэтому null может быть **штатным конструкторным default** до последующего заполнения, а не несуществующим или случайным guest write.
- v595: constructor `0x00839f30`, return `0x0083dc6a`, `ECX=0x2429c450`; затем getter thunk `0x0083a5c0`, return `0x0082c439`, `ECX=0x2429c3c0`; оба наблюдения на одном guest TID `0x000b0f68`. **Этот trace не поддерживает конкретную гипотезу scheduler race**; не является глобальным доказательством её невозможности.
- v596: full copied retail game-data root, вновь read `0x18` (P-code), без устранения blocker. Это **один другой recompiled replay**, не доказательство достаточности того же game-data root для original Wine.

Важно: Wine `inner=0x0a686a20` и P-code `inner=0x2429c450` — **разные адреса/экземпляры и разные исполнения**. Нельзя утверждать, что Wine-instance был записан именно наблюдавшимся в v594 store или в том же порядке без его собственного watchpoint.

### 4.3 P-code v597 — более близкая upstream causal chain для **recompiled runtime**, но не для Wine

GitHub [`process1_pcode_frontier_v597_d3dx_ascii_effect.json`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/process1_pcode_frontier_v597_d3dx_ascii_effect.json) (blob `e1571932eee013fb7ff10e2dc9e66a7f961dbe18`) и [`docs/RETAIL_FRONTIER_AUTOMATION.md`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/docs/RETAIL_FRONTIER_AUTOMATION.md) описывают **уже исследованную** P-code зависимость:

| Поле | P-code v597 |
| --- | --- |
| guest caller / import | `0x0083dc50` → `d3dx9_41.dll!D3DXCreateEffect` |
| guest import return address | `0x0083dcac` |
| guest thread ID | `0x000b32ec` |
| dispatch | **8,107,451** |
| input | ASCII effect at `0x00b8e988`, **773 bytes**, checksum `9fa76844ab49cade593eb0fb7e81893dd679ad158c169c1522e012017c764917` |
| result | `HRESULT=0x80004005` (`E_FAIL`), effect output `0` |
| preceding constructor write | `0x00839f30` at dispatch 8,107,450; wrote `0` to `0x2429c48c` |
| observed guest branch | failure path **skipped `0x0083d470` / `0x0083d850`**, retaining `inner+0x3c==0` |
| next observed blocker | P-code RAM read `0x18` |

По сохранённому evidence существовавший recompiled adapter принимал только бинарные effects и возвращал `E_FAIL` для exact ASCII source. Эталонный 32-bit `D3DX9_41/D3DCompiler_41` обработал исходник и создал compiled effect 1140 bytes (параметр `worldViewProj`, техника `Default`, один pass). В репозитории описано последующее *точечное* исправление входного контракта именно этого текста; оно не означает поддержку произвольного ASCII эффекта.

**Критическая граница:** наличие «D3DX effect validation reached» в описанном original Wine launch НЕ сообщает, какой `HRESULT` вернул **тот же** `D3DXCreateEffect` для `0x00b8e988`, прошёл ли original Wine caller успешную ветвь `0x0083dc50`, произошла ли запись в его `inner+0x3c` и почему к `0x0083a006` поле нулевое. Реальное Wine поведение может зависеть от конкретной `d3dx9_41.dll`/compiler DLL и game data. **Не переносить `E_FAIL` из P-code в Wine как установленный факт.**

### 4.4 Другие original-game execution environments не служат контрольной Windows выборкой

[`original_shift_portproton_run.json`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/original_shift_portproton_run.json) описывает отдельный original retail `SHIFT.exe` под GE-Proton 11-5 в скопированных prefix/game root: процесс выполнял Gecko/Scaleform code ~480 s, окно оставалось чёрным; **ни crash на этом же адресе, ни frontend/race не подтверждены**. [`original_shift_live_wine_observation.json`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/original_shift_live_wine_observation.json) описывает read-only наблюдение уже живого Wine процесса (Bink/D3DX/WineD3D), которое не восстановило guest EIP. Эти прогоны отличаются от точного сбойного WineDbg launch и **не** позволяют присвоить причину по изменению среды; сравнение потребует одинакового входного сценария и прицельной трассы нужного поля.

## 5. Байт-код, Ghidra boundaries, writers/xrefs — доказательный предел

В доступных GitHub JSON есть **mnemonics и instruction addresses**, а также адреса `constructor store`, `constructor callsite`, `lookup thunk`, `indirect call site` и `D3DXCreateEffect` caller. **Не найдено** полного authoritative byte dump instruction ranges `0x00839f30–...`, `0x0083dc50–...`, `0x0083a000–...` или `0x0083a5c0–...`, полных `getFunctionAt/getFunctionContaining` boundaries, полных `getReferencesTo` lists и полного списка indirect call targets в оригинальном PE. Следовательно, **не заявлять verified instruction bytes, exact function extents или exhaustiveness xrefs/writers**.

Фактически доступные candidate refs / transfers:

| Источник | Связь | Уровень evidence |
| --- | --- | --- |
| `0x0082c437` | `call eax` → observed `0x0083a5c0` thunk, return `0x0082c439` | WineDbg instruction + observed call path; resolved target at callsite should be logged explicitly |
| `0x0083a5c0` | `mov ecx, [ecx+0x50]`; `0x0083a5c3` → `jmp 0x0083a000` | WineDbg static instruction text |
| `0x0083a000` | load `[inner+0x3c]`, index scale 36, load at `0x0083a006` | WineDbg static instruction text + register snapshot |
| `0x0083dc65` | constructor `0x00839f30`, return `0x0083dc6a` | separate recompiled v594/v595 evidence; **not original Wine xref independently revalidated** |
| `0x00839f4c` | initial zero store `[esi+0x3c]` | separate v594 P-code write provenance with original-instruction label |
| `0x0083dc50` | call `D3DXCreateEffect`, return `0x0083dcac` | separate v597 P-code trace; **not original Wine outcome** |
| `0x0083d470` / `0x0083d850` | skipped initialization helpers after `E_FAIL` | separate v597 causal interpretation; exact bodies/writers not present |

**Ghidra минимальный read-only запрос (в отдельном исследовании):** от original pinned PE выгрузить байты, disassembly, p-code, function entry/end и body ranges вокруг всех этих sites, direct `getReferencesTo` для `0x00839f30`, `0x0083a000`, `0x0083a5c0`, `0x0083dc50`, `0x0083d470`, `0x0083d850`, а также incoming xrefs для `call eax` через dataflow в `0x0082c437`. Для **writers поля `inner+0x3c`** нужен **offset-aware def-use/dataflow по объекту**, в том числе stores through aliases, helper calls, memcpy/array initializers: обычный xref к абсолютному адресу `0x3c` не идентифицирует все записи в динамический объект. Проверять register provenance и CFG success/fail у `D3DXCreateEffect`; не присваивать тип из соседних символов.

## 6. Наименьший решающий original Wine runtime probe (без изменения семантики)

**Один контролируемый повтор того же PE под system Wine 11.17**, с read-only conditional breakpoints и **hardware write watchpoint** на найденный field адрес конкретного **этого** объекта. Сохранять guest thread ID, `EIP`, `ESP/EBP`, `EAX/ECX/EDX/EBX/ESI`, `EFLAGS`, caller/return, хронологию, сырой HRESULT и идентификатор исходного game data/DLL.

1. **В момент создания inner:** на `0x00839f30` / `0x00839f4c` проверить фактический `ESI`, `EBX`, stack/return адрес (ожидаемый static кандидат `0x0083dc65`). Зафиксировать `inner` адрес, old/new `[ESI+0x3c]` и факт store. Поставить **hardware watchpoint на `*(uint32_t*)(inner+0x3c)`** (если instance известен; не использовать прежний адрес в новом ASLR/heap execution). Зафиксировать каждый последующий writer `EIP/TID/old/new` до getter; если null уже при создании и других writers нет, это докажет отсутствие population для данного экземпляра. Если оказалось, что Wine inner был создан другим способом, не приписывать ему `0x00839f4c`.
2. **Непосредственно вокруг `0x0083dc50` и возврата `0x0083dcac`:** снять аргументы `D3DXCreateEffect` из реального guest **stack ABI**, source pointer/size/hash (проверить кандидат `0x00b8e988`/773 bytes), device, out effect pointer и `HRESULT`. При необходимости `ID3DXBuffer` с compiler errors, конкретные guest loaded `d3dx9_41.dll` и `d3dcompiler_41.dll` версии/хеши. Записать фактически выбранную guest ветку успеха/ошибки и вызовы `0x0083d470`/`0x0083d850`; не выводить API аргумент из volatile `EDX`. Снять записанные output pointers и writer trace field после возврата.
3. **На `0x0083a5c0` / `0x0082c437` / `0x0083a006`:** зафиксировать actual `call eax` target, outer receiver, `[outer+0x50]`, resolved inner, `[inner+0x3c]`, `EDX`, expected effective address, caller return `0x0082c439` и `ESP`. Сопоставить `inner` с watchpoint-instance; при несовпадении — искать другой allocator/constructor, а не переносить writer trace с чужого объекта.

**Достаточная причинная цепочка для классификации по Wine:** `same inner instance` → (constructor default zero) → (точный `D3DXCreateEffect` return) → (branch to/away from initializer helpers; их фактические writes) → (последний writer или отсутствие population) → (`0x0083a006` null read). Если `D3DXCreateEffect` также вернул `E_FAIL` и был пропущен доказанный writer, можно повысить **Wine/D3DX environment compatibility** до непосредственной upstream-причины. Если effect успешно создан, искать alternative initialization/data/alias writes вместо обвинения D3DX. Само по себе `E_FAIL` ещё недостаточно без branch-to-writer связи.

**Минимальное независимое сравнение:** повторить такую же наблюдательную трассу с тем же original PE, game data, точной source 773 bytes и одинаковым trigger в другой Wine/D3DX конфигурации или, при доступности, native Windows. Сравнить результаты API и переходы/записи; black window/общие «запускался 8 минут» не равно положительному controls.

## 7. Безопасный ближайший шаг Process 1

**Рекомендация:** получить guest call/return `D3DXCreateEffect` и lifetime watchpoint `inner+0x3c` для **того же original Wine process**. Исследовать соответствующие статические Ghidra CFG/writers при наличии original bytes и исходников. Не исправлять нуль фиктивным указателем, не замещать getter, не перескакивать branch, не называть тип структуры по GeckoFnl symbols и не менять runtime/renderer без нового фактического evidence.

**Ограничения финального вывода:** имеющиеся Github материалы объясняют P-code v597 через D3DX ASCII effect compatibility failure и показывают, что retail constructor имеет default-zero store, но не содержат Wine-вызова `D3DXCreateEffect` и writer history именно Wine inner `0x0a686a20`. Именно этот недостающий мост отделяет зафиксированный downstream AV от причинной классификации Wine/окружения, data issue или иной startup branch.

**Статус:** `immediate_guest_object_state_fault_confirmed; original_Wine_upstream_cause_unresolved`. Единственный документ отчёта добавлен в ветку `work/process-reports`; никакой код runtime/renderer не менялся.
