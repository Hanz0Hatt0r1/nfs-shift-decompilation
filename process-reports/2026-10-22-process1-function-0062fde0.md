# Process 1 — retail 0x0062FDE0 и wrapper 0x0062FFD0

**Дата:** 2026-10-22. **Бинарник:** Need for Speed Shift retail PC 1.02, PE32 x86, image base `0x00400000`.  
**SHA-256 оригинального `SHIFT.exe`, проверено локально:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Основание:** оригинальные `SHIFT.exe` и полный `SHIFT_objdump_full.txt`; runtime v749/v750 — **переданные наблюдения**, повторно не исполнялись. Только анализ, исходники не менялись, PR не создавался.

## 1. Итог

`0x0062FDE0` — инициализатор **блочного контейнера**, а не setter draw-enable/render-ready. Если `DWORD [this+0x18] != 0`, он сразу возвращает `AL=0`, не меняя `this+0x24`. Иначе нормализует alignment/flags и выбирает начальную ёмкость, передаёт настройки инициализатору блоков `0x0062F520` и при успешном прохождении собственного пути ставит два **DWORD** в ноль: `[this+0x24]=0` (**0x0062FEE8**) и `[this+0x28]=0` (**0x0062FEEB**). Завершается `AL=1`. Возвращаемый код `0x0062F520` не проверяется отдельно; поэтому `AL=1` здесь — завершение ветви инициализатора, а не доказательство наличия наполненных элементов.

`this+0x24` — **агрегатное количество содержащихся в контейнере элементов**, а не логический флаг готовности. Это подтверждается как инкрементом при добавлении (`0x004CB976–0x004CB979` для структуры совместимого контейнера), так и декрементом `0x0062FF6D`, а также проверками пустоты и очисткой. Для конкретного runtime-экземпляра `0x00BE2510` **из одного факта вызова generic writer нельзя заключить, что его реально пополняли**; необходимо фильтровать события по точному receiver.

## 2. ABI 0x0062FDE0

| Канал | Точное использование |
|---|---|
| ECX | указатель на container/this, сохраняется в ESI на 0x0062FDE5 |
| EDX | входное DWORD, сохраняется по [EBP-4] на 0x0062FDEB; передаётся дальше через EDX в 0x0062F520 и там сохраняется как [container+4] (в отсутствие ветвей переопределения) |
| [EBP+0x08] | начальное число элементов/ёмкость для случая, когда BYTE [EBP+0x18] == 0; значение идёт в 0x0062F520 |
| [EBP+0x0C] | размер элемента/stride, используется в расчётах 0x0062FE4F–0x0062FE8C и передаётся 0x0062F520 как размер элемента |
| [EBP+0x10] | настройка alignment, поступает в 0x00630DE0 на 0x0062FE06 |
| [EBP+0x14] | флаги: нижние пять бит заменяются нормализованным alignment, сохранение в [EBP+0x14] на 0x0062FE2B |
| [EBP+0x18] | проверяется **только младший байт**; управляет автоматическим подбором начальной ёмкости |
| [EBP+0x1C] | параметр allocator/metadata, передаваемый в 0x0062F520 |
| Возврат | AL=0 на непустом/уже имеющем блоке контейнере, AL=1 на основном пути; оба выхода — `ret 0x18` |

Это смешанное ECX/EDX + шесть stack DWORD соглашение, совместимое с MSVC x86 `__fastcall`; исходную C++-декларацию по нему установить однозначно нельзя. `ESI` сохраняется; `EBX/EDI` сохраняются только в главной ветви, где используются. **Возвращается байт AL**, полный EAX не обязан равняться нулю или единице.

### Ключевые развилки

