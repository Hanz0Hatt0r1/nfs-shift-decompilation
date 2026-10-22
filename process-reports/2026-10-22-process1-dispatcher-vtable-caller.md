# Process 1 — внешний virtual-call site retail dispatcher 0x004692E0

**Дата:** 2026-10-22. **Объект:** Need for Speed Shift PC retail 1.02, PE32 x86. **Image base:** \`0x00400000\`.  
**SHA-256 оригинального \`SHIFT.exe\`, проверен локально:** \`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1\`.  
**Статическая база:** приложенный 172,686,363-байтовый полный \`SHIFT_objdump_full.txt\`, приложенный оригинальный \`SHIFT.exe\` (проверен по SHA-256), непосредственное чтение .rdata и дизассемблирования по адресам. **Ghidra не доступна в текущей среде; нельзя выдавать результат GNU objdump за Ghidra decompiler xrefs.**  
**Внешняя динамика:** только переданный пользователем v768 — повторного прогона не было. **Scope:** external virtual caller, identity и provenance объекта, без повторного state switch. Изменений P-code/runtime, render, graphics assets и PR нет.

## Краткий вывод

**Точный внешний executable callsite \`[vptr+4] → 0x004692E0\` для объекта со статическим vptr \`0x00AB5644\` установить по доступным статическим xrefs НЕ удалось.** Нельзя объявлять найденный generic virtual-call site вызывающим именно этот target только по равенству offset +4; требуется доказательство источника ECX / vptr. При этом **provenance самого объекта разрешён значительно дальше прежнего отчёта**:

\`\`\`
0040EBC0    JMP 00D36210                         ; bootstrap thunk
00D36210    allocate 0x1F20 → 0054B730 → [00BC1850]  ; отдельный объект
00D36273    allocate 0x000C → 00547D50 → [00BC1858]  ; отдельный объект
00D362B9    allocate 0x46E0 bytes
00D362D7    ECX=returned memory, CALL 0045EF50   ; именно наш объект
0045EF78    [this+0] = 0x00AB5644               ; primary vptr
0045EF7E    [this+4] = 0x00AB55F0               ; SECONDARY vptr, not primary slot
0045EF85    [this+8] = 0x00AB55E4               ; another secondary vptr
00D362EC    [0x00BC185C] = returned object       ; global authoritative storage
\`\`\`

Если allocation 0x46E0 возвратит NULL, **0x00D362F3** записывает ноль в \`[0x00BC185C]\`; сам указанный код не доказывает, что объект создан в конкретном v768. В штатном успешном пути constructor \`0x0045EF50\` возвращает EAX=this. Глобальный pointer \`0x00BC185C\` и vtable первичного interface имеют реальную кодовую связь, а не только похожий layout.

## Подтверждение точного virtual slot и ABI вызова

В оригинальной .rdata прочитаны WORD-aligned DWORD (little endian):

| Адрес ячейки | Значение | Роль |
|---|---|---|
| \`0x00AB5644\` | \`0x0066D450\` | primary vtable entry 0 |
| **\`0x00AB5648\`** | **\`0x004692E0\`** | **primary vtable entry +4** |
| \`0x00AB564C\` | \`0x00466A80\` | primary vtable entry +8 |
| \`0x00AB55F0\` | \`0x0045F610\` | entry в **отдельной** vtable из \`[this+4]\` |
| \`0x00AB55E4\` | \`0x004624C0\` | entry в **отдельной** vtable из \`[this+8]\` |

**Требуемый эквивалент нормального первичного virtual call**: \`ECX=object\`, \`V=DWORD[ECX+0]\`, \`F=DWORD[V+4]\`, \`CALL F\` при V=0x00AB5644; без явных stack args, поскольку функция \`0x004692E0\` завершается обычным \`RET\`. Это описание *условия попадания*, **не найденная реальная команда вызова**. Наивное чтение \`[this+4]\` как «slot +4» ложно: \`[this+4]\` содержит secondary vptr 0x00AB55F0, а primary slot +4 находится в памяти по \`[[this]+4]\`.

**Lifecycle correction:** \`0x00462E20\`, также записывающая vptr 0x00AB5644, вызывается из \`0x00464200\` как destruct/teardown, с освобождением элементов/полей. Не следует считать её вторым независимым фабричным конструктором или новым объектом на основании одного \`mov [this],vptr\`. Полные блоки конструктора, teardown и scalar-deleting wrapper приложены ниже.

## Реальные внешние xrefs глобального экземпляра (не то же самое, что indirect caller)

Прямой доступ к \`[0x00BC185C]\` хорошо подтверждён: **115** инструкции с упоминанием этого global operand в полном objdump (включая все direct loads и static stores), но обычная таблица текстовых xrefs **не доказывает конкретную виртуальную диспетчеризацию**. Например:

- \`0x0040CFC4\` загружает \`EAX=[0x00BC185C]\`, читает \`BYTE [EAX+0xD20]\`; при своей ветви **0x0040D002** загружает \`ECX=[0x00BC185C]\`, делает \`push 1\`, **0x0040D00A: call 0x00462400\`**, а по обратной ветви **0x0040D020\` / \`0x0040D028\` вызывает тот же direct callee с нулём. Это **доказанная прямая передача именно глобального экземпляра в ECX**, но **не** вызов по \`[vptr+4]\`. Внутренние смещения объекта \`+0xD20\` и direct method family согласованы с конструктором.
- \`0x0040BB4A\` читает \`ESI=[0x00BC185C]\`, проверяет \`[ESI+0x2B0]\`; это отдельный статический consumer state, **не** virtual caller dispatcher.
- Несколько callsite используют \`[global+0xC4C]\` как **другой объект** и далее вызывают собственные slots (\`0x0048ECE5–0x0048ECF0\`, \`0x0049580E–0x00495819\`, \`0x0049917B–0x00499186\`). Это не slot +4 primary vptr.
- \`0x0040D834\`, \`0x004956D0\`, \`0x004957B7\` получают \`global+0x04\` или \`global+0x780\`: subobject interface / queue. В этих случаях нельзя считать \`ECX=primaryObject\`.

Полный поиск по \`SHIFT_objdump_full.txt\` **не нашёл ни прямых \`CALL rel32 0x004692E0\`, ни прямых JMP с этой целью**. Единственная байтовая ссылка target в указанной vtable — **data xref**, не executable callsite. Дополнительно была проведена консервативная линейная register-origin проверка более сотни инструкций после каждого direct global xref: при сохранении \`object → [object] vptr → [vptr+4] target → call target\` не обнаружено ни одного однозначного совпадения. Эта эвристика не является полноценным межпроцедурным alias analysis и может пропускать ветвления, stack spills, callback lists, opaque-returns и secondary interface coercion.

## Indirect/vtable candidates из per-frame-контекста — что исключено и что осталось

В исследованном per-frame пути \`0x0040BA50–0x0040BB38\` действительно встречаются **два syntactically matching \`vtable+4\` calls**, которые нельзя механически записывать на имя 0x004692E0:

| Косвенный CALL | Object provenance, доказанный локально | Вывод о диспетчере |
|---|---|---|
| **\`0x0040BA8E\`** | \`0x0040BA79/0x0040BA82\`: объект из \`0x00894A60()\`; \`EAX=[object]\`, \`EAX=[vptr+4]\`, \`ECX=object\` | Такой dispatch *структурно* способен вызвать slot +4; **нет подтверждения**, что \`0x00894A60()\` возвращает pointer \`[0x00BC185C]\`, и это не direct xref к глобальному объекту |
| **\`0x0040BAF5\`** | \`0x0040BACB\`: результат \`0x00409FF0()\` в EDI; \`[EDI]\` → \`[vptr+4]\` → \`CALL\` | То же ограничение: **не установлено** ни тождество EDI глобальному экземпляру, ни vptr 0x00AB5644 |

Это **два конкретных executable candidate-места с правильным механическим offset**, а не доказанные callers. Оба расположены внутри полной функции \`0x0040BA50–0x0040BB38\` (ниже). Аналогичные виртуальные вызовы во внешней процедуре \`0x00A69160\` направлены в **другие смещения** (+0x80, +0xA0, +0x38, +0x24, +0x28, +0x2C) и не совпадают с primary slot +4; этот факт **не усиливает** идентификацию нашего target.

**Неразрешённый случай:** глобальный object pointer может передаваться дальше через аргументы, поля/контейнеры, callback owner либо virtual interface; прямые текстовые xrefs тогда не дадут адрес конкретного caller. Без Ghidra interprocedural decompilation или runtime пары \`(callsite EIP, ECX, vptr)\` назначение одного из этих сайтов было бы ложноположительным. Ни один проверенный candidate пока не имеет доказанного pointer identity. Наличие конструктора и vtable entry само по себе не доказывает, что slot +4 когда-либо вызывается.

## v768 — ограниченный no-capture runtime baseline

Дано пользователем: \`SHIFT.exe\` тот же SHA; runtime SHA-256 \`545c9eadd76f7183b64e8a8dd12a51a88c480b31f857b76ed01af170626f1f3f\`; manifest v659 SHA-256 \`6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e\`. 360 host frames, exit 0, \`validation_errors=0\`, 1,755,838 P-code dispatches / 4,727 unique functions. Trace targets включают dispatcher 0x004692E0, 0x00463120, state writer setter 0x0045B1E0, 0x0045C000, producer 0x004052B0, enqueue 0x004049D0 и четыре Draw imports. \`guest_call_trace_enabled=true, truncated=false, events=[]\`; capture env unset, \`guest_draw_translation=false\`; log SHA-256 \`6b52ebad3962f47e41ce3b6c90a112cecd3518aef7fd67b757b719b92d4a48a6\`.

Следовательно **в указанном bounded run ни один отобранный target не наблюдался**, но это **не** говорит, что объект реально создан, что event никогда не выполняется в другом режиме/периоде, что игра не может переходить к main menu либо что проблема renderer имеет причиной этот dispatcher. Нельзя ошибочно использовать v768 для утверждения о runtime-vptr, поскольку vptr / адрес экземпляра в выбранных samples не сообщён.

## Confidence ledger

**PE-byte proven:** identity SHA; three distinct allocations в 0x00D36210; actual object comes from allocation **0x46E0** with return from 0x0045EF50, stored by 0x00D362EC at global \`0x00BC185C\`; constructor writes primary vptr+secondary vptr; \`[[this]+4] = 0x004692E0\`; no stack ABI for this dispatcher; distinct direct global call to 0x00462400; raw executable generic +4 sites 0x0040BA8E / 0x0040BAF5 and their local origins; destructor re-vptr does not establish constructor identity; missing direct rel32 call.

**Only source runtime evidence:** v768 bounded negative target trace, not reachability census and not object identity.

**Hypothesis/not established:** exact original class name; exact external virtual caller; whether either per-frame generic +4 call receives this global object; any hidden callback/alias chain from \`[0x00BC185C]\`; whether 0x004692E0 is invoked outside 360-frame bounded run; menu/render causal story.

## Ровно один следующий runtime filter

**Instrument only indirect-call dispatch edges where the *resolved callee target* is \`0x004692E0\`.** On a match record \`callsite guest EIP\`, \`ECX\`, \`DWORD[ECX]\` and \`DWORD[0x00BC185C]\` in that same instant, plus current dispatch/frame id. **Do not write any field or patch return.** Этот **один фильтр** при появлении события одновременно определит фактический caller и проверит \`ECX == [0x00BC185C]\`, а также отличит primary-vptr 0x00AB5644 от совпадения смещения +4 у другого типа. Если он снова пуст в bounded run, фиксировать только отрицательное наблюдение выбранного окна, не недостижимость функции.

## Полные исходные objdump-блоки

Все блоки приведены **из приложенного полного оригинального objdump**, с машинными байтами; не заменены пересказом. \`INT3\` в \`.secu\` между переходами сохраняются как реальные padding bytes, а не интерпретируются как исполняемая линейная ветвь. Никаких чужих renderer изменений.

### 1. Retail bootstrap thunk 0x0040EBC0–0x0040EBC5 (2 строк с адресами)

```asm
  40ebc0:	e9 4b 76 92 00       	jmp    0xd36210
  40ebc5:	90                   	nop
