# Process 1 — независимый аудит гипотезы об аудиоблокере retail runtime

**Дата:** 2026-10-21  
**Репозиторий:** `Hanz0Hatt0r1/nfs-shift-decompilation`  
**Отчётная ветка:** `work/process-reports`  
**Файл:** `process-reports/2026-10-21-process1-audio-runtime-audit.md`  
**Исходный PE:** `SHIFT.exe`, PC retail 1.02, PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`  
**Статус после v667:** **v520: plausible but unproven**; **bounded v667 host-frame path: отсутствие выбранных аудиоимпортов в live trace, audio compatibility не объясняет этот наблюдаемый путь**.  
**Ограничения:** исключительно предоставленный пользователем evidence и файлы GitHub. Локальный диск, процесс, исходный PE и Ghidra-проект не открывались. Ни runtime, ни renderer не изменялись. Файл отчёта — единственное запрошенное изменение.

## 1. Постановка и краткий вердикт

Вопрос: может ли неполная эмуляция оригинальных WinMM/DirectSound API объяснить наблюдение v520, при котором `ResumeThread` завершился успешно, но в наблюдаемом guest-объекте **worker/predicate bit 2** не был установлен?

**Для отдельного наблюдения v520 аудио остаётся возможной, но недоказанной причинной цепью.** Неподдержанный непосредственный PE import приводит к ошибке dispatch; отсутствующий динамический аудиосимвол может разрешиться в ноль, а `LoadLibraryA` — вернуть NULL/126. Но нет связанных друг с другом наблюдений вызова аудио API, использования результата/обратного вызова и writer/reader worker bit 2.

**Новый bounded v667 меняет оценку другого, конкретно измеренного пути:** 360 host frames завершились `host-frame-loop` без blocker; в live trace **нет выбранных WinMM/MSACM32 вызовов**, аудио-загрузок и audio-related `GetProcAddress` queries. Следовательно, отсутствие их реализации **не объясняет достигнутый v667 host-frame путь**. Это не доказывает запуск retail gameplay, полноценный рендеринг или отсутствие аудиозависимости в иным образом устроенном v520 predicate frontier (подробности в §9).

Статус `confirmed blocker` для v520 недостижим из этих данных. Глобальный `ruled out by evidence` для v520 тоже был бы неверным.

## 2. Полный релевантный runtime evidence (из задачи)

1. В `native_runtime/src/recompiled_pcode_module.cpp` обработаны:

~~~cpp
if (name == "WINMM.dll!timeBeginPeriod") return time_begin_period();
if (name == "WINMM.dll!timeEndPeriod") return time_end_period();
if (name == "WINMM.dll!timeGetTime") return time_get_time();
if (name == "DINPUT8.dll!DirectInput8Create") return direct_input8_create();
~~~

Нет явных обработчиков `waveOutOpen`, `waveInOpen`, `timeSetEvent` или методов DirectSound.

2. `GetProcAddress` ищет точное совпадение имени среди `import_traps`; если нет, динамический stub создаётся только для `kernel32.dll` и имени из `is_supported_kernel32_api`. `LoadLibraryA` успешен только для модуля из `guest PE import module map`; иначе NULL и last error 126.

3. Репозиторий содержит статический audit `tools/ghidra/analyze_p1b_hdvehicle_4330_winmm_callback_surface.py`. Ожидаемые retail callsites, включая **адрес инструкции** и **адрес содержащей функции**:

| API | Содержащая функция → инструкция вызова |
| --- | --- |
| `waveOutOpen` | `0x006135a0 → 0x006135ee`; `0x00999129 → 0x009991f6`; `0x00999b73 → 0x00999c69` |
| `waveInOpen` | `0x00613350 → 0x0061339e`; `0x009995ee → 0x00999714` |
| `timeSetEvent` | `0x009a8db7 → 0x009a8e7d` |

Ненулевые callback entry points: `waveInOpen` → `0x0099955b` (callsite `0x00999714`, `CALLBACK_FUNCTION` / `0x30000`); `timeSetEvent` → `0x009a8d8f` (callsite `0x009a8e7d`). Все три `waveOutOpen` callsites и простой `waveInOpen` callsite передают NULL callback. Этот audit привязан к хешам Ghidra SQLite/source, **не доказывает фактическую достижимость этих callsites в текущем startup replay**. По audit callback targets не входят в exact 15-function `HDVehicle+0x4330` carrier set; это НЕ исключает иные маршруты управления worker.

4. Оригинальный PC retail 1.02 PE имеет SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

5. **v520:** `ResumeThread` вернул успех; worker/predicate bit 2 в наблюдаемом объекте не был установлен. **Причинность аудио не установлена.** Адрес слова/объекта и точная writer/reader chain в текущем сообщении отсутствуют.

6. **v662:** replay остановился на `unsupported D3D9 managed texture description` после **42,542,707 dispatches**. Это конкретный graphics-side blocker отдельного запуска, а не доказательство audio/worker causality.

7. **v665:** DXT3 capture adapter, 1440 requested frames, 900 секунд, без call-trace env; процесс завершился timeout (`exit 124`), `PE loaded=true`, но usable frontier counters не получены и DXT3 capture directory пуст. Никаких причинных заключений о звуке или успешном game startup это не поддерживает.

8. **v666 (на момент постановки задачи ещё выполнялся):** повторный 1440/900-секундный guest replay с тем же retail PE/game data/module manifest и P2 capture adapter; getter trace адресов `0x005a0ef0, 0x005ab230, 0x005ab3f0, 0x005a0ec0, 0x005a0ed0, 0x005a0ee0`; за первую минуту около 2.7M P-code dispatch. **Эти targets — getters, не аудио.** Количество dispatch не свидетельствует о начале игрового процесса; незавершённый v666 не даёт результата по аудио.

Данные v520, v662, v665, v666 принадлежат разным прогонам. Их нельзя соединять в одну сквозную причинную трассу без совпадения бинарника, manifest, input и хронологии каждого запуска.

## 3. Прямая проверка доступного GitHub-кода

Проверен именно GitHub-файл ветки `work/retail-runtime-d3d9-capture`:  
[`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp), blob SHA `39a68ec4ecc4456eadcd5bdfdd4058d73b5cf42f`.