- **0x0062FDE7–0x0062FDF6**: проверка `[this+0x18]`, при ненуле `AL=0`, `ret 0x18`, никаких изменений +0x24.
- **0x0062FE01–0x0062FE25**: `flags & 0x1F`, fallback 3, вызов `0x00630DE0` для нормализации alignment, сборка `EBX=(flags & ~0x1F)|normalized`. `0x00630DE0` вычисляет число битов / log2-like требуемое выравнивание; это не функция инициализации shader.
- **0x0062FE27–0x0062FE90**: при `BYTE [EBP+0x18]==0` использует [EBP+0x08]; иначе выбирает/пересчитывает ёмкость с учётом `[this+0x10]&0x200`, `[this+4]`, `[this+8]`, stride и минимумом порядка 0x100 байт. Деление `idiv ecx` на 0x0062FE5B/0x0062FE72/0x0062FE8A требует ненулевого stride в этих ветвях; прямой проверки на ноль здесь нет.
- **0x0062FE93–0x0062FEBB**: флаги создаваемого блока: low 5 bits и `0x40` при BYTE [this+0x2C] & 4, иначе `0x800`; возможен сброс бита `0x200` объекта.
- **0x0062FEC1–0x0062FECF**: вызов `0x0062F520` с ECX=this, EDX=рабочая вместимость/значение, стек `(stride, capacity, allocatorArg, flags, 0x00AA9A28)`.
- **0x0062FED4–0x0062FEE3**: при BYTE [EBP+0x14] & 0x40 устанавливает флаг `WORD [this+0x2C] |= 2`, затем безусловно `WORD [this+0x2C] |= 8`.
- **0x0062FEE8/0x0062FEEB**: обнуляет два DWORD `[this+0x24]`, `[this+0x28]`. `mov` по 32 бита, не запись одного byte. **0x0062FEEE** `mov al,1`, возврат 0x0062FEF4.

### Значение полей структуры

| Offset | Доказательства в соседних функциях | Роль |
|---|---|---|
| +0x00 | 0x0063AC90/0x0062F2D0 используют DWORD [container] для умножения на индекс | stride элемента в байтах |
| +0x04 | 0x0062F520: mov [esi+4],ecx (ECX=входной EDX); 0x0062FF00 меняет его при росте | параметр вместимости/размера нового блока |
| +0x08 | 0x0062F520: mov [esi+8],eax | политика изменения размера блока |
| +0x10 | 0x0062F520: mov [esi+0x10],edx; 0x0062FDE0 тестирует биты | flags/config |
| +0x18 | 0x0062F520/0x0062F6F0 записывают голову блочной цепочки | pointer на первый блок |
| +0x1C | те же + 0x0062FD50 изменяют последний блок | pointer на последний блок |
| +0x24 | 0x0062FEE8, 0x0062FF6D, 0x004CB979 | совокупное количество элементов |
| +0x28 | 0x0062FEEB; 0x0062FF70; 0x0062FD99 | число элементов в головном блоке (или тесно связанный с ним cached count) |
| +0x2C | 0x0062FEDC/0x0062FEE3, 0x0062FD B0 | битовые flags |
| +0x30 | 0x004CB973, 0x0050CFD0 | cached pointer начала данных |

Внутренний блок из `0x0063AC20`: `block+0x08` — next pointer, `block+0x10` — capacity/количество слотов bitmap, `block+0x14` — количество занятых, `block+0x04` — base/current data address. Полная source-level структура и точные names неизвестны.

## 3. Wrapper 0x0062FFD0: точный ABI и флаги

`0x0062FFD0` получает `ECX=this` и **передаёт входящий EDX без изменений** непосредственно в `0x0062FDE0`. Он переносит шесть стековых DWORD `[wrapper EBP+8,+C,+10,+14,+18,+1C]` на стек целевой функции в том же порядке. Входящий `[wrapper EBP+0x20]` в теле **не используется**, хотя wrapper завершает `ret 0x1C` (очищает семь DWORD). Это важное несовпадение с `ret 0x18` целевой функции: нельзя объявлять оба ABI идентичными.

На **0x0062FFF6–0x0062FFFF** при `AL(inner)!=0` и `flags ([wrapper EBP+0x14]) & 0x20` выполняет `WORD [this+0x2C] |= 1`. На других путях wrapper просто завершает работу. **Wrapper не возвращает сохранённый bool**: после pop-регистров EAX не нормализуется и итоговый AL может остаться от inner, но его контракт по коду не следует объявлять `bool` без проверки callsite. `ret 0x1C` — очистка семи стековых аргументов, источник дополнительного седьмого DWORD находится в caller.