```


### 2. Static initializer 0x00D36210–0x00D362FA (146 строк с адресами)

```asm
  d36210:	56                   	push   esi
  d36211:	68 20 1f 00 00       	push   0x1f20
  d36216:	e8 a5 06 b5 ff       	call   0x8868c0
  d3621b:	eb 07                	jmp    0xd36224
  d3621d:	cc                   	int3
  d3621e:	cc                   	int3
  d3621f:	cc                   	int3
  d36220:	cc                   	int3
  d36221:	cc                   	int3
  d36222:	cc                   	int3
  d36223:	cc                   	int3
  d36224:	33 f6                	xor    esi,esi
  d36226:	83 c4 04             	add    esp,0x4
  d36229:	3b c6                	cmp    eax,esi
  d3622b:	74 40                	je     0xd3626d
  d3622d:	8b c8                	mov    ecx,eax
  d3622f:	e8 fc 54 81 ff       	call   0x54b730
  d36234:	eb 30                	jmp    0xd36266
  d36236:	cc                   	int3
  d36237:	cc                   	int3
  d36238:	cc                   	int3
  d36239:	cc                   	int3
  d3623a:	cc                   	int3
  d3623b:	cc                   	int3
  d3623c:	cc                   	int3
  d3623d:	cc                   	int3
  d3623e:	cc                   	int3
  d3623f:	cc                   	int3
  d36240:	cc                   	int3
  d36241:	cc                   	int3
  d36242:	cc                   	int3
  d36243:	cc                   	int3
  d36244:	cc                   	int3
  d36245:	cc                   	int3
  d36246:	cc                   	int3
  d36247:	cc                   	int3
  d36248:	cc                   	int3
  d36249:	cc                   	int3
  d3624a:	cc                   	int3
  d3624b:	cc                   	int3
  d3624c:	cc                   	int3
  d3624d:	cc                   	int3
  d3624e:	cc                   	int3
  d3624f:	cc                   	int3
  d36250:	cc                   	int3
  d36251:	cc                   	int3
  d36252:	cc                   	int3
  d36253:	cc                   	int3
  d36254:	cc                   	int3
  d36255:	cc                   	int3
  d36256:	cc                   	int3
  d36257:	cc                   	int3
  d36258:	cc                   	int3
  d36259:	cc                   	int3
  d3625a:	cc                   	int3
  d3625b:	cc                   	int3
  d3625c:	cc                   	int3
  d3625d:	cc                   	int3
  d3625e:	cc                   	int3
  d3625f:	cc                   	int3
  d36260:	cc                   	int3
  d36261:	cc                   	int3
  d36262:	cc                   	int3
  d36263:	cc                   	int3
  d36264:	cc                   	int3
  d36265:	cc                   	int3
  d36266:	a3 50 18 bc 00       	mov    ds:0xbc1850,eax
  d3626b:	eb 06                	jmp    0xd36273
  d3626d:	89 35 50 18 bc 00    	mov    DWORD PTR ds:0xbc1850,esi
  d36273:	6a 0c                	push   0xc
  d36275:	89 35 54 18 bc 00    	mov    DWORD PTR ds:0xbc1854,esi
  d3627b:	e8 40 06 b5 ff       	call   0x8868c0
  d36280:	eb 07                	jmp    0xd36289
  d36282:	cc                   	int3
  d36283:	cc                   	int3
  d36284:	cc                   	int3
  d36285:	cc                   	int3
  d36286:	cc                   	int3
  d36287:	cc                   	int3
  d36288:	cc                   	int3
  d36289:	83 c4 04             	add    esp,0x4
  d3628c:	3b c6                	cmp    eax,esi
  d3628e:	74 23                	je     0xd362b3
  d36290:	8b c8                	mov    ecx,eax
  d36292:	e8 b9 1a 81 ff       	call   0x547d50
  d36297:	eb 13                	jmp    0xd362ac
  d36299:	cc                   	int3
  d3629a:	cc                   	int3
  d3629b:	cc                   	int3
  d3629c:	cc                   	int3
  d3629d:	cc                   	int3
  d3629e:	cc                   	int3
  d3629f:	cc                   	int3
  d362a0:	cc                   	int3
  d362a1:	cc                   	int3
  d362a2:	cc                   	int3
  d362a3:	cc                   	int3
  d362a4:	cc                   	int3
  d362a5:	cc                   	int3
  d362a6:	cc                   	int3
  d362a7:	cc                   	int3
  d362a8:	cc                   	int3
  d362a9:	cc                   	int3
  d362aa:	cc                   	int3
  d362ab:	cc                   	int3
  d362ac:	a3 58 18 bc 00       	mov    ds:0xbc1858,eax
  d362b1:	eb 06                	jmp    0xd362b9
  d362b3:	89 35 58 18 bc 00    	mov    DWORD PTR ds:0xbc1858,esi
  d362b9:	68 e0 46 00 00       	push   0x46e0
  d362be:	e8 fd 05 b5 ff       	call   0x8868c0
  d362c3:	eb 0b                	jmp    0xd362d0
  d362c5:	cc                   	int3
  d362c6:	cc                   	int3
  d362c7:	cc                   	int3
  d362c8:	cc                   	int3
  d362c9:	cc                   	int3
  d362ca:	cc                   	int3
  d362cb:	cc                   	int3
  d362cc:	cc                   	int3
  d362cd:	cc                   	int3
  d362ce:	cc                   	int3
  d362cf:	cc                   	int3
  d362d0:	83 c4 04             	add    esp,0x4
  d362d3:	3b c6                	cmp    eax,esi
  d362d5:	74 1c                	je     0xd362f3
  d362d7:	8b c8                	mov    ecx,eax
  d362d9:	e8 72 8c 72 ff       	call   0x45ef50
  d362de:	eb 0c                	jmp    0xd362ec
  d362e0:	cc                   	int3
  d362e1:	cc                   	int3
  d362e2:	cc                   	int3
  d362e3:	cc                   	int3
  d362e4:	cc                   	int3
  d362e5:	cc                   	int3
  d362e6:	cc                   	int3
  d362e7:	cc                   	int3
  d362e8:	cc                   	int3
  d362e9:	cc                   	int3
  d362ea:	cc                   	int3
  d362eb:	cc                   	int3
  d362ec:	a3 5c 18 bc 00       	mov    ds:0xbc185c,eax
  d362f1:	5e                   	pop    esi
  d362f2:	c3                   	ret
  d362f3:	89 35 5c 18 bc 00    	mov    DWORD PTR ds:0xbc185c,esi
  d362f9:	5e                   	pop    esi
  d362fa:	c3                   	ret
