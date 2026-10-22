# Process 1 — retail adapter EndStateBlock at 0x0084FBF0

**Дата:** 2026-10-22. **Scope:** ограниченный статический аудит EndStateBlock adapter метода `0x0084FBF0`, его непосредственно смежной BeginStateBlock-пары `0x0084FBC0`, их двух primary-vtable записей и ближайшего конструктора `0x00850100`. Не является новым глобальным setter audit или повтором анализа `0x0084F000`. Никаких изменений runtime/P-code, guest state, renderer или исходного кода.

**Оригинальный PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **SHA-256**, перепроверен по загруженному `SHIFT.exe`: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Источники: оригинальный исполняемый файл, его `SHIFT_objdump_full.txt`, PE `.rdata` и предшествующий проверенный отчёт с commit `74c39dbe2d8352c9ec2063db2815cfc96d788b19` ([предыдущий отчёт](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process1b-adapter-state-sync-0084f000.md)). Приложены **полные** objdump обеих функций bracket и конструктора. Не проводился новый controlled replay.

## Вывод

**Полностью доказан локальный механический контракт `save(+4)→+5; +4=0; BeginStateBlock` и `restore(+5)→+4; EndStateBlock`.** Эти функции находятся в соседних **primary** vtable слотах одного установленного класса, и их underlying target согласован с реальным D3D9 device pointer из `CreateDevice`. Однако **не найден конкретный исполняемый внешний caller или ordered control-flow chain, который доказывает вызов Begin, затем End на том же adapter instance.** Поэтому корректное утверждение: *класс предоставляет сопряжённые Begin/EndStateBlock-обёртки; нормальный динамический bracket возможен, но не доказан как достигаемая/исполненная последовательность*. В этом ограниченном пути также **нет установленного самостоятельного nonzero producer для `BYTE[adapter+5]`**: единственная подтверждённая запись в это поле берёт исходный байт `BYTE[adapter+4]`, а constructor фиксирует `+4=0`.

## 1. Exact ABI, stack offsets, return, cleanup

**`0x0084FBF0` — stack-argument, callee-cleanup wrapper** (не ECX=this): `[EBP+8]=adapter`, `[EBP+0xC]=ppStateBlock` (DWORD pointer, destination for `IDirect3DStateBlock9*`); `RET 0x8` освобождает два DWORD. Входной ECX не используется как object `this`. Пролог `PUSH EBP; MOV EBP,ESP`, локального stack frame и сохранённых EBX/ESI/EDI нет. Перезаписывает volatile `EAX,ECX,EDX`; EAX после вызова нижнего COM метода возвращается **без нормализации** (типично HRESULT, не bool).

Инструкции:
- `0x0084FBF3`: `EAX=DWORD[EBP+8]`, то есть adapter.
- `0x0084FBF6`: `CL=BYTE[adapter+5]`. `0x0084FBF9`: **`BYTE[adapter+4]=CL`**, непосредственно *до* обращения к device; сохранённый `+5` **не очищается**.
- `0x0084FBFC`: `EAX=DWORD[adapter+8]`, underlying device. `0x0084FBFF`: `ECX=DWORD[EBP+0xC]`, выходной аргумент `ppStateBlock`.
- `0x0084FC02–0x0084FC04`: `EDX=DWORD[device]`; `EDX=DWORD[EDX+0xF4]`.
- `0x0084FC0A`: `PUSH ppStateBlock`; `0x0084FC0B`: `PUSH device`; `0x0084FC0C`: `CALL EDX`. Подлежащее обычное COM `IDirect3DDevice9::EndStateBlock(IDirect3DStateBlock9**)` ожидает `device this` и один stack argument, обычный callee cleanup **восемь байт** для этого вызова. Внешняя wrapper-функция затем делает `POP EBP; RET 8`: очищает **собственные** два аргумента; двойной cleanup не возникает, так как вызовы имеют разные кадры.
- **Единственный exit**: `0x0084FC0E: POP EBP; 0x0084FC0F: RET 8` (инструкция RET занимает байты до `0x0084FC11`). В данном wrapper **нет проверки return HRESULT**, guard, дополнительной обработки `ppStateBlock`, аллокации или cleanup объекта state block. Нулевые `adapter` и `device` не проверяются здесь, возможное обращение к ним требует валидного вызывающего контракта.