## 4. Проверенная цепочка до 0x0050CEB0

```asm
0050CF10  jmp 004E8BC0

004E8BC0  push ebp
004E8BC1  mov ebp,esp
004E8BC3  push ecx
004E8BC4  mov BYTE PTR [ebp-4],0
004E8BC8  mov eax,[ebp-4]
004E8BCB  push eax             ; seventh argument, zero in local normal path
004E8BCC  mov eax,[ebp+0x10]
004E8BCF  push eax
004E8BD0  mov eax,[ebp+0x0C]
004E8BD3  push 0
004E8BD5  push eax
004E8BD6  mov eax,[ebp+0x08]
004E8BD9  push 4
004E8BDB  push 0x44
004E8BDD  push eax
004E8BDE  call 0062FFD0
004E8BE3  jmp 004E8BF8
004E8BF8  mov esp,ebp
004E8BFA  pop ebp
004E8BFB  ret 0x0C
```

Следовательно, wrapper 0x0062FFD0 видит: `[+8]=callerArg1`, `[+0xC]=0x44` (stride **68 bytes**), `[+0x10]=4` (alignment parameter), `[+0x14]=callerArg2` (flags), `[+0x18]=0` (automatic-size control выключен), `[+0x1C]=callerArg3`, `[+0x20]=0` (unused wrapper trailing DWORD). `ECX` и `EDX` сохраняются через tail jump `0x0050CF10`; `0x004E8BC0` не устанавливает им новых значений.

`0x0050CF10` — **только thunk** на `0x004E8BC0`, а не отдельная реализация аллокатора.

`0x0050CEB0` использует другой уровень вложенности:
```asm
0050CEB0  push esi
0050CEB1  mov esi,ecx
0050CEB3  lea ecx,[esi+0x10]
0050CEB6  call 0082F3C0
0050CEBB  test al,al
0050CEBD  jne 0050CEC6
```
Getter `0x0082F3C0`: `cmp DWORD PTR [ecx+0x24],0; sete al; ret`. Поэтому реально читается `DWORD [outer+0x10+0x24]` = `DWORD [outer+0x34]`. Сообщение «reader [ECX+0x24] в каждом вызове 0x0050CEB0» следует понимать как **ECX getter**, равный `outer+0x10`, **а не входящий ECX outer**. Если вложенный container pointer равен `0x00BE2510`, то outer pointer — `0x00BE2500`, проверяемый адрес `0x00BE2534`.

При **нулевом счётчике** getter возвращает AL=1, функция идёт на `0x0050CEC6`, выполняет `0x0050C880(ECX=outer)` и по его результату может вернуть 1 или затем выполнить путь `[outer+0x48].vtable+0x24C` с `DL=0`; на последнем пути возвращает AL=0 (`0x0050CEE6`). При **ненулевом** счётчике `0x0050CEBF` переходит в `0x0048FB36` (`mov eax,1`) и через `0x0050CEC4` возвращает с AL=1. Значит отсутствие элементов не означает автоматического завершения всего процесса и уж тем более не доказывает draw.

## 5. Пути записи и добавления — что доказано и что нет

**Непосредственный writer из provenance:** `0x0062FEE8: mov DWORD [ESI+0x24],0` при `ESI=0x00BE2510` записывает ноль в **0x00BE2534**, а `0x0062FEEB` также обнуляет DWORD **0x00BE2538**. Если инициализатор вернул AL=1, это ожидаемое пустое начальное состояние контейнера, а не ошибка.