```


### 3. Actual constructing function 0x0045EF50–0x0045F5F1 (370 строк с адресами)

```asm
  45ef50:	55                   	push   ebp
  45ef51:	8b ec                	mov    ebp,esp
  45ef53:	83 ec 08             	sub    esp,0x8
  45ef56:	53                   	push   ebx
  45ef57:	56                   	push   esi
  45ef58:	57                   	push   edi
  45ef59:	8b f1                	mov    esi,ecx
  45ef5b:	e8 40 fc fa ff       	call   0x40eba0
  45ef60:	c7 46 04 60 4c ab 00 	mov    DWORD PTR [esi+0x4],0xab4c60
  45ef67:	c7 46 08 80 87 b0 00 	mov    DWORD PTR [esi+0x8],0xb08780
  45ef6e:	33 db                	xor    ebx,ebx
  45ef70:	bf 01 00 00 00       	mov    edi,0x1
  45ef75:	8d 4e 20             	lea    ecx,[esi+0x20]
  45ef78:	c7 06 44 56 ab 00    	mov    DWORD PTR [esi],0xab5644
  45ef7e:	c7 46 04 f0 55 ab 00 	mov    DWORD PTR [esi+0x4],0xab55f0
  45ef85:	c7 46 08 e4 55 ab 00 	mov    DWORD PTR [esi+0x8],0xab55e4
  45ef8c:	89 5e 0c             	mov    DWORD PTR [esi+0xc],ebx
  45ef8f:	c6 46 10 01          	mov    BYTE PTR [esi+0x10],0x1
  45ef93:	c6 46 11 01          	mov    BYTE PTR [esi+0x11],0x1
  45ef97:	c6 46 12 01          	mov    BYTE PTR [esi+0x12],0x1
  45ef9b:	89 7e 14             	mov    DWORD PTR [esi+0x14],edi
  45ef9e:	88 5e 18             	mov    BYTE PTR [esi+0x18],bl
  45efa1:	88 5e 19             	mov    BYTE PTR [esi+0x19],bl
  45efa4:	e8 d7 2d fa ff       	call   0x401d80
  45efa9:	d9 ee                	fldz
  45efab:	89 9e c0 01 00 00    	mov    DWORD PTR [esi+0x1c0],ebx
  45efb1:	89 9e c4 01 00 00    	mov    DWORD PTR [esi+0x1c4],ebx
  45efb7:	88 9e c8 01 00 00    	mov    BYTE PTR [esi+0x1c8],bl
  45efbd:	d9 96 cc 01 00 00    	fst    DWORD PTR [esi+0x1cc]
  45efc3:	d9 e8                	fld1
  45efc5:	88 9e dc 01 00 00    	mov    BYTE PTR [esi+0x1dc],bl
  45efcb:	d9 96 d0 01 00 00    	fst    DWORD PTR [esi+0x1d0]
  45efd1:	d9 c9                	fxch   st(1)
  45efd3:	d9 96 d4 01 00 00    	fst    DWORD PTR [esi+0x1d4]
  45efd9:	d9 96 d8 01 00 00    	fst    DWORD PTR [esi+0x1d8]
  45efdf:	d9 96 e0 01 00 00    	fst    DWORD PTR [esi+0x1e0]
  45efe5:	d9 05 6c 1a ab 00    	fld    DWORD PTR ds:0xab1a6c
  45efeb:	d9 96 e4 01 00 00    	fst    DWORD PTR [esi+0x1e4]
  45eff1:	d9 ca                	fxch   st(2)
  45eff3:	d9 96 e8 01 00 00    	fst    DWORD PTR [esi+0x1e8]
  45eff9:	d9 96 f0 01 00 00    	fst    DWORD PTR [esi+0x1f0]
  45efff:	88 9e fc 01 00 00    	mov    BYTE PTR [esi+0x1fc],bl
  45f005:	d9 c9                	fxch   st(1)
  45f007:	d9 96 ec 01 00 00    	fst    DWORD PTR [esi+0x1ec]
  45f00d:	d9 96 f4 01 00 00    	fst    DWORD PTR [esi+0x1f4]
  45f013:	d9 96 f8 01 00 00    	fst    DWORD PTR [esi+0x1f8]
  45f019:	d9 96 00 02 00 00    	fst    DWORD PTR [esi+0x200]
  45f01f:	d9 ca                	fxch   st(2)
  45f021:	d9 96 04 02 00 00    	fst    DWORD PTR [esi+0x204]
  45f027:	d9 c9                	fxch   st(1)
  45f029:	d9 96 08 02 00 00    	fst    DWORD PTR [esi+0x208]
  45f02f:	d9 ca                	fxch   st(2)
  45f031:	88 9e 1c 02 00 00    	mov    BYTE PTR [esi+0x21c],bl
  45f037:	d9 96 0c 02 00 00    	fst    DWORD PTR [esi+0x20c]
  45f03d:	d9 96 14 02 00 00    	fst    DWORD PTR [esi+0x214]
  45f043:	d9 96 18 02 00 00    	fst    DWORD PTR [esi+0x218]
  45f049:	d9 ca                	fxch   st(2)
  45f04b:	d9 96 10 02 00 00    	fst    DWORD PTR [esi+0x210]
  45f051:	d9 ca                	fxch   st(2)
  45f053:	d9 96 20 02 00 00    	fst    DWORD PTR [esi+0x220]
  45f059:	d9 c9                	fxch   st(1)
  45f05b:	d9 9e 24 02 00 00    	fstp   DWORD PTR [esi+0x224]
  45f061:	d9 c9                	fxch   st(1)
  45f063:	d9 9e 28 02 00 00    	fstp   DWORD PTR [esi+0x228]
  45f069:	d9 05 fc 9a aa 00    	fld    DWORD PTR ds:0xaa9afc
  45f06f:	89 9e 2c 02 00 00    	mov    DWORD PTR [esi+0x22c],ebx
  45f075:	d9 9e 44 02 00 00    	fstp   DWORD PTR [esi+0x244]
  45f07b:	89 9e 30 02 00 00    	mov    DWORD PTR [esi+0x230],ebx
  45f081:	89 9e 34 02 00 00    	mov    DWORD PTR [esi+0x234],ebx
  45f087:	89 be 38 02 00 00    	mov    DWORD PTR [esi+0x238],edi
  45f08d:	d9 9e 68 02 00 00    	fstp   DWORD PTR [esi+0x268]
  45f093:	89 be 3c 02 00 00    	mov    DWORD PTR [esi+0x23c],edi
  45f099:	89 be 40 02 00 00    	mov    DWORD PTR [esi+0x240],edi
  45f09f:	89 9e 48 02 00 00    	mov    DWORD PTR [esi+0x248],ebx
  45f0a5:	88 9e 4c 02 00 00    	mov    BYTE PTR [esi+0x24c],bl
  45f0ab:	88 9e 4d 02 00 00    	mov    BYTE PTR [esi+0x24d],bl
  45f0b1:	88 9e 4e 02 00 00    	mov    BYTE PTR [esi+0x24e],bl
  45f0b7:	88 9e a0 02 00 00    	mov    BYTE PTR [esi+0x2a0],bl
  45f0bd:	c6 86 a1 02 00 00 01 	mov    BYTE PTR [esi+0x2a1],0x1
  45f0c4:	89 9e a4 02 00 00    	mov    DWORD PTR [esi+0x2a4],ebx
  45f0ca:	89 9e a8 02 00 00    	mov    DWORD PTR [esi+0x2a8],ebx
  45f0d0:	89 9e ac 02 00 00    	mov    DWORD PTR [esi+0x2ac],ebx
  45f0d6:	89 9e b0 02 00 00    	mov    DWORD PTR [esi+0x2b0],ebx
  45f0dc:	8d 8e c0 02 00 00    	lea    ecx,[esi+0x2c0]
  45f0e2:	e8 99 3f 1d 00       	call   0x633080
  45f0e7:	8d 8e 20 05 00 00    	lea    ecx,[esi+0x520]
  45f0ed:	e8 1e 68 1c 00       	call   0x625910
  45f0f2:	8d 8e 80 07 00 00    	lea    ecx,[esi+0x780]
  45f0f8:	e8 83 3f 1d 00       	call   0x633080
  45f0fd:	8d 8e e0 09 00 00    	lea    ecx,[esi+0x9e0]
  45f103:	e8 78 3f 1d 00       	call   0x633080
  45f108:	53                   	push   ebx
  45f109:	68 cc 55 ab 00       	push   0xab55cc
  45f10e:	68 00 20 00 00       	push   0x2000
  45f113:	c7 86 40 0c 00 00 ff ff ff ff 	mov    DWORD PTR [esi+0xc40],0xffffffff
  45f11d:	c7 86 44 0c 00 00 ff ff ff ff 	mov    DWORD PTR [esi+0xc44],0xffffffff
  45f127:	c7 86 48 0c 00 00 ff ff ff ff 	mov    DWORD PTR [esi+0xc48],0xffffffff
  45f131:	89 9e 4c 0c 00 00    	mov    DWORD PTR [esi+0xc4c],ebx
  45f137:	c6 86 50 0c 00 00 01 	mov    BYTE PTR [esi+0xc50],0x1
  45f13e:	88 9e 51 0c 00 00    	mov    BYTE PTR [esi+0xc51],bl
  45f144:	89 9e 54 0c 00 00    	mov    DWORD PTR [esi+0xc54],ebx
  45f14a:	88 9e 58 0c 00 00    	mov    BYTE PTR [esi+0xc58],bl
  45f150:	88 9e 59 0c 00 00    	mov    BYTE PTR [esi+0xc59],bl
  45f156:	88 9e 5a 0c 00 00    	mov    BYTE PTR [esi+0xc5a],bl
  45f15c:	e8 cf 6c 23 00       	call   0x695e30
  45f161:	8b c8                	mov    ecx,eax
  45f163:	e8 a8 6d 23 00       	call   0x695f10
  45f168:	8b c8                	mov    ecx,eax
  45f16a:	e8 91 b5 22 00       	call   0x68a700
  45f16f:	53                   	push   ebx
  45f170:	68 c0 55 ab 00       	push   0xab55c0
  45f175:	6a 20                	push   0x20
  45f177:	89 86 5c 0c 00 00    	mov    DWORD PTR [esi+0xc5c],eax
  45f17d:	e8 ae 6c 23 00       	call   0x695e30
  45f182:	8b c8                	mov    ecx,eax
  45f184:	e8 87 6d 23 00       	call   0x695f10
  45f189:	8b c8                	mov    ecx,eax
  45f18b:	e8 70 b5 22 00       	call   0x68a700
  45f190:	53                   	push   ebx
  45f191:	68 a4 55 ab 00       	push   0xab55a4
  45f196:	68 00 04 00 00       	push   0x400
  45f19b:	89 86 70 0c 00 00    	mov    DWORD PTR [esi+0xc70],eax
  45f1a1:	e8 8a 6c 23 00       	call   0x695e30
  45f1a6:	8b c8                	mov    ecx,eax
  45f1a8:	e8 63 6d 23 00       	call   0x695f10
  45f1ad:	8b c8                	mov    ecx,eax
  45f1af:	e8 4c b5 22 00       	call   0x68a700
  45f1b4:	53                   	push   ebx
  45f1b5:	68 8c 55 ab 00       	push   0xab558c
  45f1ba:	68 00 10 00 00       	push   0x1000
  45f1bf:	89 86 a4 0c 00 00    	mov    DWORD PTR [esi+0xca4],eax
  45f1c5:	e8 66 6c 23 00       	call   0x695e30
  45f1ca:	8b c8                	mov    ecx,eax
  45f1cc:	e8 3f 6d 23 00       	call   0x695f10
  45f1d1:	8b c8                	mov    ecx,eax
  45f1d3:	e8 28 b5 22 00       	call   0x68a700
  45f1d8:	8d be b0 0c 00 00    	lea    edi,[esi+0xcb0]
  45f1de:	8b cf                	mov    ecx,edi
  45f1e0:	89 86 a8 0c 00 00    	mov    DWORD PTR [esi+0xca8],eax
  45f1e6:	e8 d5 d9 21 00       	call   0x67cbc0
  45f1eb:	b8 10 00 00 00       	mov    eax,0x10
  45f1f0:	89 47 04             	mov    DWORD PTR [edi+0x4],eax
  45f1f3:	89 47 08             	mov    DWORD PTR [edi+0x8],eax
  45f1f6:	89 5f 0c             	mov    DWORD PTR [edi+0xc],ebx
  45f1f9:	89 5f 18             	mov    DWORD PTR [edi+0x18],ebx
  45f1fc:	89 5f 1c             	mov    DWORD PTR [edi+0x1c],ebx
  45f1ff:	89 1f                	mov    DWORD PTR [edi],ebx
  45f201:	89 5f 20             	mov    DWORD PTR [edi+0x20],ebx
  45f204:	c7 47 24 02 00 00 00 	mov    DWORD PTR [edi+0x24],0x2
  45f20b:	6a 01                	push   0x1
  45f20d:	8d 8e 10 0d 00 00    	lea    ecx,[esi+0xd10]
  45f213:	88 9e 00 0d 00 00    	mov    BYTE PTR [esi+0xd00],bl
  45f219:	e8 b2 fc 1e 00       	call   0x64eed0
  45f21e:	8d be 2c 0d 00 00    	lea    edi,[esi+0xd2c]
  45f224:	8b cf                	mov    ecx,edi
  45f226:	88 9e 20 0d 00 00    	mov    BYTE PTR [esi+0xd20],bl
  45f22c:	88 9e 21 0d 00 00    	mov    BYTE PTR [esi+0xd21],bl
  45f232:	89 9e 24 0d 00 00    	mov    DWORD PTR [esi+0xd24],ebx
  45f238:	88 9e 28 0d 00 00    	mov    BYTE PTR [esi+0xd28],bl
  45f23e:	e8 1d b0 3a 00       	call   0x80a260
  45f243:	8d 8e b0 0d 00 00    	lea    ecx,[esi+0xdb0]
  45f249:	89 9e ac 0d 00 00    	mov    DWORD PTR [esi+0xdac],ebx
  45f24f:	e8 0c a8 0a 00       	call   0x509a60
  45f254:	8d 8e 60 0e 00 00    	lea    ecx,[esi+0xe60]
  45f25a:	e8 31 28 07 00       	call   0x4d1a90
  45f25f:	8d 8e a0 11 00 00    	lea    ecx,[esi+0x11a0]
  45f265:	e8 56 3c 07 00       	call   0x4d2ec0
  45f26a:	8d 8e e0 14 00 00    	lea    ecx,[esi+0x14e0]
  45f270:	e8 7b 97 0a 00       	call   0x5089f0
  45f275:	8d 8e 40 18 00 00    	lea    ecx,[esi+0x1840]
  45f27b:	e8 40 46 07 00       	call   0x4d38c0
  45f280:	8d 8e 40 1c 00 00    	lea    ecx,[esi+0x1c40]
  45f286:	e8 05 3f 07 00       	call   0x4d3190
  45f28b:	8d 8e a0 1f 00 00    	lea    ecx,[esi+0x1fa0]
  45f291:	e8 2a 39 07 00       	call   0x4d2bc0
  45f296:	8d 8e e0 22 00 00    	lea    ecx,[esi+0x22e0]
  45f29c:	e8 bf 4f 07 00       	call   0x4d4260
  45f2a1:	8d 8e 60 26 00 00    	lea    ecx,[esi+0x2660]
  45f2a7:	e8 24 42 07 00       	call   0x4d34d0
  45f2ac:	8d 8e c0 29 00 00    	lea    ecx,[esi+0x29c0]
  45f2b2:	e8 c9 6e 07 00       	call   0x4d6180
  45f2b7:	8d 8e 20 2d 00 00    	lea    ecx,[esi+0x2d20]
  45f2bd:	e8 4e 78 07 00       	call   0x4d6b10
  45f2c2:	8d 8e e0 33 00 00    	lea    ecx,[esi+0x33e0]
  45f2c8:	e8 73 5f 07 00       	call   0x4d5240
  45f2cd:	8d 8e 60 38 00 00    	lea    ecx,[esi+0x3860]
  45f2d3:	e8 58 2e 07 00       	call   0x4d2130
  45f2d8:	8d 8e e0 3b 00 00    	lea    ecx,[esi+0x3be0]
  45f2de:	e8 ed 2a 07 00       	call   0x4d1dd0
  45f2e3:	8d 8e 20 3f 00 00    	lea    ecx,[esi+0x3f20]
  45f2e9:	e8 52 54 07 00       	call   0x4d4740
  45f2ee:	8d 8e 20 43 00 00    	lea    ecx,[esi+0x4320]
  45f2f4:	e8 67 33 07 00       	call   0x4d2660
  45f2f9:	68 a0 00 00 00       	push   0xa0
  45f2fe:	e8 bd 75 42 00       	call   0x8868c0
  45f303:	83 c4 04             	add    esp,0x4
  45f306:	3b c3                	cmp    eax,ebx
  45f308:	74 0d                	je     0x45f317
  45f30a:	53                   	push   ebx
  45f30b:	8b c8                	mov    ecx,eax
  45f30d:	e8 ce 41 24 00       	call   0x6a34e0
  45f312:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  45f315:	eb 03                	jmp    0x45f31a
  45f317:	89 5d fc             	mov    DWORD PTR [ebp-0x4],ebx
  45f31a:	68 00 10 00 00       	push   0x1000
  45f31f:	6a 06                	push   0x6
  45f321:	6a 01                	push   0x1
  45f323:	8d 45 fc             	lea    eax,[ebp-0x4]
  45f326:	50                   	push   eax
  45f327:	8b cf                	mov    ecx,edi
  45f329:	e8 12 42 24 00       	call   0x6a3540
  45f32e:	53                   	push   ebx
  45f32f:	68 74 55 ab 00       	push   0xab5574
  45f334:	68 00 10 00 00       	push   0x1000
  45f339:	e8 f2 6a 23 00       	call   0x695e30
  45f33e:	8b c8                	mov    ecx,eax
  45f340:	e8 cb 6b 23 00       	call   0x695f10
  45f345:	8b c8                	mov    ecx,eax
  45f347:	e8 b4 b3 22 00       	call   0x68a700
  45f34c:	53                   	push   ebx
  45f34d:	68 5c 55 ab 00       	push   0xab555c
  45f352:	68 00 10 00 00       	push   0x1000
  45f357:	89 86 60 0c 00 00    	mov    DWORD PTR [esi+0xc60],eax
  45f35d:	e8 ce 6a 23 00       	call   0x695e30
  45f362:	8b c8                	mov    ecx,eax
  45f364:	e8 a7 6b 23 00       	call   0x695f10
  45f369:	8b c8                	mov    ecx,eax
  45f36b:	e8 90 b3 22 00       	call   0x68a700
  45f370:	53                   	push   ebx
  45f371:	68 44 55 ab 00       	push   0xab5544
  45f376:	68 00 10 00 00       	push   0x1000
  45f37b:	89 86 64 0c 00 00    	mov    DWORD PTR [esi+0xc64],eax
  45f381:	e8 aa 6a 23 00       	call   0x695e30
  45f386:	8b c8                	mov    ecx,eax
  45f388:	e8 83 6b 23 00       	call   0x695f10
  45f38d:	8b c8                	mov    ecx,eax
  45f38f:	e8 6c b3 22 00       	call   0x68a700
  45f394:	53                   	push   ebx
  45f395:	68 2c 55 ab 00       	push   0xab552c
  45f39a:	68 00 10 00 00       	push   0x1000
  45f39f:	89 86 68 0c 00 00    	mov    DWORD PTR [esi+0xc68],eax
  45f3a5:	e8 86 6a 23 00       	call   0x695e30
  45f3aa:	8b c8                	mov    ecx,eax
  45f3ac:	e8 5f 6b 23 00       	call   0x695f10
  45f3b1:	8b c8                	mov    ecx,eax
  45f3b3:	e8 48 b3 22 00       	call   0x68a700
  45f3b8:	89 86 6c 0c 00 00    	mov    DWORD PTR [esi+0xc6c],eax
  45f3be:	8d be 74 0c 00 00    	lea    edi,[esi+0xc74]
  45f3c4:	c7 45 f8 0c 00 00 00 	mov    DWORD PTR [ebp-0x8],0xc
  45f3cb:	eb 03                	jmp    0x45f3d0
  45f3cd:	8d 49 00             	lea    ecx,[ecx+0x0]
  45f3d0:	53                   	push   ebx
  45f3d1:	68 50 45 ab 00       	push   0xab4550
  45f3d6:	68 00 10 00 00       	push   0x1000
  45f3db:	e8 50 6a 23 00       	call   0x695e30
  45f3e0:	8b c8                	mov    ecx,eax
  45f3e2:	e8 29 6b 23 00       	call   0x695f10
  45f3e7:	8b c8                	mov    ecx,eax
  45f3e9:	e8 12 b3 22 00       	call   0x68a700
  45f3ee:	89 07                	mov    DWORD PTR [edi],eax
  45f3f0:	83 c7 04             	add    edi,0x4
  45f3f3:	83 6d f8 01          	sub    DWORD PTR [ebp-0x8],0x1
  45f3f7:	75 d7                	jne    0x45f3d0
  45f3f9:	89 9e 38 0d 00 00    	mov    DWORD PTR [esi+0xd38],ebx
  45f3ff:	89 9e 3c 0d 00 00    	mov    DWORD PTR [esi+0xd3c],ebx
  45f405:	89 9e 40 0d 00 00    	mov    DWORD PTR [esi+0xd40],ebx
  45f40b:	89 9e 44 0d 00 00    	mov    DWORD PTR [esi+0xd44],ebx
  45f411:	ba 09 00 00 00       	mov    edx,0x9
  45f416:	b9 14 55 ab 00       	mov    ecx,0xab5514
  45f41b:	88 9e 78 0d 00 00    	mov    BYTE PTR [esi+0xd78],bl
  45f421:	88 9e 84 0d 00 00    	mov    BYTE PTR [esi+0xd84],bl
  45f427:	89 9e 7c 0d 00 00    	mov    DWORD PTR [esi+0xd7c],ebx
  45f42d:	89 9e 88 0d 00 00    	mov    DWORD PTR [esi+0xd88],ebx
  45f433:	88 9e 90 0d 00 00    	mov    BYTE PTR [esi+0xd90],bl
  45f439:	88 9e 91 0d 00 00    	mov    BYTE PTR [esi+0xd91],bl
  45f43f:	89 9e 94 0d 00 00    	mov    DWORD PTR [esi+0xd94],ebx
  45f445:	89 9e 98 0d 00 00    	mov    DWORD PTR [esi+0xd98],ebx
  45f44b:	c7 86 9c 0d 00 00 ff ff ff ff 	mov    DWORD PTR [esi+0xd9c],0xffffffff
  45f455:	89 9e a0 0d 00 00    	mov    DWORD PTR [esi+0xda0],ebx
  45f45b:	c6 86 a4 0d 00 00 01 	mov    BYTE PTR [esi+0xda4],0x1
  45f462:	e8 d9 3a 1d 00       	call   0x632f40
  45f467:	8d be 40 0c 00 00    	lea    edi,[esi+0xc40]
  45f46d:	8b d7                	mov    edx,edi
  45f46f:	b9 fc 54 ab 00       	mov    ecx,0xab54fc
  45f474:	e8 97 3a 1d 00       	call   0x632f10
  45f479:	8d 96 44 0c 00 00    	lea    edx,[esi+0xc44]
  45f47f:	b9 e8 54 ab 00       	mov    ecx,0xab54e8
  45f484:	e8 87 3a 1d 00       	call   0x632f10
  45f489:	8d 96 48 0c 00 00    	lea    edx,[esi+0xc48]
  45f48f:	b9 d0 54 ab 00       	mov    ecx,0xab54d0
  45f494:	e8 77 3a 1d 00       	call   0x632f10
  45f499:	8b 17                	mov    edx,DWORD PTR [edi]
  45f49b:	53                   	push   ebx
  45f49c:	53                   	push   ebx
  45f49d:	68 ac 54 ab 00       	push   0xab54ac
  45f4a2:	6a 0d                	push   0xd
  45f4a4:	8d be 20 05 00 00    	lea    edi,[esi+0x520]
  45f4aa:	6a 01                	push   0x1
  45f4ac:	8b cf                	mov    ecx,edi
  45f4ae:	e8 7d 39 1d 00       	call   0x632e30
  45f4b3:	e8 48 35 2a 00       	call   0x702a00
  45f4b8:	50                   	push   eax
  45f4b9:	e8 12 9a ff ff       	call   0x458ed0
  45f4be:	50                   	push   eax
  45f4bf:	ba 03 00 00 00       	mov    edx,0x3
  45f4c4:	8b cf                	mov    ecx,edi
  45f4c6:	e8 25 41 1d 00       	call   0x6335f0
  45f4cb:	8b 96 44 0c 00 00    	mov    edx,DWORD PTR [esi+0xc44]
  45f4d1:	53                   	push   ebx
  45f4d2:	53                   	push   ebx
  45f4d3:	68 8c 54 ab 00       	push   0xab548c
  45f4d8:	6a 09                	push   0x9
  45f4da:	6a 01                	push   0x1
  45f4dc:	8d 8e 80 07 00 00    	lea    ecx,[esi+0x780]
  45f4e2:	e8 49 39 1d 00       	call   0x632e30
  45f4e7:	8b 96 48 0c 00 00    	mov    edx,DWORD PTR [esi+0xc48]
  45f4ed:	53                   	push   ebx
  45f4ee:	53                   	push   ebx
  45f4ef:	68 68 54 ab 00       	push   0xab5468
  45f4f4:	6a 09                	push   0x9
  45f4f6:	6a 01                	push   0x1
  45f4f8:	8d 8e e0 09 00 00    	lea    ecx,[esi+0x9e0]
  45f4fe:	e8 2d 39 1d 00       	call   0x632e30
  45f503:	d9 05 68 1a ab 00    	fld    DWORD PTR ds:0xab1a68
  45f509:	d9 9e 6c 02 00 00    	fstp   DWORD PTR [esi+0x26c]
  45f50f:	d9 05 64 54 ab 00    	fld    DWORD PTR ds:0xab5464
  45f515:	d9 9e 70 02 00 00    	fstp   DWORD PTR [esi+0x270]
  45f51b:	d9 05 14 9a aa 00    	fld    DWORD PTR ds:0xaa9a14
  45f521:	d9 96 74 02 00 00    	fst    DWORD PTR [esi+0x274]
  45f527:	d9 05 a4 0d ab 00    	fld    DWORD PTR ds:0xab0da4
  45f52d:	d9 9e 78 02 00 00    	fstp   DWORD PTR [esi+0x278]
  45f533:	d9 05 f0 b4 aa 00    	fld    DWORD PTR ds:0xaab4f0
  45f539:	d9 9e 7c 02 00 00    	fstp   DWORD PTR [esi+0x27c]
  45f53f:	d9 e8                	fld1
  45f541:	d9 9e 80 02 00 00    	fstp   DWORD PTR [esi+0x280]
  45f547:	d9 05 a8 0d ab 00    	fld    DWORD PTR ds:0xab0da8
  45f54d:	d9 9e 84 02 00 00    	fstp   DWORD PTR [esi+0x284]
  45f553:	d9 05 60 54 ab 00    	fld    DWORD PTR ds:0xab5460
  45f559:	d9 9e 88 02 00 00    	fstp   DWORD PTR [esi+0x288]
  45f55f:	d9 ee                	fldz
  45f561:	d9 9e 8c 02 00 00    	fstp   DWORD PTR [esi+0x28c]
  45f567:	d9 05 5c 54 ab 00    	fld    DWORD PTR ds:0xab545c
  45f56d:	d9 9e 90 02 00 00    	fstp   DWORD PTR [esi+0x290]
  45f573:	d9 05 58 54 ab 00    	fld    DWORD PTR ds:0xab5458
  45f579:	d9 9e 94 02 00 00    	fstp   DWORD PTR [esi+0x294]
  45f57f:	b9 78 d0 aa 00       	mov    ecx,0xaad078
  45f584:	d9 05 b4 c7 aa 00    	fld    DWORD PTR ds:0xaac7b4
  45f58a:	89 9e 64 02 00 00    	mov    DWORD PTR [esi+0x264],ebx
  45f590:	d9 9e 98 02 00 00    	fstp   DWORD PTR [esi+0x298]
  45f596:	89 9e 34 0d 00 00    	mov    DWORD PTR [esi+0xd34],ebx
  45f59c:	d9 05 04 45 ab 00    	fld    DWORD PTR ds:0xab4504
  45f5a2:	d9 9e 9c 02 00 00    	fstp   DWORD PTR [esi+0x29c]
  45f5a8:	d9 05 f8 b3 aa 00    	fld    DWORD PTR ds:0xaab3f8
  45f5ae:	d9 9e 50 02 00 00    	fstp   DWORD PTR [esi+0x250]
  45f5b4:	d9 05 bc c7 aa 00    	fld    DWORD PTR ds:0xaac7bc
  45f5ba:	d9 9e 54 02 00 00    	fstp   DWORD PTR [esi+0x254]
  45f5c0:	d9 96 58 02 00 00    	fst    DWORD PTR [esi+0x258]
  45f5c6:	d9 05 f8 9a aa 00    	fld    DWORD PTR ds:0xaa9af8
  45f5cc:	d9 9e 5c 02 00 00    	fstp   DWORD PTR [esi+0x25c]
  45f5d2:	d9 9e 60 02 00 00    	fstp   DWORD PTR [esi+0x260]
  45f5d8:	e8 13 75 1e 00       	call   0x646af0
  45f5dd:	88 86 c0 46 00 00    	mov    BYTE PTR [esi+0x46c0],al
  45f5e3:	5f                   	pop    edi
  45f5e4:	88 9e c1 46 00 00    	mov    BYTE PTR [esi+0x46c1],bl
  45f5ea:	8b c6                	mov    eax,esi
  45f5ec:	5e                   	pop    esi
  45f5ed:	5b                   	pop    ebx
  45f5ee:	8b e5                	mov    esp,ebp
  45f5f0:	5d                   	pop    ebp
  45f5f1:	c3                   	ret