**`0x0084FBC0` — симметричный wrapper BeginStateBlock:** `[EBP+8]=adapter`, `RET 4`; `0x0084FBC6–0x0084FBCC`: `CL=BYTE[adapter+4]`, `BYTE[adapter+5]=CL`, `BYTE[adapter+4]=0`; после этого `EAX=[adapter+8]`, `F=[[device]+0xF0]`, `PUSH device; CALL F`. Протягивает конечный EAX, не проверяет HRESULT, нет условного выхода. **Сохранение и обнуление происходят даже если underlying BeginStateBlock вернёт ошибку.** Restoration в `0x0084FBF0` также происходит до получения HRESULT End.

Это **не** регистровый `__thiscall(ECX=adapter)` контракт: обоим adapter methods нужен аргумент `adapter` на стеке; соответствующие обращения к виртуальным методам должны поместить его как explicit stack `this`. Формально входные функции ABI совместимы с `stdcall` (1 параметр для Begin, 2 для End), а внутренняя device COM функция — тоже callee-cleanup stdcall.

## 2. Exact same-class vtable and device identity

Конструктор `0x00850100` пишет при **0x00850109** `DWORD[adapter]=0x00B1BBA8`, при `0x0085010F` `DWORD[adapter+8]=[EBP+8]` (полученный device pointer). PE `.rdata` содержит следующие **проверенные little-endian DWORD**:

| Адрес DWORD | Относительно primary vptr 0x00B1BBA8 | Original 4 bytes | Значение | Роль |
|---|---|---|---|---|
| **0x00B1BC98** | **+0xF0 (index 60)** | `c0 fb 84 00` | **0x0084FBC0** | Adapter `BeginStateBlock` |
| **0x00B1BC9C** | **+0xF4 (index 61)** | `f0 fb 84 00` | **0x0084FBF0** | Adapter `EndStateBlock` |

Оригинальный PE также связывает `adapter+8` с устройством из `IDirect3D9::CreateDevice`: запись в adapter при `0x0084E2DD` и соответствующий CreateDevice-flow `0x0083304D–0x0083309E` установлены в предыдущем отчёте. Внутри функций рассматриваемого scope **две раздельные виртуальные операции**: (а) потенциальное внешнее обращение к **adapter.vptr +0xF0/+0xF4**, (б) **device.vptr +0xF0/+0xF4** внутри функций. Эти vptr **разные**. Идентификация внутренних функций `IDirect3DDevice9::BeginStateBlock` и `IDirect3DDevice9::EndStateBlock` поддержана device-provenance, соседними COM слотами и точными 0/1 explicit stack args. Она не выводится лишь из совпадения offset у произвольного объекта.

**Доказанные маршруты входа на уровне данных**:
```text
adapter = pointer to object initialized by 0x00850100
adapter.vptr = 0x00B1BBA8
DWORD[adapter.vptr+0xF0] = 0x0084FBC0
DWORD[adapter.vptr+0xF4] = 0x0084FBF0

virtual Begin invocation, if present:
    push adapter
    CALL DWORD[DWORD[adapter]+0xF0]  →  0x0084FBC0
    save adapter+4→+5; clear +4; call device.vptr+0xF0

virtual End invocation, if present:
    push ppStateBlock; push adapter
    CALL DWORD[DWORD[adapter]+0xF4]  →  0x0084FBF0
    restore adapter+5→+4; call device.vptr+0xF4
```

Эти псевдоинструкции обозначают **условие вызова** из существующей vtable, **не** найденный кодовый site. В частности, нельзя использовать любой текстовый `[reg+0xF4]` из полного objdump, чтобы утверждать вызов `0x0084FBF0`, пока неизвестен происхождение receiver/vptr.

## 3. Bounded executable caller search and bracket confidence

Проверен **весь поставленный `SHIFT_objdump_full.txt`** на точные прямые `CALL rel32` цели `0x0084FBC0` и `0x0084FBF0`: **0 и 0**. Поиск оригинальных четырёх байтов значений `c0 fb 84 00` и `f0 fb 84 00` по **всему PE-файлу** нашёл ровно по **одному** вхождению: PE file offsets **`0x71A698` и `0x71A69C`** соответственно (две `.rdata` vtable ячейки). Это **подтверждает два static target pointers в таблице**, но не исключает работу с target через indirect calls.

Для оценки смешения layout были проверены **все текстовые обращения с `+0xF0]` и `+0xF4]`** в полном линейном objdump: **486 и 399 инструкций/строк** соответственно. Эти выражения включают ordinary data members и vtable slots **других типов**; реальное `adapter.vptr=0x00B1BBA8` при конкретном caller из них **не доказано**. Это scan исходных декодированных инструкций, **не** межпроцедурный alias analysis, не полный CFG для перекрывающихся code bytes. Строго ограниченный разбор candidate windows не установил callsite, который можно назвать исполнителем **именно этого** adapter class method.