Также прочитаны [WinMM audit script](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/tools/ghidra/analyze_p1b_hdvehicle_4330_winmm_callback_surface.py) (blob `c9cb811c2f7d82447bdca0b3430b866527ca11eb`), [audit contract](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/docs/PROCESS_1B_HDVEHICLE_4330_WINMM_CALLBACK_SURFACE.md) (blob `a6b7fa0bc555f796cc12d5c0dcd7a4b626c275a7`) и [result JSON](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/p1b_hdvehicle_4330_winmm_callback_surface.json) (blob `4878bd5ebbfdeee9b43b1f075bbd92f0efb65404`). Ни Ghidra SQLite, ни original-source input этих артефактов заново не выполнялись/не сверялись.

### 3.1 Direct/import-trap dispatch: fail hard, а не silent success

В `Impl::dispatch` входящий target проверяется по `import_id_traps`, затем `import_traps` (около строк 1622–1646). Доступные WinMM handlers — только три `time*` API выше (строки 1692–1697). После перечисленных обработчиков (около строки 2223) исполнение попадает в:

~~~cpp
error = "unimplemented PE import " + imported->second;
// diagnostics: last LoadLibraryA, active caller,
// guest return address and stack words
return -1;
~~~

Следовательно, **если** `WINMM.dll!waveOutOpen`, `WINMM.dll!waveInOpen`, `WINMM.dll!timeSetEvent` либо `DSOUND.dll!…` присутствует как import trap **и этот trap реально вызван**, этот runtime не возвращает правдоподобный `MMRESULT`/timer ID и не вызывает guest callback: он устанавливает диагностическую ошибку и возвращает `-1` в host dispatcher. Эта ошибка **не** означает, что WinMM API вернул `MMSYSERR_ERROR` гостю; завершение не является гостевой семантикой WinMM. Для неизвестного не-import P-code target путь `resolve()` также может завершиться `-1` (около строк 2327–2351), но это другой механизм, который нельзя приписывать всем COM/vtable-вызовам без их target evidence.

**Не установлено:** действительно ли эти WinMM/DSOUND имена присутствуют в **импортной таблице именно загруженного retail PE**. Загрузка PE строит `imported_thunks` и `import_traps` из import descriptors (около строк 14924–15103), но фактический список импортов оригинального EXE здесь не предоставлен. Статический callsite audit не равен полному PE-import inventory.

### 3.2 `LoadLibraryA`: явно возвращает NULL / 126

`load_library_a()` (строки 12610–12640) нормализует имя модуля, ищет `guest_module_handles` и при отсутствии вызывает:

~~~cpp
guest_last_error = 126;
guest_last_load_library_error = guest_last_error;
return return_kernel32_dword(0, api, 4);
~~~

При совпадении возвращает mapped handle и сбрасывает `guest_last_error` в 0. На NULL pointer имени выставляет 87. Реальное существование DLL в host filesystem не является критерием поддержки этого guest API; речь о guest PE map.

### 3.3 `GetProcAddress`: несуществующий audio symbol → 0; важное отличие last-error

`get_proc_address()` (строки 13193–13239) получает module handle и символ/ordinal, сопоставляет имя модуля и **точное** имя/ordinal `import_traps`; только для `kernel32.dll` и разрешённого API создаёт новый динамический import trap. Без совпадения `procedure_address` остаётся 0, записывается в guest `EAX`, выполняется `finish_stdcall(8, api)`.

**Важно:** в этой ветке **не выставляется `guest_last_error = 127`** или иное новое значение при неуспешном разрешении символа. Следовательно, `GetLastError` после такого NULL может вернуть **старую** ошибку, и его нельзя трактовать как достоверный marker «symbol not found». Ошибка `GetProcAddress` в этом runtime не равнозначна «unimplemented PE import»: непосредственный вызов отсутствующего dynamic symbol может вообще не состояться, если guest код проверяет NULL.

Если symbol был найден в `import_traps`, `GetProcAddress` возвращает **ненулевой trap address даже при отсутствии реализации**; последующий вызов этого trap падает через `unimplemented PE import`. Таким образом, одно наличие ненулевого указателя на API не означает поддержку функции.

### 3.4 WinMM time* поддержаны частично; не путать с аудиокодеком

В исходнике:
- `timeBeginPeriod(period)` принимает **только 1 мс** (`kGuestTimerPeriodMs = 1`): возвращает `TIMERR_NOERROR=0` и учитывает reference count; другой period возвращает `TIMERR_NOCANDO=97` (строки 199–201, 3693–3706).
- `timeEndPeriod(period)` успешен для существующего request, иначе 97 (строки 3709–3720).
- `timeGetTime()` возвращает `monotonic_tick_milliseconds()` (строки 3722–3725).

Этот отдельный timer compatibility contract может влиять на startup timing, **только если** соответствующие запросы реально вызываются и используются. Он не эквивалентен реализации `timeSetEvent`, асинхронной доставки timer callbacks или WinMM waveform audio.

### 3.5 DirectSound — условная граница, не доказанная runtime цепочка

В проверенном C++ не найдено явных `DirectSound`/`waveOutOpen`/`waveInOpen`/`timeSetEvent` handlers. Однако **нельзя** утверждать, какой конкретно путь использует retail startup для DirectSound: direct PE import, динамический `GetProcAddress`, COM/vtable, внутриигровой FMOD wrapper, другой модуль или вовсе отсутствие DirectSound-вызова до worker frontier. При прямом разрешённом PE import без handler действует `unimplemented PE import`; при неизвестном динамическом имени — `EAX=0`; при неизвестном COM/callback target нужен конкретный target и результат `resolve`. Нельзя назначать общую семантику «silent stub» DirectSound без подтверждённого import/target. В рамках перечисленных аудио-имен **не выявлено silent success handler**.

## 4. WinMM callsite/xref audit и ограничения его доказательной силы

`analyze_p1b_hdvehicle_4330_winmm_callback_surface.py` содержит `EXPECTED` с шестью **физическими** инструкциями вызова, сверяемыми по pin-значениям Ghidra SQLite/source. Source fragment проверки приводит следующий существенный код:

~~~c
waveInOpen(&local_18,param_2,&local_14,0,0,0);
waveOutOpen(&local_18,param_2,&local_14,0,0,0);
waveOutOpen(&local_8,param_1,&local_30,0,0,0);
waveOutOpen((LPHWAVEOUT)((int)this + 0x288),param_1,&local_2c,0,0,0);
waveInOpen(phwi,*(UINT *)(param_3 + 0xc),&WStack_2c,0x99955b,param_1,0x30000);
fptc = &fptc_009a8d8f;
timeSetEvent((UINT)uVar5,uResolution,fptc,dwUser,fuEvent);
~~~

