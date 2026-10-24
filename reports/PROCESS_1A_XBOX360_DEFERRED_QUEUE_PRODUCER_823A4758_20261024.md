# Process 1A — Xbox 360 retail deferred-queue producer `0x823A4758`

**Дата:** 2026-10-24  
**Режим:** advance / static report-only; без изменений кода и без изменения runtime gates.  
**Область:** ровно одна функция `[0x823A4758, 0x823A4904)` (`0x1AC` байт), следующий entry `0x823A4908`. Не переносить выводы из PC P-code аудита или Process 2 renderer.

## 1. Идентичность и границы доказательств

- **Исходный retail:** Xbox 360 `default.xex`. Предоставленный XEX SHA-256: `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`.
- **Источник disassembly:** live-memory-derived ELF `/home/pes/ghidra_projects/research_inputs/nfs_shift_xbox360_live_20261024.elf`. В задании не указан сам 64-символьный ELF SHA-256 (после пути стоит двоеточие без хеша); его **нельзя считать проверенным**.
- **Первичный статический материал:** полный PowerPC objdump-блок `0x823A4758..0x823A4900`, предоставленный в задаче, включая исходные байты, целевые `bl`, `bctrl` и ветвления; конечная граница `0x823A4904` исключительная. В настоящем отчёте адреса инструкций служат однозначными ссылками на этот блок; несвязанный PC `SHIFT_objdump_full.txt` не подменяет Xbox ELF.
- **Ограничение независимой проверки:** Xbox ELF и `default.xex` отсутствовали в доступной среде анализа; локальный хеш, import-stub names, глобальные XREF, полная таблица указателей и прямые callers **не проверены**. Анализ инструкций ниже независим от названия ReXGlue и опирается на предоставленные байты/мнемоники.

**Уровни:** **[S]** непосредственно следует из приведённых инструкций; **[R]** отдельно передано как runtime observation; **[I]** интерпретация, требующая дополнительной проверки. Они не взаимозаменяемы.

## 2. ABI, процессный объект и синхронизация

**[S] Входной ABI.** Единственный читаемый входной аргумент — 32-битное слово в PPC `r3`, перенесённое в callee-saved `r30` на `0x823A4764` перед первым рабочим вызовом. Входные `r4`–`r10` функция не использует как аргументы. Явного осмысленного return value блок не задаёт; корректный внешний контракт — side effects (предположительно void), а не возвращаемое значение.

```text
packed       = u32(initial r3)
increment    = (packed >> 8) & 0xF           // r29; 0x823A47A0
threshold    = packed & 0xFF                 // r27; 0x823A47A8
tag_or_value = packed & 0xFFFFF000           // r30; 0x823A47B4
```

**[S] Выбор процесса.** Вызов `bl 0x83063ABC` на `0x823A4768` возвращает `r3`; `cmpwi cr6,r3,2` и `bf 26` проверяют равенство двум. Если `r3 == 2`, используется `lwz r11,0x6B0(0x82000000)` (`0x820006B0`), иначе — `lwz r11,0x6AC(0x82000000)` (`0x820006AC`). Далее на `0x823A4788` выполняется **второй** `lwz r31,0(r11)`: это два уровня чтения, `object = *(*slot)`, а не `object = *(0x820006AC/0x820006B0)`. Путь `r3 == 2` не означает отсутствие объекта или выбор по `r30`.

**[I] Символ** `KeGetCurrentProcessType` для `0x83063ABC` согласуется с предоставленным описанием, но сам full import/thunk mapping этого адреса не приложен; численный процессный переключатель доказан, символьная идентификация — пока внешний контекст.

**[S] Lock-пара.** `r26 = object + 0x4148` на `0x823A478C..0x823A4790`; `r3 = r26; bl 0x83063C0C` на `0x823A4794`. Возвращённое `r3` сохраняется в `r25` на `0x823A47AC`. Общий выход `0x823A48F0..0x823A48F8` делает `r3 = object + 0x4148; r4 = saved_r25; bl 0x83063BFC`. **[I]** Этот ABI соответствует acquire spin lock → saved previous state/IRQL → release spin lock, однако имена импортов и точный смысл token не подтверждены символами. Callback (`bctrl`) вызывается *между* этими двумя вызовами, то есть под тем же lock, если идентификация lock-пары верна. До работы с объектом есть служебный `bl 0x826D98B8`, в конце `b 0x826D9908`; по одному блоку нельзя именовать их или трактовать как дополнительный бизнес-вызов.