**Bracket ledger:** 
- **Высокая уверенность в *семантике пары методов***: vtable index 60/61 одного класса, save/clear и restore, underlying D3D9 Begin/End signature. Это **конкретный аналог нормального D3D9 state-block bracket**.
- **Недоказанный факт исполнения и порядка:** нет подтверждённого caller sequence `Begin → End` для **одного adapter instance**, нет runtime v755/v756 event по этим targets, нет доказательства, что каждый End preceded Begin. End сам не проверяет предшествующий Begin и не читает bracket counter; его `adapter+5` может быть прочитано без локально доказанного сохранения в данной трассе. Это ограничение доказательства, не утверждение о реальной ошибке.

## 4. Nonzero source for adapter+5: local class audit

Из близких *однозначно идентифицированных* методов этого adapter class имеются следующие операции:

| Функция / инструкция | Write/Read | Доказанный value-flow |
|---|---|---|
| `0x00850176` constructor | **write `BYTE[adapter+4]=0`** | Создаваемый объект на выходе имеет нулевой `+4` |
| `0x0084FBC6` | **read adapter+4** | Берёт исходное значение непосредственно перед Begin |
| **`0x0084FBC9`** | **write adapter+5** | `adapter+5 := old adapter+4`; значение никак не устанавливается константой 1 |
| `0x0084FBCC` | **write adapter+4=0** | Временное принудительное обнуление на самой Begin-wrapper |
| `0x0084FBF6` | **read adapter+5** | Чтение saved byte перед End |
| **`0x0084FBF9`** | **write adapter+4** | `adapter+4 := saved adapter+5`; End не меняет saved byte |

**Ближайший constructor не инициализирует `adapter+5` явно.** Следовательно, для **ненулевого** сохранения в `0x0084FBC9` нужен **ранее ненулевой adapter+4** или другой alias/write в `adapter+5`. Ни тот, ни другой производитель не установлен в этом узком классовом пути. Если `adapter+4=0` перед Begin, непосредственно показанная последовательность сохраняет ноль и End восстанавливает ноль. Это **условное следствие байтов**, а не runtime-утверждение о v755/v756.

Ограниченный scan `.text` interval `0x0084E000–0x0085017E` также обнаружил похожие операции с полями `+4` у **других receiver types**. Например, соседняя инициализация `0x00850190` относится к **другому вложенному объекту** с vptr `0x00B1BD88`, поэтому его `+4/+5` не следует смешивать с байтами adapter primary object. Внутри подтверждённых методов adapter из таблицы выше **нет показанного producer ненулевой константы**. Этот scan не покрывает внешние callback/aliases, сохранение необработанного указателя во внешней памяти и runtime-initialized writes; **не делается вывод об отсутствии любых других writers**.

## 5. Given v755/v756 observations — not new measurements

Пользователем предоставлено: предыдущие bounded v755/v756 controlled P-code traces не дошли до Draw path. Эти выборки **не содержат прямой измеренной цепочки входов** в adapter `0x0084FBC0` или `0x0084FBF0`, значения `adapter+4/+5` на входе либо одного pair-instance ID; **никакой положительной или отрицательной runtime частоты Begin/End из них не следует**. Новый replay в рамках этой задачи не запускался.

**Proven PE:** original SHA and exact complete code of both adapter wrappers; stack ABI and `RET 8` / `RET 4`; device pointer flow and COM-call shape; primary vtable entries, constructor `+4=0`; bounded static reference results and complementary class-local bytes.  
**Inference supported by behavior/COM interface:** these wrappers implement stateblock-style save/disable/restore around device Begin/End operations.  
**Unknown:** positive source for adapter+4 and adapter+5; dynamically ordered Begin→End caller; whether these methods execute in v755/v756; any renderer/UI causality. No gates or project-wide fail-closed constraints were modified.

## 6. Exactly one next evidence-backed target

**`0x0084FBC9`** — именно **store `BYTE[adapter+5]=CL`** внутри Begin-wrapper. Следующий read-only trace/target должен зафиксировать реальный caller, `[EBP+8]` adapter pointer, primary vptr `[adapter]`, входные `BYTE[adapter+4]` и `BYTE[adapter+5]` и сохраняемый `CL` **до записи**. Это непосредственно установит, бывает ли сохранение ненулевого значения и какой конкретный экземпляр задействован; отсутствие hits ограничивать проверенным временным окном. Никакого изменения guest state или расширения до глобального setter-аудита.