Декомпилятор дублирует представление одного FMOD `waveInOpen` path из-за stack recovery; authority для числа физических вызовов — SQLite inventory с **одним** callsite `0x00999714`. Json `ready=true` означает успешность **ограниченного статического аудита**, а не прохождение runtime startup. Script pins отдельные `ghidra_sqlite_sha256=ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e` и `shift_exe_c_sha256=512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9` — **это хеши статических артефактов, а не SHA оригинального PE, заданный выше**.

Статически подтверждаются потенциальные вызовы и адреса регистраций callback, но **не** их время выполнения, ветка приложения, успешность `waveInOpen`/`timeSetEvent`, вызов callback в replay, связь с worker object или кросс-поточный порядок. Отсутствие прямого совпадения двух WinMM callback entrypoints с `HDVehicle+0x4330` carriers не означает отсутствие косвенного влияния аудио на иной worker bit 2.

## 5. Проверка предположения «успех ResumeThread ⇒ worker должен установить bit 2»

`resume_thread()` (строки 5130–5151) читает handle, возвращает `UINT32_MAX`/last-error 6 только для неизвестного handle, иначе уменьшает `suspend_count` при ненулевом значении и возвращает **предыдущий suspend count**; при zero count и незавершённом thread вызывает `run_guest_thread` для ещё не запущенного worker и/или `enqueue_guest_thread` по условиям scheduler.

`run_guest_thread()` (около строк 5020–5052) может запускать гостевой worker **синхронно** при неактивной guest coroutine либо подготовить его и поставить в очередь при активной. Синхронный/асинхронный путь, состояние `started/completed/runnable/waiting`, guest EIP и guest return code важны. **Успешный `ResumeThread` не является доказательством, что worker уже исполнил инструкцию, устанавливающую бит 2.**

`WaitForSingleObject`/`WaitForSingleObjectEx` (около строк 5322–5424) опираются на `wait_guest_object`: возможны `WAIT_OBJECT_0=0`, `WAIT_TIMEOUT=0x102`, `WAIT_FAILED=0xFFFFFFFF`; для alertable path — `WAIT_IO_COMPLETION=0xC0`. При определённых scheduler-context условиях бесконечное ожидание может вернуть failure `50`, а конечное — immediate timeout; это **самостоятельная область проверки**, не доказательство проблемы аудио.

Неизвестны адрес и type observed object, инструкция writer бита 2 (маска `0x4`), инструкция чтения predicate и wait/event dependency. Отсутствие бита само по себе совместимо с неполным worker scheduling, ожиданием внешнего callback, ошибкой import, неисполняемой веткой, graphics blocking либо нормальным ещё не наступившим milestone.

## 6. Минимальный P1 diagnostic probe для доказательства/исключения аудиопричинности

**Цель:** один bounded read-only trace с уникальным ordered event ID, guest thread ID, guest function/guest callsite EIP (либо return address с вычисленным callsite), guest ESP, несколькими stack DWORD arguments, raw API return, last error, guest object bit 2 value до/после и writer provenance. Не подменять результат аудио-API, не запускать фиктивный timer, не вызывать callback самостоятельно.