```


### 4. Destructing/teardown function 0x00462E20–0x00463111 (201 строк с адресами)

```asm
  462e20:	55                   	push   ebp
  462e21:	8b ec                	mov    ebp,esp
  462e23:	51                   	push   ecx
  462e24:	53                   	push   ebx
  462e25:	56                   	push   esi
  462e26:	8b f1                	mov    esi,ecx
  462e28:	57                   	push   edi
  462e29:	8b be 30 02 00 00    	mov    edi,DWORD PTR [esi+0x230]
  462e2f:	33 db                	xor    ebx,ebx
  462e31:	3b fb                	cmp    edi,ebx
  462e33:	c7 06 44 56 ab 00    	mov    DWORD PTR [esi],0xab5644
  462e39:	c7 46 04 f0 55 ab 00 	mov    DWORD PTR [esi+0x4],0xab55f0
  462e40:	c7 46 08 e4 55 ab 00 	mov    DWORD PTR [esi+0x8],0xab55e4
  462e47:	74 16                	je     0x462e5f
  462e49:	8b cf                	mov    ecx,edi
  462e4b:	e8 20 05 24 00       	call   0x6a3370
  462e50:	57                   	push   edi
  462e51:	e8 da 3a 42 00       	call   0x886930
  462e56:	83 c4 04             	add    esp,0x4
  462e59:	89 9e 30 02 00 00    	mov    DWORD PTR [esi+0x230],ebx
  462e5f:	8b 96 34 02 00 00    	mov    edx,DWORD PTR [esi+0x234]
  462e65:	3b d3                	cmp    edx,ebx
  462e67:	74 16                	je     0x462e7f
  462e69:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  462e6f:	8b 01                	mov    eax,DWORD PTR [ecx]
  462e71:	8b 80 04 02 00 00    	mov    eax,DWORD PTR [eax+0x204]
  462e77:	ff d0                	call   eax
  462e79:	89 9e 34 02 00 00    	mov    DWORD PTR [esi+0x234],ebx
  462e7f:	8b be 2c 02 00 00    	mov    edi,DWORD PTR [esi+0x22c]
  462e85:	3b fb                	cmp    edi,ebx
  462e87:	74 16                	je     0x462e9f
  462e89:	8b cf                	mov    ecx,edi
  462e8b:	e8 20 05 24 00       	call   0x6a33b0
  462e90:	57                   	push   edi
  462e91:	e8 9a 3a 42 00       	call   0x886930
  462e96:	83 c4 04             	add    esp,0x4
  462e99:	89 9e 2c 02 00 00    	mov    DWORD PTR [esi+0x22c],ebx
  462e9f:	8b be c0 01 00 00    	mov    edi,DWORD PTR [esi+0x1c0]
  462ea5:	3b fb                	cmp    edi,ebx
  462ea7:	74 16                	je     0x462ebf
  462ea9:	8b cf                	mov    ecx,edi
  462eab:	e8 70 30 22 00       	call   0x685f20
  462eb0:	57                   	push   edi
  462eb1:	e8 7a 3a 42 00       	call   0x886930
  462eb6:	83 c4 04             	add    esp,0x4
  462eb9:	89 9e c0 01 00 00    	mov    DWORD PTR [esi+0x1c0],ebx
  462ebf:	8b be c4 01 00 00    	mov    edi,DWORD PTR [esi+0x1c4]
  462ec5:	3b fb                	cmp    edi,ebx
  462ec7:	74 16                	je     0x462edf
  462ec9:	8b cf                	mov    ecx,edi
  462ecb:	e8 50 30 22 00       	call   0x685f20
  462ed0:	57                   	push   edi
  462ed1:	e8 5a 3a 42 00       	call   0x886930
  462ed6:	83 c4 04             	add    esp,0x4
  462ed9:	89 9e c4 01 00 00    	mov    DWORD PTR [esi+0x1c4],ebx
  462edf:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  462ee2:	3b cb                	cmp    ecx,ebx
  462ee4:	74 0b                	je     0x462ef1
  462ee6:	8b 11                	mov    edx,DWORD PTR [ecx]
  462ee8:	8b 02                	mov    eax,DWORD PTR [edx]
  462eea:	6a 01                	push   0x1
  462eec:	ff d0                	call   eax
  462eee:	89 5e 0c             	mov    DWORD PTR [esi+0xc],ebx
  462ef1:	8b 8e 4c 0c 00 00    	mov    ecx,DWORD PTR [esi+0xc4c]
  462ef7:	3b cb                	cmp    ecx,ebx
  462ef9:	74 0e                	je     0x462f09
  462efb:	8b 11                	mov    edx,DWORD PTR [ecx]
  462efd:	8b 02                	mov    eax,DWORD PTR [edx]
  462eff:	6a 01                	push   0x1
  462f01:	ff d0                	call   eax
  462f03:	89 9e 4c 0c 00 00    	mov    DWORD PTR [esi+0xc4c],ebx
  462f09:	8b be 5c 0c 00 00    	mov    edi,DWORD PTR [esi+0xc5c]
  462f0f:	3b fb                	cmp    edi,ebx
  462f11:	74 10                	je     0x462f23
  462f13:	8b cf                	mov    ecx,edi
  462f15:	e8 d6 7d 22 00       	call   0x68acf0
  462f1a:	57                   	push   edi
  462f1b:	e8 10 3a 42 00       	call   0x886930
  462f20:	83 c4 04             	add    esp,0x4
  462f23:	8b be 34 0d 00 00    	mov    edi,DWORD PTR [esi+0xd34]
  462f29:	3b fb                	cmp    edi,ebx
  462f2b:	74 18                	je     0x462f45
  462f2d:	8d 4f 4c             	lea    ecx,[edi+0x4c]
  462f30:	e8 1b d1 08 00       	call   0x4f0050
  462f35:	8b cf                	mov    ecx,edi
  462f37:	e8 d4 c5 1e 00       	call   0x64f510
  462f3c:	57                   	push   edi
  462f3d:	e8 ee 39 42 00       	call   0x886930
  462f42:	83 c4 04             	add    esp,0x4
  462f45:	8b be 70 0c 00 00    	mov    edi,DWORD PTR [esi+0xc70]
  462f4b:	3b fb                	cmp    edi,ebx
  462f4d:	74 10                	je     0x462f5f
  462f4f:	8b cf                	mov    ecx,edi
  462f51:	e8 9a 7d 22 00       	call   0x68acf0
  462f56:	57                   	push   edi
  462f57:	e8 d4 39 42 00       	call   0x886930
  462f5c:	83 c4 04             	add    esp,0x4
  462f5f:	8d 9e 74 0c 00 00    	lea    ebx,[esi+0xc74]
  462f65:	c7 45 fc 0c 00 00 00 	mov    DWORD PTR [ebp-0x4],0xc
  462f6c:	8d 64 24 00          	lea    esp,[esp+0x0]
  462f70:	8b 3b                	mov    edi,DWORD PTR [ebx]
  462f72:	85 ff                	test   edi,edi
  462f74:	74 10                	je     0x462f86
  462f76:	8b cf                	mov    ecx,edi
  462f78:	e8 73 7d 22 00       	call   0x68acf0
  462f7d:	57                   	push   edi
  462f7e:	e8 ad 39 42 00       	call   0x886930
  462f83:	83 c4 04             	add    esp,0x4
  462f86:	83 c3 04             	add    ebx,0x4
  462f89:	83 6d fc 01          	sub    DWORD PTR [ebp-0x4],0x1
  462f8d:	75 e1                	jne    0x462f70
  462f8f:	8d be 60 0c 00 00    	lea    edi,[esi+0xc60]
  462f95:	c7 45 fc 04 00 00 00 	mov    DWORD PTR [ebp-0x4],0x4
  462f9c:	8d 64 24 00          	lea    esp,[esp+0x0]
  462fa0:	8b 1f                	mov    ebx,DWORD PTR [edi]
  462fa2:	85 db                	test   ebx,ebx
  462fa4:	74 10                	je     0x462fb6
  462fa6:	8b cb                	mov    ecx,ebx
  462fa8:	e8 43 7d 22 00       	call   0x68acf0
  462fad:	53                   	push   ebx
  462fae:	e8 7d 39 42 00       	call   0x886930
  462fb3:	83 c4 04             	add    esp,0x4
  462fb6:	83 c7 04             	add    edi,0x4
  462fb9:	83 6d fc 01          	sub    DWORD PTR [ebp-0x4],0x1
  462fbd:	75 e1                	jne    0x462fa0
  462fbf:	8b ce                	mov    ecx,esi
  462fc1:	e8 ba 82 ff ff       	call   0x45b280
  462fc6:	8b be a4 0c 00 00    	mov    edi,DWORD PTR [esi+0xca4]
  462fcc:	85 ff                	test   edi,edi
  462fce:	74 10                	je     0x462fe0
  462fd0:	8b cf                	mov    ecx,edi
  462fd2:	e8 19 7d 22 00       	call   0x68acf0
  462fd7:	57                   	push   edi
  462fd8:	e8 53 39 42 00       	call   0x886930
  462fdd:	83 c4 04             	add    esp,0x4
  462fe0:	8b be a8 0c 00 00    	mov    edi,DWORD PTR [esi+0xca8]
  462fe6:	85 ff                	test   edi,edi
  462fe8:	74 10                	je     0x462ffa
  462fea:	8b cf                	mov    ecx,edi
  462fec:	e8 ff 7c 22 00       	call   0x68acf0
  462ff1:	57                   	push   edi
  462ff2:	e8 39 39 42 00       	call   0x886930
  462ff7:	83 c4 04             	add    esp,0x4
  462ffa:	8d 8e 20 43 00 00    	lea    ecx,[esi+0x4320]
  463000:	e8 db f6 06 00       	call   0x4d26e0
  463005:	8d 8e 20 3f 00 00    	lea    ecx,[esi+0x3f20]
  46300b:	e8 b0 18 07 00       	call   0x4d48c0
  463010:	8d 8e e0 3b 00 00    	lea    ecx,[esi+0x3be0]
  463016:	e8 e5 ed 06 00       	call   0x4d1e00
  46301b:	8d 8e 60 38 00 00    	lea    ecx,[esi+0x3860]
  463021:	e8 8a f1 06 00       	call   0x4d21b0
  463026:	8d 8e e0 33 00 00    	lea    ecx,[esi+0x33e0]
  46302c:	e8 6f 23 07 00       	call   0x4d53a0
  463031:	8d 8e 20 2d 00 00    	lea    ecx,[esi+0x2d20]
  463037:	e8 14 3f 07 00       	call   0x4d6f50
  46303c:	8d 8e c0 29 00 00    	lea    ecx,[esi+0x29c0]
  463042:	e8 69 31 07 00       	call   0x4d61b0
  463047:	8d 8e 60 26 00 00    	lea    ecx,[esi+0x2660]
  46304d:	e8 ae 04 07 00       	call   0x4d3500
  463052:	8d 8e e0 22 00 00    	lea    ecx,[esi+0x22e0]
  463058:	e8 83 12 07 00       	call   0x4d42e0
  46305d:	8d 8e a0 1f 00 00    	lea    ecx,[esi+0x1fa0]
  463063:	e8 88 fb 06 00       	call   0x4d2bf0
  463068:	8d 8e 40 1c 00 00    	lea    ecx,[esi+0x1c40]
  46306e:	e8 5d 01 07 00       	call   0x4d31d0
  463073:	8d 8e 40 18 00 00    	lea    ecx,[esi+0x1840]
  463079:	e8 62 09 07 00       	call   0x4d39e0
  46307e:	8d 8e e0 14 00 00    	lea    ecx,[esi+0x14e0]
  463084:	e8 c7 59 0a 00       	call   0x508a50
  463089:	8d 8e a0 11 00 00    	lea    ecx,[esi+0x11a0]
  46308f:	e8 5c fe 06 00       	call   0x4d2ef0
  463094:	8d 8e 60 0e 00 00    	lea    ecx,[esi+0xe60]
  46309a:	e8 21 ea 06 00       	call   0x4d1ac0
  46309f:	8d 8e b0 0d 00 00    	lea    ecx,[esi+0xdb0]
  4630a5:	e8 76 6a 0a 00       	call   0x509b20
  4630aa:	8d 8e 2c 0d 00 00    	lea    ecx,[esi+0xd2c]
  4630b0:	e8 2b 06 24 00       	call   0x6a36e0
  4630b5:	8d be b0 0c 00 00    	lea    edi,[esi+0xcb0]
  4630bb:	8b cf                	mov    ecx,edi
  4630bd:	e8 3e 79 41 00       	call   0x87aa00
  4630c2:	8b cf                	mov    ecx,edi
  4630c4:	e8 27 0d 49 00       	call   0x8f3df0
  4630c9:	8d 8e e0 09 00 00    	lea    ecx,[esi+0x9e0]
  4630cf:	e8 4c 02 1d 00       	call   0x633320
  4630d4:	8d 8e 80 07 00 00    	lea    ecx,[esi+0x780]
  4630da:	e8 41 02 1d 00       	call   0x633320
  4630df:	8d 8e 20 05 00 00    	lea    ecx,[esi+0x520]
  4630e5:	e8 46 28 1c 00       	call   0x625930
  4630ea:	8d 8e c0 02 00 00    	lea    ecx,[esi+0x2c0]
  4630f0:	e8 2b 02 1d 00       	call   0x633320
  4630f5:	8d 4e 04             	lea    ecx,[esi+0x4]
  4630f8:	c7 46 08 80 87 b0 00 	mov    DWORD PTR [esi+0x8],0xb08780
  4630ff:	e8 1c e5 3a 00       	call   0x811620
  463104:	8b ce                	mov    ecx,esi
  463106:	e8 a5 ba fa ff       	call   0x40ebb0
  46310b:	5f                   	pop    edi
  46310c:	5e                   	pop    esi
  46310d:	5b                   	pop    ebx
  46310e:	8b e5                	mov    esp,ebp
  463110:	5d                   	pop    ebp
  463111:	c3                   	ret