**Другие code-level writers в том же container-family:**
- `0x0062FF60–0x0062FF73`: `0x0062FF67` декрементирует count блока `[head+0x14]`; **0x0062FF6D** выполняет `add DWORD [container+0x24], -1`; **0x0062FF70** уменьшает `+0x28`. Это обратная операция удаления.
- `0x0062FD50`: на пути удаления последнего блока `0x0062FDC2` записывает `[container+0x24]=0`, а `0x0062FDBF` зануляет `+0x28`; флаги `+0x2C&2` определяют, снимается ли цепочка блоков.
- `0x004CB900` — подтверждённый **generic add** для совместимого по layout контейнера: `0x004CB944–0x004CB946` получает новый слот через `0x004CB6D0`, `0x004CB95E–0x004CB960` копирует DWORD из `[EDX]`, `0x004CB966–0x004CB979` увеличивает `[container+0x24]` на 1 и при первом элементе устанавливает cached base `+0x30`. **Однако нет доказательства из v749/v750, что этот конкретный generic add исполнялся с `ECX=0x00BE2510`**. Кроме того, для данного container установлен stride 0x44, поэтому нельзя автоматически приписывать ему именно DWORD-copy generic add; сам add может быть template-specialized.
- `0x0062F6F0` резервирует/находит слот, вызывает `0x0063AC90`, который на **0x0063AD1B** инкрементирует **[block+0x14]** и возвращает адрес элемента. Эта операция **сама по себе не показывает инкремент outer [container+0x24]**; не следует подменять блоковый счётчик глобальным. Нужны вызывающий код и фактические write-probes.
- Уничтожающие/очищающие пути `0x0050CE30`, `0x0050CFxx` также зануляют поля контейнера при обходе блоков; точный runtime reachability не подтверждён.

**Что означают v749/v750:** read = 0 на всех наблюдаемых `0x0050CEB0` getter calls, provenance называет последним writer `0x0062FDE0` и показанный адрес. Это согласуется с отсутствием **зарегистрированного ненулевого добавления** до этих чтений, но не доказывает, что никакой producer не существует, что container не выделял блоков, или что отсутствие элементов вызвало отсутствие Draw*. Единственное надёжное утверждение о состоянии: `[container+0x24]=0` в моменты чтения. Никакое принудительное присваивание поля недопустимо.

## 6. Подтверждённое / гипотезы

**Подтверждено оригинальным retail EXE:** SHA-256; регистрово-стековый ABI, ранний AL=0 при `+0x18!=0`, нормализация флагов, вызов `0x0062F520`, два DWORD-zero на `0x0062FEE8/+EB`, отдельная flag-логика wrapper, точная цепочка `0x0050CF10 → 0x004E8BC0 → 0x0062FFD0 → 0x0062FDE0`, `0x0050CEB0` сдвигает ECX на +0x10 до getter, общий счётчик +0x24 и block-level +0x14, generic добавление +1 в `0x004CB900`.

**Сильно поддержанное назначение:** инициализация и учёт элементов блочного контейнера 68-байтных записей для обрамляющего объекта. Это не frame flag/renderer enable.

**Не доказано:** исходное имя класса/метода, назначение записей размером 0x44, фактический producer для именно `0x00BE2510`, почему этот producer не сработал в v749/v750, является ли контейнер необходимым условием Draw*, причина отсутствия GPU-команд. Нельзя делать вывод по одному значению счётчика.

## 7. Следующий **один** trace target

**Write watchpoint на DWORD 0x00BE2534, условие new value != 0**, с сохранением retail EIP, receiver, return address и стека. Это самый конкретный единичный target: он выявит первый реально достигнутый producer/инкремент именно нужного экземпляра без необоснованного предположения, что им является `0x004CB900` или `0x0062F6F0`. Если такой write отсутствует во всём ограниченном прогоне, зафиксировать отсутствие наблюдаемых добавлений, не принуждая значение и не экстраполируя на GPU.

## 8. Полный objdump: 0x0062FDE0–0x0062FEF4 (без пропусков)