| Точка/имя | Снять как минимум | Разрешающий вопрос |
| --- | --- | --- |
| `WINMM.dll!waveOutOpen`: инструкция `0x006135ee`/`0x009991f6`/`0x00999c69` | entry EIP/return PC, thread ID, 6 аргументов (`lphwo, deviceID, format*, dwCallback, dwInstance, fdwOpen`), decoder route/import-trap, MMRESULT, выходной `HWAVEOUT`, guest last-error если применяется | Вызывается ли именно эта registration до gate worker и чем она закончилась? |
| `WINMM.dll!waveInOpen`: `0x0061339e`/`0x00999714` | те же 6 аргументов, включая `dwCallback`, `fdwOpen`; MMRESULT и выходной `HWAVEIN`; проверять фактический `0x0099955b` / `0x30000` | Была ли callback registration успешной и было ли ожидание callback? |
| `WINMM.dll!timeSetEvent`: `0x009a8e7d` | `uDelay, uResolution, fptc, dwUser, fuEvent`, thread ID, return timer ID (`0` означает отказ), callback pointer `0x009a8d8f`, лог фактического callback EIP/параметров | Планировался ли timer и был ли callback реально доставлен? |
| `WINMM.dll!timeBeginPeriod` / `timeEndPeriod` / `timeGetTime` | period/result, при необходимости timeGetTime return, callsite, guest TID | Не отказал ли таймерный запрос с 97, либо не возникла ли зависимость от времени? |
| `KERNEL32.dll!LoadLibraryA` / `GetModuleHandleA` / `GetProcAddress` / `GetLastError` | requested module string/normalized name, handle, symbol/ordinal, resolved trap pointer, return, last-error before/after, PC | Отсутствие DLL, NULL dynamic API, или ненулевой but unimplemented trap? Не принимать stale `GetLastError` после GetProcAddress за новый код ошибки |
| `DSOUND.dll` / `DirectSound*` **только если увидены в реальном import/dynamic target trace** | точное module/API/ordinal/vtable target, CALL PC, params, return HRESULT, guest thread | Есть ли вообще DirectSound на пути, и как конкретно до него дошли? Не выдумывать import list |
| `KERNEL32.dll!CreateThread` / `ResumeThread` / `GetExitCodeThread` / `ExitThread` | start EIP, handle, guest TID, flags, suspend count до/после, result `ResumeThread` (previous count), scheduler mode, started/runnable/waiting/completed, worker first EIP/exit code | Был ли worker фактически исполнен после `ResumeThread`? |
| `KERNEL32.dll!CreateEventA/W` / `SetEvent` / `ResetEvent` / `WaitForSingleObject(Ex)` и реально используемые synchronization APIs | handle identity, waiter/signaler TIDs, wait timeout/alertable/result, signal transitions, callsite/EIP, guest-stack args | Какое условие удерживает worker или predicate consumer? |
| **Observed worker/predicate bit 2** | фактический address слова и owning observed object (не угадывать тип), значение `old/new` и `old & 0x4`/`new & 0x4`, every write PC/TID/caller/ESP, every decisive reader/branch PC, last-writer provenance | Существует ли causal edge от audio return/callback → producer/writer → bit 2, или worker никогда не дошёл до writer? |

Дополнительно уместно записывать исход `dispatch` для каждого audio import: `matched import trap` / `GetProcAddress NULL` / `unimplemented PE import -1` / `unknown target`; guest state перед аварийным возвратом. Не смешивать host dispatcher `return -1` с guest `MMRESULT` или `HRESULT`.

**Минимально достаточная причинная трасса:** `ResumeThread(handle)` → worker реально начинает исполняться → достигнут WinMM/DirectSound callsite (или зависимый вызов к получению API) → зафиксирован конкретный fail/result/callback outcome → установлена последующая ветка или wait по этому результату → идентифицирован точный writer/expected signal бита 2, который не наступил вследствие этого исхода. Если audio API до момента freeze/gate не вызывается, гипотеза об отсутствии *его handler в этом временном префиксе* не объясняет frontier (за исключением другой, доказанной зависимости от аудиосостояния).

### Отделение от graphics/host frame pacing без изменения семантики

**Один способ:** в *том же* replay сделать единую упорядоченную временную шкалу `ResumeThread`/worker instruction and waits, audio import calls/results/callbacks, write/read predicate bit 2, **первого** `D3D9`/Present/texture/capture отказа и host frame-pacing/yield markers. Каждое событие снабдить monotonic host time, guest TID и counter только как индекс (не как доказательство игрового кадра). Проверить, происходит ли decisive worker gate *до* первого graphics-side stop или pacing wait и имеет ли он непосредственную dependence на audio result. Если истинное ожидание связано с host frame scheduler, а audio API не достигался, не классифицировать проблему как audio. Одна лишь временная последовательность «audio error раньше bit 2» **недостаточна** без последующего consumer/branch/producer edge.

## 7. Безопасный следующий шаг P1

1. **Сначала наблюдение:** добавить или включить только ограниченную диагностику, не меняющую значения guest registers/stack, условные ветки, callback delivery или время вызова: имена import/API, return status, guest callsite/EIP/ESP, callback pointers, TIDs, wait results и read/write provenance конкретного predicate word.
2. Если повторный replay реально достигает отсутствующего API, проверить конкретную фактическую сигнатуру/ABI, args и dependency on its return. Только тогда планировать **минимальную корректную** совместимость именно подтверждённого API с реальными output handles, ошибками, lifetime, timer scheduling и callback semantics, при необходимости независимо от рендерера.
3. **Не** возвращать всегда-success `waveOutOpen`/`waveInOpen`, не фабриковать успешный `timeSetEvent` без его timer/callback, не выставлять bit 2 напрямую, не подавлять вызов и не пропускать audio gate: всё это скрывает либо создаёт ложную причинность.