```


### 5. Deleting wrapper 0x00464200–0x0046421E (14 строк с адресами)

```asm
  464200:	55                   	push   ebp
  464201:	8b ec                	mov    ebp,esp
  464203:	56                   	push   esi
  464204:	8b f1                	mov    esi,ecx
  464206:	e8 15 ec ff ff       	call   0x462e20
  46420b:	f6 45 08 01          	test   BYTE PTR [ebp+0x8],0x1
  46420f:	74 09                	je     0x46421a
  464211:	56                   	push   esi
  464212:	e8 19 27 42 00       	call   0x886930
  464217:	83 c4 04             	add    esp,0x4
  46421a:	8b c6                	mov    eax,esi
  46421c:	5e                   	pop    esi
  46421d:	5d                   	pop    ebp
  46421e:	c2 04 00             	ret    0x4
```


### 6. Actual global-pointer access 0x0040CFC0–0x0040D034 (27 строк с адресами)

```asm
  40cfc0:	84 c9                	test   cl,cl
  40cfc2:	74 53                	je     0x40d017
  40cfc4:	a1 5c 18 bc 00       	mov    eax,ds:0xbc185c
  40cfc9:	80 b8 20 0d 00 00 00 	cmp    BYTE PTR [eax+0xd20],0x0
  40cfd0:	75 62                	jne    0x40d034
  40cfd2:	f6 05 30 d0 bb 00 01 	test   BYTE PTR ds:0xbbd030,0x1
  40cfd9:	75 1e                	jne    0x40cff9
  40cfdb:	83 0d 30 d0 bb 00 01 	or     DWORD PTR ds:0xbbd030,0x1
  40cfe2:	b9 00 c6 bb 00       	mov    ecx,0xbbc600
  40cfe7:	e8 a4 34 00 00       	call   0x410490
  40cfec:	68 60 ae a9 00       	push   0xa9ae60
  40cff1:	e8 bd 3f 4f 00       	call   0x900fb3
  40cff6:	83 c4 04             	add    esp,0x4
  40cff9:	83 3d 10 c6 bb 00 0a 	cmp    DWORD PTR ds:0xbbc610,0xa
  40d000:	7d 32                	jge    0x40d034
  40d002:	8b 0d 5c 18 bc 00    	mov    ecx,DWORD PTR ds:0xbc185c
  40d008:	6a 01                	push   0x1
  40d00a:	e8 f1 53 05 00       	call   0x462400
  40d00f:	c6 05 c4 14 bc 00 01 	mov    BYTE PTR ds:0xbc14c4,0x1
  40d016:	c3                   	ret
  40d017:	80 3d c4 14 bc 00 00 	cmp    BYTE PTR ds:0xbc14c4,0x0
  40d01e:	74 14                	je     0x40d034
  40d020:	8b 0d 5c 18 bc 00    	mov    ecx,DWORD PTR ds:0xbc185c
  40d026:	6a 00                	push   0x0
  40d028:	e8 d3 53 05 00       	call   0x462400
  40d02d:	c6 05 c4 14 bc 00 00 	mov    BYTE PTR ds:0xbc14c4,0x0
  40d034:	c3                   	ret