~~~asm
0062fde0: 55                   push ebp
0062fde1: 8b ec                mov ebp,esp
0062fde3: 51                   push ecx
0062fde4: 56                   push esi
0062fde5: 8b f1                mov esi,ecx
0062fde7: 83 7e 18 00          cmp DWORD PTR [esi+0x18],0
0062fdeb: 89 55 fc             mov DWORD PTR [ebp-0x4],edx
0062fdee: 74 09                je 0x62fdf9
0062fdf0: 32 c0                xor al,al
0062fdf2: 5e                   pop esi
0062fdf3: 8b e5                mov esp,ebp
0062fdf5: 5d                   pop ebp
0062fdf6: c2 18 00             ret 0x18
0062fdf9: 8b 4d 10             mov ecx,DWORD PTR [ebp+0x10]
0062fdfc: 53                   push ebx
0062fdfd: 8b 5d 14             mov ebx,DWORD PTR [ebp+0x14]
0062fe00: 57                   push edi
0062fe01: 8b fb                mov edi,ebx
0062fe03: 83 e7 1f             and edi,0x1f
0062fe06: e8 d5 0f 00 00       call 0x630de0
0062fe0b: 85 ff                test edi,edi
0062fe0d: 75 05                jne 0x62fe14
0062fe0f: bf 03 00 00 00       mov edi,0x3
0062fe14: 3b f8                cmp edi,eax
0062fe16: 72 05                jb 0x62fe1d
0062fe18: 83 ff 1f             cmp edi,0x1f
0062fe1b: 75 02                jne 0x62fe1f
0062fe1d: 8b f8                mov edi,eax
0062fe1f: 8b 4d 0c             mov ecx,DWORD PTR [ebp+0xc]
0062fe22: 83 e3 e0             and ebx,0xffffffe0
0062fe25: 0b df                or ebx,edi
0062fe27: 80 7d 18 00          cmp BYTE PTR [ebp+0x18],0
0062fe2b: 89 5d 14             mov DWORD PTR [ebp+0x14],ebx
0062fe2e: 74 60                je 0x62fe90
0062fe30: 8b 56 10             mov edx,DWORD PTR [esi+0x10]
0062fe33: f7 c2 00 02 00 00    test edx,0x200
0062fe39: 74 14                je 0x62fe4f
0062fe3b: 8b 46 04             mov eax,DWORD PTR [esi+0x4]
0062fe3e: 8b 7e 08             mov edi,DWORD PTR [esi+0x8]
0062fe41: 81 e2 ff fd ff ff    and edx,0xfffffdff
0062fe47: 89 45 fc             mov DWORD PTR [ebp-0x4],eax
0062fe4a: 89 56 10             mov DWORD PTR [esi+0x10],edx
0062fe4d: eb 44                jmp 0x62fe93
0062fe4f: 8b c1                mov eax,ecx
0062fe51: c1 e0 04             shl eax,0x4
0062fe54: 83 c0 1f             add eax,0x1f
0062fe57: 83 e0 e0             and eax,0xffffffe0
0062fe5a: 99                   cdq
0062fe5b: f7 f9                idiv ecx
0062fe5d: 8b f8                mov edi,eax
0062fe5f: 0f af c1             imul eax,ecx
0062fe62: 3d 00 01 00 00       cmp eax,0x100
0062fe67: 89 7d fc             mov DWORD PTR [ebp-0x4],edi
0062fe6a: 7f 0b                jg 0x62fe77
0062fe6c: b8 00 01 00 00       mov eax,0x100
0062fe71: 99                   cdq
0062fe72: f7 f9                idiv ecx
0062fe74: 89 45 fc             mov DWORD PTR [ebp-0x4],eax
0062fe77: 8b d7                mov edx,edi
0062fe79: 0f af d1             imul edx,ecx
0062fe7c: 81 fa 00 01 00 00    cmp edx,0x100
0062fe82: 7f 0f                jg 0x62fe93
0062fe84: b8 00 01 00 00       mov eax,0x100
0062fe89: 99                   cdq
0062fe8a: f7 f9                idiv ecx
0062fe8c: 8b f8                mov edi,eax
0062fe8e: eb 03                jmp 0x62fe93
0062fe90: 8b 7d 08             mov edi,DWORD PTR [ebp+0x8]
0062fe93: 8b d3                mov edx,ebx
0062fe95: 83 e2 1f             and edx,0x1f
0062fe98: f6 46 2c 04          test BYTE PTR [esi+0x2c],0x4
0062fe9c: 74 05                je 0x62fea3
0062fe9e: 83 ca 40             or edx,0x40
0062fea1: eb 06                jmp 0x62fea9
0062fea3: 81 ca 00 08 00 00    or edx,0x800
0062fea9: 8b 46 10             mov eax,DWORD PTR [esi+0x10]
0062feac: 8b d8                mov ebx,eax
0062feae: c1 eb 09             shr ebx,0x9
0062feb1: f6 c3 01             test bl,0x1
0062feb4: 74 08                je 0x62febe
0062feb6: 25 ff fd ff ff       and eax,0xfffffdff
0062febb: 89 46 10             mov DWORD PTR [esi+0x10],eax
0062febe: 8b 45 1c             mov eax,DWORD PTR [ebp+0x1c]
0062fec1: 68 28 9a aa 00       push 0xaa9a28
0062fec6: 52                   push edx
0062fec7: 8b 55 fc             mov edx,DWORD PTR [ebp-0x4]
0062feca: 50                   push eax
0062fecb: 57                   push edi
0062fecc: 51                   push ecx
0062fecd: 8b ce                mov ecx,esi
0062fecf: e8 4c f6 ff ff       call 0x62f520
0062fed4: f6 45 14 40          test BYTE PTR [ebp+0x14],0x40
0062fed8: 5f                   pop edi
0062fed9: 5b                   pop ebx
0062feda: 74 05                je 0x62fee1
0062fedc: 66 83 4e 2c 02       or WORD PTR [esi+0x2c],0x2
0062fee1: 33 c0                xor eax,eax
0062fee3: 66 83 4e 2c 08       or WORD PTR [esi+0x2c],0x8
0062fee8: 89 46 24             mov DWORD PTR [esi+0x24],eax
0062feeb: 89 46 28             mov DWORD PTR [esi+0x28],eax
0062feee: b0 01                mov al,0x1
0062fef0: 5e                   pop esi
0062fef1: 8b e5                mov esp,ebp
0062fef3: 5d                   pop ebp
0062fef4: c2 18 00             ret 0x18
~~~