## Appendix — unabridged original PE objdump blocks, with bytes

### A. Begin-state adapter wrapper, 0x0084FBC0–0x0084FBDF

```asm
  84fbc0:	55                   	push   ebp
  84fbc1:	8b ec                	mov    ebp,esp
  84fbc3:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84fbc6:	8a 48 04             	mov    cl,BYTE PTR [eax+0x4]
  84fbc9:	88 48 05             	mov    BYTE PTR [eax+0x5],cl
  84fbcc:	c6 40 04 00          	mov    BYTE PTR [eax+0x4],0x0
  84fbd0:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84fbd3:	8b 10                	mov    edx,DWORD PTR [eax]
  84fbd5:	50                   	push   eax
  84fbd6:	8b 82 f0 00 00 00    	mov    eax,DWORD PTR [edx+0xf0]
  84fbdc:	ff d0                	call   eax
  84fbde:	5d                   	pop    ebp
  84fbdf:	c2 04 00             	ret    0x4
```

### B. End-state adapter wrapper, 0x0084FBF0–0x0084FC0F (RET extends to 0x0084FC11)

```asm
  84fbf0:	55                   	push   ebp
  84fbf1:	8b ec                	mov    ebp,esp
  84fbf3:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84fbf6:	8a 48 05             	mov    cl,BYTE PTR [eax+0x5]
  84fbf9:	88 48 04             	mov    BYTE PTR [eax+0x4],cl
  84fbfc:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84fbff:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84fc02:	8b 10                	mov    edx,DWORD PTR [eax]
  84fc04:	8b 92 f4 00 00 00    	mov    edx,DWORD PTR [edx+0xf4]
  84fc0a:	51                   	push   ecx
  84fc0b:	50                   	push   eax
  84fc0c:	ff d2                	call   edx
  84fc0e:	5d                   	pop    ebp
  84fc0f:	c2 08 00             	ret    0x8
```

### C. Adapter constructor, 0x00850100–0x0085017E

```asm
  850100:	55                   	push   ebp
  850101:	8b ec                	mov    ebp,esp
  850103:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  850106:	56                   	push   esi
  850107:	8b f1                	mov    esi,ecx
  850109:	c7 06 a8 bb b1 00    	mov    DWORD PTR [esi],0xb1bba8
  85010f:	89 46 08             	mov    DWORD PTR [esi+0x8],eax
  850112:	e8 d9 9f bb ff       	call   0x40a0f0
  850117:	33 c9                	xor    ecx,ecx
  850119:	89 86 e0 19 00 00    	mov    DWORD PTR [esi+0x19e0],eax
  85011f:	ba 08 00 00 00       	mov    edx,0x8
  850124:	f7 e2                	mul    edx
  850126:	0f 90 c1             	seto   cl
  850129:	f7 d9                	neg    ecx
  85012b:	0b c8                	or     ecx,eax
  85012d:	51                   	push   ecx
  85012e:	e8 8d 67 03 00       	call   0x8868c0
  850133:	89 86 dc 19 00 00    	mov    DWORD PTR [esi+0x19dc],eax
  850139:	c7 00 20 00 00 00    	mov    DWORD PTR [eax],0x20
  85013f:	8b 86 dc 19 00 00    	mov    eax,DWORD PTR [esi+0x19dc]
  850145:	c7 40 08 10 00 00 00 	mov    DWORD PTR [eax+0x8],0x10
  85014c:	8b 8e dc 19 00 00    	mov    ecx,DWORD PTR [esi+0x19dc]
  850152:	c7 41 10 30 00 00 00 	mov    DWORD PTR [ecx+0x10],0x30
  850159:	8b 96 dc 19 00 00    	mov    edx,DWORD PTR [esi+0x19dc]
  85015f:	c7 42 18 08 00 00 00 	mov    DWORD PTR [edx+0x18],0x8
  850166:	8b 86 dc 19 00 00    	mov    eax,DWORD PTR [esi+0x19dc]
  85016c:	c7 40 20 38 00 00 00 	mov    DWORD PTR [eax+0x20],0x38
  850173:	83 c4 04             	add    esp,0x4
  850176:	c6 46 04 00          	mov    BYTE PTR [esi+0x4],0x0
  85017a:	8b c6                	mov    eax,esi
  85017c:	5e                   	pop    esi
  85017d:	5d                   	pop    ebp
  85017e:	c2 04 00             	ret    0x4
```