## 8. Что доказано, чего не хватает и финальный статус

**Доказано из GitHub runtime:** текущие три `time*` handlers; в отсутствие конкретного handler import-trap завершается `unimplemented PE import` и host return -1; `GetProcAddress` по неподдержанному имени без import trap возвращает 0 **без установки новой last-error**; `LoadLibraryA` для неизвестного guest module возвращает NULL/126; `ResumeThread` возвращает previous suspend count и не гарантирует исполнения worker до write bit 2.

**Подтверждено как ограниченный статический audit:** шесть callsites для `waveOutOpen`/`waveInOpen`/`timeSetEvent`, два ненулевых callback pointers, четыре NULL callback registrations; не достижимость в данном replay.

**Недоступно и не выдумано:** фактическая PE import table и DSOUND imports/exports, реальный исход любого аудиовызова v520/v662/v665/v666, writer/readers бита 2, классы/типы по адресам, guest callbacks/timer firing, точная причина timeout v665, финальный исход v666.

**Исторический вердикт до v667: `plausible but unproven` по v520.** Для нового bounded v667 это уточнено §9 ниже: отсутствующие наблюдаемые аудиовызовы не являются установленной преградой его host-frame пути. Предыдущие главы сохраняют первоначальный evidence и ограниченный вывод своего времени.

## 9. Дополнение: независимое runtime evidence v667 (полный предоставленный результат)

**Происхождение:** сведения о выполнении/trace v667 предоставлены пользователем; в этой редакции не выполнялся replay, не открывались локальные логи и не проверялся указанный SHA содержимого лога. Предыдущий статический обзор GitHub остаётся отдельной проверкой кода. Это **recompiled guest P-code runtime с оригинальным retail PE**, **не** нативный Windows процесс `SHIFT.exe`.

### 9.1 Provenance и bounded outcome