## 3. Данные, counters и временная шкала

### Поля объекта, наблюдаемые **[S]**

| Offset от `object = r31` | Операция в данной функции | Контракт в пределах блока |
| --- | --- | --- |
| `+0x409C` | `lwz` `0x823A4830`, проверка на ноль, `mtctr/bctrl` | необязательный function pointer, **не** поле deferred queue |
| `+0x40A4` | `lwz` `0x823A4808`, `0x823A4870` | `baseline`/reference counter, **не** физическая ёмкость очереди |
| `+0x40A8` | `lwz` `0x823A47CC` | low time-base epoch; в блоке не изменяется |
| `+0x40AC` | `lwz` `0x823A4804`; `stw` `0x823A4874` | previous → selected candidate counter |
| `+0x40B4` | `lwz/addi/stw` `0x823A4798..0x823A47B0` | число вызовов, увеличивается на **каждом проходе**, до callback |
| `+0x40B8` | `lwz/addi/stw` `0x823A48B4..0x823A48C0` | счётчик **альтернативной (не enqueue) ветки** |
| `+0x40BC..+0x413B` | `stw` `0x823A489C`, `0x823A48A0` | 16 записей × 8 байт deferred ring |
| `+0x413C` | нет чтения/записи здесь | отдельно наблюдавшийся consumer/read index; **producer не использует его для full-check** |
| `+0x4140` | `lwz` `0x823A488C`, `stw` `0x823A48AC` | producer/write index, инкремент только в enqueue |
| `+0x4148` | передаётся адрес в lock/unlock | slot/структура lock |
| `+0x2A94` | `lwz` `0x823A48DC` | указатель на объект прямой/альтернативной операции; zero-store по `[ptr+4]` |
| `+0x5434` | `lwz` `0x823A479C` | ненулевой делитель, при нуле fallback 60 |
| `+0x5B50` | `stw` `0x823A48EC` | low TB timestamp, только не-enqueue ветка |

**[S]** `0x823A47C8 mftb 268` даёт 32-битную low time-base; `elapsed = (u32)(TB_low - object[0x40A8])`. Вызов `0x8306375C` на `0x823A47D8` выдаёт величину `freq_like` в `r3` (имя/единицы не доказаны). Нулевой `object[0x5434]` заменяется на `60` (`0x823A47BC..0x823A47C4`). `0x823A47E4` сначала вычисляет unsigned `ticks_per_unit = (u32)freq_like / divisor`, далее `0x823A47E0` имеет 32-битное `mulli elapsed,100`, `0x823A47F0` вычисляет unsigned quotient, `0x823A47F4` прибавляет 1, `0x823A47F8..0x823A4800` ограничивает результат сверху 100:

```text
divisor        = (object[0x5434] != 0 ? object[0x5434] : 60)
elapsed        = u32(TB_low - object[0x40A8])
ticks_per_unit = u32(freq_like) / u32(divisor)
percent        = u32((u32)(elapsed * 100) / ticks_per_unit + 1)
if (percent > 100) percent = 100
```

**[S]** Инструкции `twi 6,r28,0` и `twi 6,r11,0` после первого деления на `0x823A47E8..0x823A47EC` сигнализируют trap при нулевых соответствующих значениях; функция не содержит отдельной защитной ветки на `ticks_per_unit == 0`. Возможен 32-битный wrap у `elapsed`, произведения, счётчиков и кандидата — не следует интерпретировать арифметику как произвольной разрядности. **[I]** Процент может отражать фазу/время относительно опорного периода; его физические единицы требуют контракта `0x8306375C`.

**[S] Выбор candidate.** На `0x823A4804..0x823A4830`:
```text
old      = object[0x40AC]
baseline = object[0x40A4]
candidate = u32(old + increment)
if (candidate <= baseline) {
    candidate = baseline
    if (increment != 0 && percent > threshold)
        candidate = u32(candidate + 1)
}
```
Проверка `bt 25` после `cmplw cr6,candidate,baseline` означает **unsigned greater-than**: при `candidate > baseline` немедленный выход к callback. Это не `min(candidate,baseline)`; при отсутствии пороговой коррекции результат соответствует `max(old+increment,baseline)`.

## 4. Callback ABI и факт изменения candidate

**[S]** Если `object[0x409C] != 0`, `0x823A483C..0x823A4868` строит временный 24-байтный stack record по `r1+0x50`, `r3 = &record`, затем `mtctr callback; bctrl`. Точное расположение **по байтам относительно передаваемого указателя**:

| Byte offset | Значение до callback |
| --- | --- |
| `+0x00` | `u32(tag_or_value != 0)`: `addic/subfe` на `0x823A4840..0x823A484C` |
| `+0x04` | инкрементированный `object[0x40B4]` |
| `+0x08` | `baseline = object[0x40A4]` |
| `+0x0C` | `old = object[0x40AC]` |
| `+0x10` | `percent` (верхняя отсечка 100) |
| `+0x14` | текущий `candidate` |

**[S]** Возврат callback в `r3` не используется. На `0x823A486C` producer **повторно загружает** `candidate = record[+0x14]`, то есть callback может менять решение о дальнейшем enqueue (by-reference), и только после этого `0x823A4874` записывает значение в `object[0x40AC]`. Поля `record[0..+0x10]` после callback самим producer не перечитываются. Отсутствие callback сохраняет исходно рассчитанный candidate.

**[I]** Нельзя по данному блоку назвать callback `0x82649B68` или утверждать, что setter `0x823A5730` пишет именно `+0x409C`: в пользовательском runtime наблюдении есть адрес setter/значение/адрес объекта, **но нет disassembly store offset setter и подтверждения, что он пишет в выбранный здесь `r31`**.

## 5. Enqueue и альтернативная ветка (инструкция за инструкцией)

**[S] Решение:** после `object[0x40AC] = candidate`, `0x823A4878..0x823A4888` направляет в не-enqueue ветку `0x823A48B4`, если
`(candidate == object[0x40A4]) || (object[0x40B4] == 1)`.
Иначе выполняется enqueue `0x823A488C..0x823A48B0`. Сравнение `candidate` делается после callback; проверка `0x40B4` — после его инкремента. Функция *не* тестирует `+0x413C`.

**[S] Enqueue layout и индексирование:**
```text
write_index = object[0x4140]
slot        = write_index & 0xF
off         = slot * 8      // rlwinm r10,r10,3,25,28 => (index << 3) & 0x78
*(u32 *)(object + 0x40BC + off) = tag_or_value    // stw at 0x823A48A0
*(u32 *)(object + 0x40C0 + off) = candidate       // stw at 0x823A489C
object[0x4140] = u32(write_index + 1)
```
Итак, `record[i] = { u32 tag_or_value, u32 candidate }`, `i = write_index % 16`; base `+0x40BC`, slot size `8`, последний второй word находится по `+0x4138`. Порядок фактических store обратен структурному порядку: **сначала candidate по `+4`, потом tag по `+0`**, затем increment write index. **[S]** В показанном producer нет сравнения read/write indices, полного состояния, ожидания свободного slot или остановки перед overwrite. **[I]** Название «кольцевая очередь» соответствует masked slot index; при отставании consumer возможна перезапись ещё не считанного record, если нет внешней гарантии заполнения. Наличие/отсутствие такой гарантии этим блоком не доказано.

**[S] Не-enqueue / direct-side-effect ветка `0x823A48B4..0x823A48F0`:**
1. Безусловно `object[0x40B8] = u32(object[0x40B8] + 1)`.
2. При `tag_or_value != 0`: `stw tag_or_value,0x7FC86110` (`lis 0x7FC8; stw +0x6110`, `0x823A48C8..0x823A48D0`), затем `eieio` и `sync`.
3. При `tag_or_value == 0`: `ptr = object[0x2A94]; *(u32 *)(ptr+4) = 0` (`0x823A48DC..0x823A48E4`); null-check `ptr` внутри блока нет.
4. В обеих подветках `object[0x5B50] = TB_low` (`0x823A48E8..0x823A48EC`).
5. Обе ветки convergе на unlock `0x823A48F0`.

**[I]** Назначение адреса `0x7FC86110` похоже на аппаратный side effect/MMIO (наличие `eieio;sync` это поддерживает), но точный register/functionality не установлен. Нельзя называть всю ветку «discard» без оговорки: она **не ставит запись в deferred ring**, но совершает прямой side effect и timestamp. Счётчик `+0x40B8` здесь точно считает эту ветку, а не доказанное число потерь.

**Разграничение очередей [S/R]:** `+0x4140` — writer deferred ring именно этой функции; `+0x413C` — другой индекс deferred ring, не изменяемый producer. Указатель `+0x2A94` в альтернативной ветке **не** равен software-queue tail `+0x2A9C`; предоставленное runtime наблюдение о независимой software queue не позволяет объединять их.

## 6. Статические callers, registration и dynamic evidence