Следующие 0x0062FEF7–0x0062FEFF — INT3 padding; 0x0062FF00 — **другая** функция, не часть блока.

## 9. Полный objdump wrapper 0x0062FFD0–0x00630007

~~~asm
0062ffd0: 55                   push ebp
0062ffd1: 8b ec                mov ebp,esp
0062ffd3: 8b 45 1c             mov eax,DWORD PTR [ebp+0x1c]
0062ffd6: 53                   push ebx
0062ffd7: 8b 5d 14             mov ebx,DWORD PTR [ebp+0x14]
0062ffda: 56                   push esi
0062ffdb: 50                   push eax
0062ffdc: 8b 45 10             mov eax,DWORD PTR [ebp+0x10]
0062ffdf: 8b f1                mov esi,ecx
0062ffe1: 8b 4d 18             mov ecx,DWORD PTR [ebp+0x18]
0062ffe4: 51                   push ecx
0062ffe5: 8b 4d 0c             mov ecx,DWORD PTR [ebp+0xc]
0062ffe8: 53                   push ebx
0062ffe9: 50                   push eax
0062ffea: 8b 45 08             mov eax,DWORD PTR [ebp+0x8]
0062ffed: 51                   push ecx
0062ffee: 50                   push eax
0062ffef: 8b ce                mov ecx,esi
0062fff1: e8 ea fd ff ff       call 0x62fde0
0062fff6: 84 c0                test al,al
0062fff8: 74 0a                je 0x630004
0062fffa: f6 c3 20             test bl,0x20
0062fffd: 74 05                je 0x630004
0062ffff: 66 83 4e 2c 01       or WORD PTR [esi+0x2c],0x1
00630004: 5e                   pop esi
00630005: 5b                   pop ebx
00630006: 5d                   pop ebp
00630007: c2 1c 00             ret 0x1c
~~~

Следующее 0x0063000A+ — padding и **другие функции**.