| Поле | v667 |
| --- | --- |
| Оригинальный PE | SHIFT.exe PC retail 1.02, PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` |
| P1 production source | `e6f674a6` |
| P2 DXT3 capture adapter | `1fef18a8` |
| Game data | `pcode-game-data-v661` |
| Module manifest | реконструирован из evidence v659 |
| Probe | **360 requested frames**, **420 s timeout**, **live import call trace** |
| Exit | **0** |
| Status / blocker | `status=host-frame-loop` / `blocker=null` |
| Host frame result | **360 rendered host frames** |
| P-code dispatches | **1,736,499** |
| Unique functions | **4,728** |
| Main thread function | `0x00832160` |
| Worker waiting | `worker_waiting_count=5` |
| Validation errors | **0** |
| Probe log SHA-256 | `da5cde6b0bdbddf2649b4bec339141098d36a103cbe077669cad2190a28be3ed` |

**D3D9 bridge:** **1,110 clear requests / 360 submissions**, **1,108 present requests / 360 submissions**, **748 pending presents**; `guest_draw_translation=false`, `retail_rendering_proven=false`.

Следовательно, `exit=0` и 360 host frames **подтверждают прохождение именно ограниченного host-frame-loop в recompiled runtime**, а не доказанную реализацию графики/guest draw, обычный native retail Windows запуск или полноценный игровой прогресс. Число dispatches и unique functions — показатели выполнения P-code, **не** доказательство игрового запуска. Пять ожидающих workers не отождествляются без trace с тем worker/predicate bit 2, который наблюдался в v520.

### 9.2 Полная selection import trace (32 имени) и фактические наблюдения

В live import trace были выбраны 32 API (имена ниже сохранены в том виде, в котором они даны для selection; unqualified suffixes продолжают предшествующий указанный модуль внутри списка):

~~~text
WINMM.dll!waveOutOpen
waveOutClose
waveOutWrite
waveOutReset
waveOutPrepareHeader
waveOutUnprepareHeader
waveOutGetPosition
waveOutGetNumDevs
waveOutGetDevCapsA
waveOutSetVolume
waveInOpen
waveInClose
waveInStart
waveInStop
waveInReset
waveInAddBuffer
waveInPrepareHeader
waveInUnprepareHeader
waveInGetPosition
waveInGetNumDevs
timeSetEvent
timeKillEvent
mciSendCommandA
MSACM32.dll!acmStreamOpen
acmStreamUnprepareHeader
acmFormatSuggest
acmStreamSize
acmStreamPrepareHeader
acmStreamConvert
KERNEL32.dll!LoadLibraryA
GetProcAddress
FreeLibrary
~~~

**Наблюдения v667:** ни одного выбранного вызова `WINMM.dll!` или `MSACM32.dll!` не записано. Два записанных вызова `LoadLibraryA` запрашивали **`kernel32.dll`** и **`nvapi.dll`**; запросов загрузки DirectSound/WinMM/MSACM-модулей и audio-related `GetProcAddress` не было. Диагностического `unimplemented PE import` не зафиксировано. Отсутствуют свидетельства исполнения выбранных audio callsites на этом ограниченном пути.

**Граница отрицательного результата:** это не утверждение о *всех* API, динамических вызовах, непросмотренных `timeBeginPeriod`/`timeGetTime` или COM/vtable-инструкциях; селекция ограничена перечисленными именами и конкретным интервалом до 360 host frames. Отсутствие записи в выбранном import trace не доказывает, что весь аудиодвижок не работал или что никогда не будет вызвано аудио API. Не следует задним числом приписывать этот результат v520 либо другим версиям.

### 9.3 Обновлённая причинная оценка v667 против v520

| Гипотеза/вывод | После v667 | Причина |
| --- | --- | --- |
| Нереализованный выбранный WinMM/MSACM импорт блокирует **bounded v667 host-frame path** | **Не объясняет наблюдаемый путь** | Прогон вышел с кодом 0 и `blocker=null`; ни одного выбранного аудиовызова/`unimplemented PE import` в live trace |
| Аудио через неизвестный, не выбранный route никогда не понадобится | **Не доказано** | Live trace ограничен 32 именами и 360 host frames; DirectSound/COM и неперечисленные timing APIs не покрываются данным отрицанием |
| v667 доказал retail gameplay/rendering | **Нет** | `guest_draw_translation=false`, `retail_rendering_proven=false`, pending presents 748; речь о host-frame loop |
| Отсутствие аудио-семантики вызвало **v520 bit 2 не установлен** | **Plausible but unproven** | v667 не воспроизводил точные predicate reader/writer, worker causal chain и execution state v520 |
| Аудиопричинность v520 исключена | **Нет** | Нельзя переносить отсутствие выбранных вызовов из v667 в отдельный v520 frontier |
| v667 доказывает отсутствие scheduler/worker проблемы | **Нет** | `worker_waiting_count=5` — агрегат; нет correlation к конкретным handle, wait result, predicate bit 2 |

**Актуальный вердикт для исходного вопроса о v520 — `plausible but unproven`.** Вместе с тем **неполная audio compatibility больше не является объяснением конкретно достигнутого bounded v667 host-frame path**, поскольку соответствующие выбранные audio imports там не вызывались, а явного unsupported import blocker не обнаружено. Эти две формулировки не противоречат друг другу: разные probes проверяют разные frontier и причинные связи.

### 9.4 Самый узкий следующий P1 probe

Без изменения guest audio/timer/callback семантики сделать **в одном воспроизводимом прогоне вокруг v520 frontier** коррелированный, read-only trace:

1. `ResumeThread`: вызывающий guest PC, handle, guest thread ID, previous/new suspend count, mode synchronous/enqueued, first scheduled guest EIP и status worker (`started/runnable/waiting/completed`).
2. Target worker: wait callsite/EIP/ESP, event handle, `WaitForSingleObject(Ex)` timeout/alertable/result, `SetEvent` source TID и состояние `signaled`; если relevant — отдельные audio `LoadLibraryA/GetProcAddress`, selected WinMM/MSACM и observed DSOUND/COM targets с args/returns/callback addresses.
3. **Конкретный адрес predicate word**: снимки значения маски `0x4` до ResumeThread, при входе worker, до/после event/wait, на каждом фактическом writer, при decisive reader/branch; writer EIP, TID, old/new, last-writer provenance.

Сопоставить эти точки с первым graphics/present/host pacing yield **в том же прогоне**. Только установленная цепь `audio result → branch/wait/callback → конкретный predicate writer` может повысить v520 до `confirmed blocker`. Пока такая связь не представлена, не менять runtime audio API и не моделировать `waveInOpen/timeSetEvent` фиктивным успехом.

**Update scope:** это дополнение к существующему отчёту в `work/process-reports`, не отдельный файл. Код runtime/renderer неизменён.