**[S]** В самом блоке **нет** установки `object[0x409C]`, нет store адреса `0x823A4758` в таблицу callback и нет прямой ссылки на `0x82649B68` или `0x823A5730`. Единственный косвенный вызов — `bctrl` через `object[0x409C]`, а не вызов producer. Обычный прямой `bl` к producer, indirect caller или регистрация указателя на producer должны находиться *за пределами* `[0x823A4758,0x823A4904)`.

**Проверка доступного репозитория:** GitHub code search доступной индексированной default-ветки `Hanz0Hatt0r1/nfs-shift-decompilation` по строкам `823A4758` и `823A5730` не дал файловых совпадений на момент отчёта. Это проверка **текста репозитория, не XREF retail ELF**; она не доказывает отсутствие callers, регистрации callback или non-text pointers. Полный статический XREF-проход по `/home/pes/ghidra_projects/research_inputs/nfs_shift_xbox360_live_20261024.elf` в этой среде выполнить нельзя. Поэтому **ни один статический caller `0x823A4758` не подтверждён**, и «нет callers» — недопустимый вывод. Для полноценной проверки нужны direct branch targets в executable ranges и big-endian pointer references к `0x823A4758`, плюс анализ indirect `bctr/bctrl` и возможных registration stores; аналогично — исследование store offset setter `0x823A5730`.

**[R] Runtime, строго независимо:**
- Setter `0x823A5730` был выполнен и записал `0x82649B68` в объект `0xB7365F00`. Конкретное поле/offset не зафиксировано в предоставленных данных.
- Source-0 interrupt callback `0x823B37B8` и consumer `0x823A4640` выполнялись. Выборочные `+0x413C/+0x4140 = 0/0`, первый deferred record нулевой.
- Candidate producer `0x823A4758` **не дал dynamic hits** в двух ограниченных GDB прогонах.
- Software-queue tail `+0x2A9C` относится к отдельному пути. Predicate bit `0x02` ставится retail только на failure-ветке `VdIsHSIOTrainingSucceeded`; эту ветку нельзя форсировать ради hit.

**Что отсутствие dynamic hit означает:** в конкретных двух run scopes breakpoint/trace не обнаружил входа в `0x823A4758`; при ненарушенном instrumentation это согласуется с неподнявшимся producer и нулевым write index. **Чего не означает:** отсутствия статических callers, отсутствия регистрации, вечной недостижимости, отсутствия deferred traffic в иных игровых состояниях, либо прямой связи с predicate `0x02`. Нулевые индексы — выборка состояния, не доказательство инварианта; динамическая связь между отмеченным setter и `+0x409C` пока не установлена.

## 7. Один следующий точный retail target для Process 1

**`0x823A5730` — entry подтверждённого callback setter.** Следующее действие владельца Process 1: снять оригинальный PPC disassembly *этой функции* и проверить **точный effective address её store `0x82649B68`** относительно переданного `0xB7365F00`; сопоставить store-offset с проверяемым здесь `object+0x409C` и установить, ссылаются ли per-process globals `0x820006AC/0x820006B0` на тот же объект. Это единственный приоритетный адрес в данном handoff. Совпадение offset + identity подтвердит связывание callback; несовпадение локализует независимый registration path. Не форсировать `VdIsHSIOTrainingSucceeded`/bit `0x02`. После этого уже можно отдельно расширить статические XREF и runtime-trigger coverage для producer, без утверждения о достигнутом hit.

## 8. Вывод и обязательные ограничения

**Доказано статически по предоставленному retail-блоку:** packed-`r3` ABI; ветвление на `process_type == 2`; per-process double-deref; lock-like acquire/release ABI; обязательный counter `+0x40B4`; вычисление кандидата с TB-derived порогом; by-reference callback `+0x409C`; 16×8 deferred ring `+0x40BC` c write index `+0x4140`; отсутствие producer-side read/full-check `+0x413C`; отдельный direct path, counter `+0x40B8`, запись в `0x7FC86110` либо по `object[0x2A94]+4`, timestamp `+0x5B50`.

**Не доказано:** SHA-256 ELF; independent rehash XEX; реальные имена импортов `0x83063ABC/0x83063C0C/0x83063BFC/0x8306375C`; конкретное значение MMIO register; происхождение и единицы `freq_like`; static caller `0x823A4758`; registration source `object+0x409C`; равенство объекта setter и выбранного per-process object; безусловное выполнение producer за пределами двух ограниченных runs. **Никакие code/runtime gate изменения данным отчётом не авторизуются.**