```


### 7. Potential vcall-pattern context 0x0040BA50–0x0040BB38 (82 строк с адресами)

```asm
  40ba50:	56                   	push   esi
  40ba51:	8b f1                	mov    esi,ecx
  40ba53:	8b 06                	mov    eax,DWORD PTR [esi]
  40ba55:	8b 50 48             	mov    edx,DWORD PTR [eax+0x48]
  40ba58:	ff d2                	call   edx
  40ba5a:	85 c0                	test   eax,eax
  40ba5c:	0f 85 d5 00 00 00    	jne    0x40bb37
  40ba62:	53                   	push   ebx
  40ba63:	57                   	push   edi
  40ba64:	8d 9e 20 06 00 00    	lea    ebx,[esi+0x620]
  40ba6a:	8d 9b 00 00 00 00    	lea    ebx,[ebx+0x0]
  40ba70:	80 be 0d 14 00 00 00 	cmp    BYTE PTR [esi+0x140d],0x0
  40ba77:	74 2e                	je     0x40baa7
  40ba79:	e8 e2 8f 48 00       	call   0x894a60
  40ba7e:	85 c0                	test   eax,eax
  40ba80:	74 12                	je     0x40ba94
  40ba82:	e8 d9 8f 48 00       	call   0x894a60
  40ba87:	8b 10                	mov    edx,DWORD PTR [eax]
  40ba89:	8b c8                	mov    ecx,eax
  40ba8b:	8b 42 04             	mov    eax,DWORD PTR [edx+0x4]
  40ba8e:	ff d0                	call   eax
  40ba90:	84 c0                	test   al,al
  40ba92:	75 13                	jne    0x40baa7
  40ba94:	e8 d7 fd ff ff       	call   0x40b870
  40ba99:	8b 38                	mov    edi,DWORD PTR [eax]
  40ba9b:	8b c8                	mov    ecx,eax
  40ba9d:	8b 47 44             	mov    eax,DWORD PTR [edi+0x44]
  40baa0:	ba 01 00 00 00       	mov    edx,0x1
  40baa5:	ff d0                	call   eax
  40baa7:	8b ce                	mov    ecx,esi
  40baa9:	e8 22 d8 23 00       	call   0x6492d0
  40baae:	e8 cd c4 0f 00       	call   0x507f80
  40bab3:	8b c8                	mov    ecx,eax
  40bab5:	e8 36 c4 23 00       	call   0x647ef0
  40baba:	53                   	push   ebx
  40babb:	8b ce                	mov    ecx,esi
  40babd:	e8 de a2 ff ff       	call   0x405da0
  40bac2:	8b 16                	mov    edx,DWORD PTR [esi]
  40bac4:	8b 42 40             	mov    eax,DWORD PTR [edx+0x40]
  40bac7:	8b ce                	mov    ecx,esi
  40bac9:	ff d0                	call   eax
  40bacb:	e8 20 e5 ff ff       	call   0x409ff0
  40bad0:	8b f8                	mov    edi,eax
  40bad2:	85 ff                	test   edi,edi
  40bad4:	74 4e                	je     0x40bb24
  40bad6:	e8 55 b5 3f 00       	call   0x807030
  40badb:	d9 05 3c 9b aa 00    	fld    DWORD PTR ds:0xaa9b3c
  40bae1:	51                   	push   ecx
  40bae2:	33 d2                	xor    edx,edx
  40bae4:	d9 1c 24             	fstp   DWORD PTR [esp]
  40bae7:	8b c8                	mov    ecx,eax
  40bae9:	e8 a2 b2 3f 00       	call   0x806d90
  40baee:	8b 17                	mov    edx,DWORD PTR [edi]
  40baf0:	8b 42 04             	mov    eax,DWORD PTR [edx+0x4]
  40baf3:	8b cf                	mov    ecx,edi
  40baf5:	ff d0                	call   eax
  40baf7:	85 c0                	test   eax,eax
  40baf9:	74 09                	je     0x40bb04
  40bafb:	8b 17                	mov    edx,DWORD PTR [edi]
  40bafd:	8b 42 08             	mov    eax,DWORD PTR [edx+0x8]
  40bb00:	8b cf                	mov    ecx,edi
  40bb02:	ff d0                	call   eax
  40bb04:	e8 27 b5 3f 00       	call   0x807030
  40bb09:	33 d2                	xor    edx,edx
  40bb0b:	8b c8                	mov    ecx,eax
  40bb0d:	e8 5e b2 3f 00       	call   0x806d70
  40bb12:	84 c0                	test   al,al
  40bb14:	74 0e                	je     0x40bb24
  40bb16:	e8 15 b5 3f 00       	call   0x807030
  40bb1b:	33 d2                	xor    edx,edx
  40bb1d:	8b c8                	mov    ecx,eax
  40bb1f:	e8 ac b3 3f 00       	call   0x806ed0
  40bb24:	8b 16                	mov    edx,DWORD PTR [esi]
  40bb26:	8b 42 48             	mov    eax,DWORD PTR [edx+0x48]
  40bb29:	8b ce                	mov    ecx,esi
  40bb2b:	ff d0                	call   eax
  40bb2d:	85 c0                	test   eax,eax
  40bb2f:	0f 84 3b ff ff ff    	je     0x40ba70
  40bb35:	5f                   	pop    edi
  40bb36:	5b                   	pop    ebx
  40bb37:	5e                   	pop    esi
  40bb38:	c3                   	ret
```
