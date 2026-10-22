# Process 1 — retail adapter state synchronization at 0x0084F000

**Дата:** 2026-10-22. **Область:** один helper `0x0084F000–0x0084F3AF`, ближайшие методы того же adapter class для `+4`; без нового исследования forwarder, UI gate, renderer или глобальных setters.  
**PE:** Need for Speed SHIFT PC retail 1.02; PE32 x86; ImageBase `0x00400000`.  
**SHA-256 оригинального `SHIFT.exe`, проверен локально:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Источники:** пользовательский полный retail objdump, независимо проверенный по загруженному `SHIFT.exe` через `objdump -D -Mintel -w`, `SHIFT_objdump_full.txt`, байты vtable в PE `.rdata`, переданная сводка v755; сигнатуры `IDirect3DDevice9` сверены с официальным перечислением Microsoft и публичной индексной таблицей (ссылки ниже). **Replay не запускался; код, runtime/P-code, renderer, флаги и поля не изменялись.**

## Классификация

**`0x0084F000` — синхронизатор накопленного adapter state/cache с underlying `IDirect3DDevice9`, а не функция отправки примитивов.** В его полном исполнительном блоке **нет ни одной `CALL rel32` и нет вызова слотов DrawPrimitive (+0x144), DrawIndexedPrimitive (+0x148), DrawPrimitiveUP (+0x14C), DrawIndexedPrimitiveUP (+0x150)**. Все **12 косвенных `CALL`** читают слоты реального underlying device из `EBX=[adapter+8]` и вызывают state/bind методы с совместимыми stack ABI. Это отрицательный результат **только для данного helper**, не для его вызывающего `0x0084FD60`, который после helper самостоятельно вызывает DrawIndexedPrimitive.

**Предыдущий доказанный тип указателя сохраняется:** отдельный retail путь `IDirect3D9::CreateDevice` в `0x0083304D–0x0083306C` выдаёт device pointer, `0x00833095–0x0083309E` передаёт его в `0x0084E2C0`, и `0x0084E2DD` сохраняет в `adapter+8`. `0x00850100` устанавливает primary vptr `0x00B1BBA8`, PE `DWORD[0x00B1BCF0]=0x0084FD60`. Таким образом **идентификация методов D3D9 ниже опирается на CreateDevice-объект + корректную stack-arity + независимый интерфейсный порядок, а не на равенство смещений любых объектов**. Для подменённого в runtime pointer/vtable динамической идентичности здесь не установлено.

## ABI, frame, control and return effects

- **Вход:** `ECX=adapter` (после 0x0084F008 это ESI); **никаких stack args**. `EBX=DWORD[adapter+8]` — underlying COM device, загружается на 0x0084F011. Сохраняются EBP, EBX, ESI, EDI. Frame: `push EBP; mov EBP,ESP; sub ESP,0x10` создаёт **16 байт locals**: `[EBP-4]` указатель/индекс, `[EBP-8]` loop index, `[EBP-0xC]` state index, `[EBP-0x10]` cached value.
- **Выход:** единственный эпилог `0x0084F3A9–0x0084F3AF`, `RET` без стековой очистки аргументов. **EAX не нормализован** и обычно содержит последнюю промежуточную величину/результат; это не доказанный HRESULT либо Boolean. Множественные ветви идут к одному эпилогу; **собственной ветви failure return нет**, результаты device calls не проверяются перед обновлением cache.
- **Флаг `DWORD[adapter+0x19D8]`:** `bit2 (mask 0x4)` разрешает texture/sampler batch, `bit1 (0x2)` — streams/index/vertex declaration/FVF batch, `bit0 (0x1)` — render targets/depth-stencil/viewport batch. Но **две shader cache-пары и render-state queue обрабатываются независимо от этих трёх битов**, даже когда флаг равен нулю.
- В `0x0084F1A3–0x0084F1B5` значение DWORD флага читается и, после обнуления очереди render states, **если весь DWORD равен нулю**, управление идёт на эпилог `0x0084F3A9`; иначе после условных групп завершается `0x0084F39F: mov [adapter+0x19D8],0`. При чистом `bit2/bit1/bit0` могут присутствовать и другие биты: обработка указанных групп обусловлена именно масками; в конце сбрасывается **весь DWORD**.
- Важно: в вызывающем forwarder `0x0084FD60` вход в helper регулируется **другим полем `BYTE[adapter+4]`**; **этот helper вообще не пишет `adapter+4`**. Нет оснований отождествлять guard byte +4 и маску +0x19D8.

## Полный список виртуальных device calls и exact arguments

Здесь `D=DWORD[adapter+8]=EBX`, `V=DWORD[D]`, `CALL DWORD[V+offset]`, с `push D` как первым stack параметром callee `this`. Все вызовы — обычные **D3D9 COM stdcall** при сохранении device identity; полное соответствие stack-параметров дано ниже.

| Callsite | COM slot (index) | Method | Аргументы после device `this`, в порядке callee |
|---|---|---|---|
| **0x0084F045** | `+0x104` (65) | `SetTexture` | stage=`i` из `[adapter+0x1988]` (позже индекс), texture=`[adapter+0x1908+4*i]` |
| **0x0084F0BC** | `+0x114` (69) | `SetSamplerState` | sampler=`record>>16`, state=`record&0xF`, value=`[adapter+0xF8C+4*(sampler*16+state)]` |
| **0x0084F105** | `+0x1AC` (107) | `SetPixelShader` | shader=`[adapter+0x1890]` |
| **0x0084F12B** | `+0x170` (92) | `SetVertexShader` | shader=`[adapter+0x1898]` |
| **0x0084F172** | `+0x0E4` (57) | `SetRenderState` | state ID=`DWORD[dirtyList+4*i]` (`dirtyList=adapter+0x69C`), value=`[adapter+0x0C+4*stateID]` |
| **0x0084F203** | `+0x190` (100) | `SetStreamSource` | stream=`i` (0 или 1), buffer=`[EDI-0x24]`, offset=`[EDI-0x20]`, stride=`[EDI-0x1C]` (`EDI=adapter+0x19B8+i*0x10`) |
| **0x0084F232** | `+0x1A0` (104) | `SetIndices` | indexBuffer=`[adapter+0x19D0]` |
| **0x0084F258** | `+0x15C` (87) | `SetVertexDeclaration` | decl=`[adapter+0x18A8]` |
| **0x0084F280** | `+0x164` (89) | `SetFVF` | FVF=`[adapter+0x18A0]` |
| **0x0084F2B8** | `+0x094` (37) | `SetRenderTarget` | targetIndex=`i` (0..3), surface=`[adapter+0x18B0+4*i]` |
| **0x0084F2E8** | `+0x09C` (39) | `SetDepthStencilSurface` | surface=`[adapter+0x18D0]` |
| **0x0084F368** | `+0x0BC` (47) | `SetViewport` | pointer to six-DWORD viewport at `adapter+0x18D8` |

Это **все 12 executable CALL** внутри `0x0084F000–0x0084F3AF`. Следствие: именно **установка состояния/bindings**, а не Draw*. Для проверки идентификации использованы совместно device происхождение, аргументы `push` в данном objdump и спецификация D3D9; reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nn-d3d9-idirect3ddevice9 и индексированная COM-таблица https://docs.hsp.moe/Win32API/iface/Windows.Win32.Graphics.Direct3D9/IDirect3DDevice9.html . Внешняя таблица **не** подменяет байтовое доказательство receiver.

## Exact branches, adapter reads/writes, cache effects

### Group A — mask 0x4, textures / samplers (0x0084F00A–0x0084F0ED)

If `[adapter+0x19D8]&4 == 0`: direct jump to `0x0084F0ED`, no texture or sampler batch; shader/cache and subsequent state groups **still execute**.

If bit2 set:
1. `i=[adapter+0x1988]` and `limit=[adapter+0x198C]`, **unsigned compare**, loop while `i<limit`. `EDI=adapter+0x1908+i*4`; compare current `[EDI]` to applied `[EDI+0x40]`. On mismatch call `SetTexture(i,current)` and **always copy** `[EDI+0x40]=[EDI]` at 0x0084F04C, without inspecting HRESULT. After loop, clear both counters `[adapter+0x1988]` and `[adapter+0x198C]` at 0x0084F068/0x0084F06E. Their capacity bounds relative to backing arrays are not validated here.
2. Loop `[adapter+0x188C]` pending sampler packed records from `adapter+0x138C`, increment pointer by 4; `record` encodes **sampler=(record>>16)** and **state=(record&0xF)**, `index=sampler*16+state`. Compare `[adapter+0xF8C+4*index]` desired to `[adapter+0xB8C+4*index]` applied; on mismatch call `SetSamplerState(sampler,state,desired)`, then update applied. On every processed record set `BYTE[adapter+0x178C+index]=0` at `0x0084F0D2`; after loop set `DWORD[adapter+0x188C]=0` at `0x0084F0E7`. If there are no records, the count is still reset to 0.

### Group B — always-run shader and render-state sync (0x0084F0ED–0x0084F1B5)

1. Compare `DWORD[adapter+0x1890]` with `DWORD[adapter+0x1894]`; if unequal call `SetPixelShader(desired)`, then cache `[+0x1894]=[+0x1890]` at `0x0084F10D`.
2. Compare `[adapter+0x1898]` vs `[adapter+0x189C]`; if unequal call `SetVertexShader(desired)`, then cache `[+0x189C]=[+0x1898]` at `0x0084F133`.
3. Iterate unsigned `[adapter+0xB88]` entries from `adapter+0x69C`, each an index `stateID`. Compare `DWORD[adapter+0x0C+4*stateID]` against `DWORD[adapter+0x354+4*stateID]`; on mismatch call `SetRenderState(stateID,desired)`, then update applied cache. If mismatched: `BYTE[adapter+0xAB6+stateID]=0`. Regardless of equality: `BYTE[adapter+0x9E4+stateID]=0`. Reset count `DWORD[adapter+0xB88]=0` at 0x0084F1AB. These loops have no local bounds check on external indices/counts.

### Group C — mask 0x2, stream/index/layout (0x0084F1BB–0x0084F28E)

When bit 0x2 absent, branch at 0x0084F1BD bypasses stream/index/layout methods to 0x0084F28E.

When set:
1. Exactly two stream records, `i=0,1`; `EDI=adapter+0x19B8+i*0x10`. If `BYTE[EDI-0x28]!=0`, compare three DWORD current/cached pairs at `[EDI-0x24] ↔ [EDI-4]`, `[EDI-0x20] ↔ [EDI]`, `[EDI-0x1C] ↔ [EDI+4]`. On any mismatch call `SetStreamSource(i,buffer,offset,stride)`, then clear `BYTE[EDI-0x28]=0` (0x0084F208). **When dirty byte was nonzero but triplet identical, the code jumps straight to 0x0084F20C without clearing this dirty byte**; do not silently declare every dirty flag consumed.
2. `[adapter+0x19D0]` indexBuffer compared to `[adapter+0x19D4]`; if unequal call `SetIndices`, then `[+0x19D4]=[+0x19D0]` at 0x0084F23A.
3. If `[adapter+0x18A8] != [adapter+0x18AC]`, call `SetVertexDeclaration([+0x18A8])`. Then at **0x0084F260** write **`[+0x18A8]=[+0x18AC]`** (source is old comparison partner). This is the **actual byte-level copy direction**, rather than assumed applied←desired.
4. Only if preceding pair was equal, compare `[adapter+0x18A0]` vs `[adapter+0x18A4]`; if unequal call `SetFVF([+0x18A0])`, then at **0x0084F288** write **`[+0x18A0]=[+0x18A4]`**. Again copy direction is proven, interpretation of desired/current names not.
5. These branches are **exclusive at the decision point**: after taking the changed vertex-declaration path, jump at 0x0084F266 bypasses FVF comparison.

### Group D — mask 0x1, render targets / depth-stencil / viewport (0x0084F28E–0x0084F39F)

When bit0 absent skip directly to `0x0084F39F`. When set:
1. For `i=0..3`, compare `DWORD[adapter+0x18B0+4i]` against `DWORD[adapter+0x18C0+4i]`; on mismatch call `SetRenderTarget(i,current)`, then copy the current DWORD to cache (0x0084F2BF).
2. Compare `[+0x18D0]` against `[+0x18D4]`; if unequal call `SetDepthStencilSurface([+0x18D0])`, then cache `[+0x18D4]=[+0x18D0]` (0x0084F2F0).
3. Viewport: compare four DWORDs `[+0x18F0..+0x18FC]` against `[+0x18D8..+0x18E4]`; compare two float pairs `[+0x1900]↔[+0x18E8]`, `[+0x1904]↔[+0x18EC]` using `FUCOMPP/FNSTSW AX; TEST AH,0x44; JP/JNP`. An unequal/unordered comparison can enter `0x0084F35E`; equal path goes to `0x0084F39F`. On update call `SetViewport(adapter+0x18D8)`, copy all **six** viewport DWORDs into `adapter+0x18F0..+0x1904`. Equality is semantic x87/flags logic, **not** simply raw `memcmp` of 24 bytes.
4. At **0x0084F39F**, reset **DWORD[adapter+0x19D8]=0** regardless of underlying HRESULT outcomes. Epilogue follows. Successful method calls are *assumed by control flow for caching*, but success in a runtime frame has not been demonstrated.

### Derived hazards/limits

The helper unconditionally treats `[adapter+8]` as a dereferenceable device on paths that invoke a method; no local null check. Indexed loops depend on stored indices and counts, and can only be judged safe using broader constructors/setters, not the isolated function. The helper updates some caches even after **negative HRESULT**, as it does not test return codes. This is a statement about instruction order, **not** a proven game runtime defect.

## Immediate adapter+4 writers in the real class (bounded, not global)

Primary adapter constructor **0x00850100** has `0x00850109: mov DWORD[adapter],0x00B1BBA8` and at **0x00850176** `mov BYTE[adapter+4],0`. The adapter vtable PE bytes also prove:

| adapter vtable address | slot | actual target | effect on +4 |
|---|---|---|---|
| `0x00B1BC98` | `+0xF0` | **0x0084FBC0** | `0x0084FBC6` read `+4`; `0x0084FBC9` save to `+5`; **0x0084FBCC clear +4**; calls underlying device `+0xF0` with no extra args (corresponding to `BeginStateBlock` on created IDirect3DDevice9) |
| `0x00B1BC9C` | `+0xF4` | **0x0084FBF0** | `0x0084FBF6` reads `+5`; **0x0084FBF9 restores +4 from +5**; underlying device `+0xF4` with one extra stack argument (corresponding to `EndStateBlock`) |

These are **verified immediate class-local writes**. They establish a save/temporary-disable/restore relation, **not an independent proof of any writer setting +4 to 1**. If +4 were zero when saved, this pair restores zero. The constructor init 0 is proven; additional hidden/alias writers, later dynamic lifetime, or any nonzero source **remain unknown** in this bounded scope. No global +4 setter audit was attempted; other methods may write indirect aliases.

**The helper `0x0084F000` neither reads nor writes `adapter+4`; the guard is in its forwarder caller, not this helper.** Do not confuse the ESI+0x19D8 flags with ESI+4.

## v755 runtime evidence (user-supplied, not rerun)

**Controlled P-code replay v755:** same original PE, runtime SHA-256 `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`, manifest v659 SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`, game-data v661; 360 host frames, host-frame-loop, trace enabled and not truncated, **0 events** for selected `0x0084FD60` and four D3D9 Draw* guest imports. `0x0084F000` was **not among listed trace targets**: v755 does not directly tell us whether the helper executed from some other code path. Because `0x0084FD60` had zero observed events in this window, the particular *forwarder→helper* route also had no recorded forwarder entry; cannot infer inability to execute elsewhere, or that +4 is always zero. There is no new targeted replay here, no guest state forced or modified.

## Confidence ledger

**PE-byte established:** original SHA; complete instruction block, ABI/epilogue, branch targets and 12 indirect calls, adapter+8 → device pointer provenance from earlier constructor class, 12 calls' stack arity and exact passed values, all local writes and cache changes, vtable `0x00B1BBA8` slots `+0xF0/+0xF4`, constructor +4 initialization, save/restore class methods. The static function has **no Draw* call** among its actual calls.

**D3D9 ABI corroboration:** device type from retail CreateDevice chain plus independent indexed method ordering; not address-only inference and not runtime GPU device identity. Microsoft reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nn-d3d9-idirect3ddevice9 ; index/argument reference: https://docs.hsp.moe/Win32API/iface/Windows.Win32.Graphics.Direct3D9/IDirect3DDevice9.html .

**Only externally provided runtime observation:** bounded v755 zero target events. **Not established:** invocation of this helper, value of +4/+0x19D8 in v755, whether device COM calls succeeded, identities of dynamically replaced objects, absence of any additional writers, broader frontend/callback or Draw submission causality.

## Exactly one next bounded target

**`0x0084FBF0`** — specifically trace/review caller and value provenance of **`BYTE[adapter+5]` before `0x0084FBF9` restores it into `BYTE[adapter+4]`**; capture adapter pointer and old/new bytes read-only. This distinguishes a genuine nonzero restoration from a zero→zero save/restore. No forced flags, no additional global searches in this report.

## Full retail objdump appendices

All four blocks below come from the same original SHA-matching full retail objdump, with machine bytes. They are **not** synthetic pseudocode. Assigned helper `0x0084F000–0x0084F3AF` is unabridged; the additional tiny class methods and constructor are printed in full because they anchor the bounded +4 writer classification.

### A. Entire helper 0x0084F000–0x0084F3AF (270 machine-code lines)

```asm
  84f000:	55                   	push   ebp
  84f001:	8b ec                	mov    ebp,esp
  84f003:	83 ec 10             	sub    esp,0x10
  84f006:	53                   	push   ebx
  84f007:	56                   	push   esi
  84f008:	8b f1                	mov    esi,ecx
  84f00a:	f6 86 d8 19 00 00 04 	test   BYTE PTR [esi+0x19d8],0x4
  84f011:	8b 5e 08             	mov    ebx,DWORD PTR [esi+0x8]
  84f014:	57                   	push   edi
  84f015:	0f 84 d2 00 00 00    	je     0x84f0ed
  84f01b:	8b 86 88 19 00 00    	mov    eax,DWORD PTR [esi+0x1988]
  84f021:	3b 86 8c 19 00 00    	cmp    eax,DWORD PTR [esi+0x198c]
  84f027:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84f02a:	73 34                	jae    0x84f060
  84f02c:	8d bc 86 08 19 00 00 	lea    edi,[esi+eax*4+0x1908]
  84f033:	8b 0f                	mov    ecx,DWORD PTR [edi]
  84f035:	3b 4f 40             	cmp    ecx,DWORD PTR [edi+0x40]
  84f038:	74 15                	je     0x84f04f
  84f03a:	8b 13                	mov    edx,DWORD PTR [ebx]
  84f03c:	51                   	push   ecx
  84f03d:	50                   	push   eax
  84f03e:	8b 82 04 01 00 00    	mov    eax,DWORD PTR [edx+0x104]
  84f044:	53                   	push   ebx
  84f045:	ff d0                	call   eax
  84f047:	8b 0f                	mov    ecx,DWORD PTR [edi]
  84f049:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84f04c:	89 4f 40             	mov    DWORD PTR [edi+0x40],ecx
  84f04f:	83 c0 01             	add    eax,0x1
  84f052:	83 c7 04             	add    edi,0x4
  84f055:	3b 86 8c 19 00 00    	cmp    eax,DWORD PTR [esi+0x198c]
  84f05b:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84f05e:	72 d3                	jb     0x84f033
  84f060:	33 c0                	xor    eax,eax
  84f062:	39 86 8c 18 00 00    	cmp    DWORD PTR [esi+0x188c],eax
  84f068:	89 86 8c 19 00 00    	mov    DWORD PTR [esi+0x198c],eax
  84f06e:	89 86 88 19 00 00    	mov    DWORD PTR [esi+0x1988],eax
  84f074:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f077:	76 6e                	jbe    0x84f0e7
  84f079:	8d 96 8c 13 00 00    	lea    edx,[esi+0x138c]
  84f07f:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  84f082:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84f085:	8b 00                	mov    eax,DWORD PTR [eax]
  84f087:	8b c8                	mov    ecx,eax
  84f089:	c1 e9 10             	shr    ecx,0x10
  84f08c:	83 e0 0f             	and    eax,0xf
  84f08f:	8b d1                	mov    edx,ecx
  84f091:	c1 e2 04             	shl    edx,0x4
  84f094:	8d 3c 02             	lea    edi,[edx+eax*1]
  84f097:	89 45 f4             	mov    DWORD PTR [ebp-0xc],eax
  84f09a:	8b 84 be 8c 0f 00 00 	mov    eax,DWORD PTR [esi+edi*4+0xf8c]
  84f0a1:	3b 84 be 8c 0b 00 00 	cmp    eax,DWORD PTR [esi+edi*4+0xb8c]
  84f0a8:	89 45 f0             	mov    DWORD PTR [ebp-0x10],eax
  84f0ab:	74 1b                	je     0x84f0c8
  84f0ad:	8b 13                	mov    edx,DWORD PTR [ebx]
  84f0af:	50                   	push   eax
  84f0b0:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  84f0b3:	50                   	push   eax
  84f0b4:	51                   	push   ecx
  84f0b5:	8b 8a 14 01 00 00    	mov    ecx,DWORD PTR [edx+0x114]
  84f0bb:	53                   	push   ebx
  84f0bc:	ff d1                	call   ecx
  84f0be:	8b 55 f0             	mov    edx,DWORD PTR [ebp-0x10]
  84f0c1:	89 94 be 8c 0b 00 00 	mov    DWORD PTR [esi+edi*4+0xb8c],edx
  84f0c8:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84f0cb:	83 45 fc 04          	add    DWORD PTR [ebp-0x4],0x4
  84f0cf:	83 c0 01             	add    eax,0x1
  84f0d2:	c6 84 37 8c 17 00 00 00 	mov    BYTE PTR [edi+esi*1+0x178c],0x0
  84f0da:	3b 86 8c 18 00 00    	cmp    eax,DWORD PTR [esi+0x188c]
  84f0e0:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f0e3:	72 9d                	jb     0x84f082
  84f0e5:	33 c0                	xor    eax,eax
  84f0e7:	89 86 8c 18 00 00    	mov    DWORD PTR [esi+0x188c],eax
  84f0ed:	8b 86 90 18 00 00    	mov    eax,DWORD PTR [esi+0x1890]
  84f0f3:	3b 86 94 18 00 00    	cmp    eax,DWORD PTR [esi+0x1894]
  84f0f9:	74 18                	je     0x84f113
  84f0fb:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f0fd:	8b 91 ac 01 00 00    	mov    edx,DWORD PTR [ecx+0x1ac]
  84f103:	50                   	push   eax
  84f104:	53                   	push   ebx
  84f105:	ff d2                	call   edx
  84f107:	8b 86 90 18 00 00    	mov    eax,DWORD PTR [esi+0x1890]
  84f10d:	89 86 94 18 00 00    	mov    DWORD PTR [esi+0x1894],eax
  84f113:	8b 86 98 18 00 00    	mov    eax,DWORD PTR [esi+0x1898]
  84f119:	3b 86 9c 18 00 00    	cmp    eax,DWORD PTR [esi+0x189c]
  84f11f:	74 18                	je     0x84f139
  84f121:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f123:	8b 91 70 01 00 00    	mov    edx,DWORD PTR [ecx+0x170]
  84f129:	50                   	push   eax
  84f12a:	53                   	push   ebx
  84f12b:	ff d2                	call   edx
  84f12d:	8b 86 98 18 00 00    	mov    eax,DWORD PTR [esi+0x1898]
  84f133:	89 86 9c 18 00 00    	mov    DWORD PTR [esi+0x189c],eax
  84f139:	83 be 88 0b 00 00 00 	cmp    DWORD PTR [esi+0xb88],0x0
  84f140:	c7 45 f8 00 00 00 00 	mov    DWORD PTR [ebp-0x8],0x0
  84f147:	76 5a                	jbe    0x84f1a3
  84f149:	8d 8e 9c 06 00 00    	lea    ecx,[esi+0x69c]
  84f14f:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  84f152:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  84f155:	8b 3a                	mov    edi,DWORD PTR [edx]
  84f157:	8b 44 be 0c          	mov    eax,DWORD PTR [esi+edi*4+0xc]
  84f15b:	39 84 be 54 03 00 00 	cmp    DWORD PTR [esi+edi*4+0x354],eax
  84f162:	89 45 f0             	mov    DWORD PTR [ebp-0x10],eax
  84f165:	74 1f                	je     0x84f186
  84f167:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f169:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  84f16f:	50                   	push   eax
  84f170:	57                   	push   edi
  84f171:	53                   	push   ebx
  84f172:	ff d2                	call   edx
  84f174:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  84f177:	89 84 be 54 03 00 00 	mov    DWORD PTR [esi+edi*4+0x354],eax
  84f17e:	c6 84 37 b6 0a 00 00 00 	mov    BYTE PTR [edi+esi*1+0xab6],0x0
  84f186:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84f189:	83 45 fc 04          	add    DWORD PTR [ebp-0x4],0x4
  84f18d:	83 c0 01             	add    eax,0x1
  84f190:	c6 84 3e e4 09 00 00 00 	mov    BYTE PTR [esi+edi*1+0x9e4],0x0
  84f198:	3b 86 88 0b 00 00    	cmp    eax,DWORD PTR [esi+0xb88]
  84f19e:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f1a1:	72 af                	jb     0x84f152
  84f1a3:	8b 86 d8 19 00 00    	mov    eax,DWORD PTR [esi+0x19d8]
  84f1a9:	85 c0                	test   eax,eax
  84f1ab:	c7 86 88 0b 00 00 00 00 00 00 	mov    DWORD PTR [esi+0xb88],0x0
  84f1b5:	0f 84 ee 01 00 00    	je     0x84f3a9
  84f1bb:	a8 02                	test   al,0x2
  84f1bd:	0f 84 cb 00 00 00    	je     0x84f28e
  84f1c3:	33 c0                	xor    eax,eax
  84f1c5:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f1c8:	8d be b8 19 00 00    	lea    edi,[esi+0x19b8]
  84f1ce:	8b ff                	mov    edi,edi
  84f1d0:	80 7f d8 00          	cmp    BYTE PTR [edi-0x28],0x0
  84f1d4:	74 36                	je     0x84f20c
  84f1d6:	8b 4f dc             	mov    ecx,DWORD PTR [edi-0x24]
  84f1d9:	39 4f fc             	cmp    DWORD PTR [edi-0x4],ecx
  84f1dc:	75 0f                	jne    0x84f1ed
  84f1de:	8b 0f                	mov    ecx,DWORD PTR [edi]
  84f1e0:	3b 4f e0             	cmp    ecx,DWORD PTR [edi-0x20]
  84f1e3:	75 08                	jne    0x84f1ed
  84f1e5:	8b 57 04             	mov    edx,DWORD PTR [edi+0x4]
  84f1e8:	3b 57 e4             	cmp    edx,DWORD PTR [edi-0x1c]
  84f1eb:	74 1f                	je     0x84f20c
  84f1ed:	8b 4f e4             	mov    ecx,DWORD PTR [edi-0x1c]
  84f1f0:	8b 13                	mov    edx,DWORD PTR [ebx]
  84f1f2:	8b 92 90 01 00 00    	mov    edx,DWORD PTR [edx+0x190]
  84f1f8:	51                   	push   ecx
  84f1f9:	8b 4f e0             	mov    ecx,DWORD PTR [edi-0x20]
  84f1fc:	51                   	push   ecx
  84f1fd:	8b 4f dc             	mov    ecx,DWORD PTR [edi-0x24]
  84f200:	51                   	push   ecx
  84f201:	50                   	push   eax
  84f202:	53                   	push   ebx
  84f203:	ff d2                	call   edx
  84f205:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84f208:	c6 47 d8 00          	mov    BYTE PTR [edi-0x28],0x0
  84f20c:	83 c0 01             	add    eax,0x1
  84f20f:	83 c7 10             	add    edi,0x10
  84f212:	83 f8 02             	cmp    eax,0x2
  84f215:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f218:	72 b6                	jb     0x84f1d0
  84f21a:	8b 86 d0 19 00 00    	mov    eax,DWORD PTR [esi+0x19d0]
  84f220:	3b 86 d4 19 00 00    	cmp    eax,DWORD PTR [esi+0x19d4]
  84f226:	74 18                	je     0x84f240
  84f228:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f22a:	8b 91 a0 01 00 00    	mov    edx,DWORD PTR [ecx+0x1a0]
  84f230:	50                   	push   eax
  84f231:	53                   	push   ebx
  84f232:	ff d2                	call   edx
  84f234:	8b 86 d0 19 00 00    	mov    eax,DWORD PTR [esi+0x19d0]
  84f23a:	89 86 d4 19 00 00    	mov    DWORD PTR [esi+0x19d4],eax
  84f240:	8b 86 a8 18 00 00    	mov    eax,DWORD PTR [esi+0x18a8]
  84f246:	3b 86 ac 18 00 00    	cmp    eax,DWORD PTR [esi+0x18ac]
  84f24c:	74 1a                	je     0x84f268
  84f24e:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f250:	8b 91 5c 01 00 00    	mov    edx,DWORD PTR [ecx+0x15c]
  84f256:	50                   	push   eax
  84f257:	53                   	push   ebx
  84f258:	ff d2                	call   edx
  84f25a:	8b 86 ac 18 00 00    	mov    eax,DWORD PTR [esi+0x18ac]
  84f260:	89 86 a8 18 00 00    	mov    DWORD PTR [esi+0x18a8],eax
  84f266:	eb 26                	jmp    0x84f28e
  84f268:	8b 86 a0 18 00 00    	mov    eax,DWORD PTR [esi+0x18a0]
  84f26e:	3b 86 a4 18 00 00    	cmp    eax,DWORD PTR [esi+0x18a4]
  84f274:	74 18                	je     0x84f28e
  84f276:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  84f278:	8b 91 64 01 00 00    	mov    edx,DWORD PTR [ecx+0x164]
  84f27e:	50                   	push   eax
  84f27f:	53                   	push   ebx
  84f280:	ff d2                	call   edx
  84f282:	8b 86 a4 18 00 00    	mov    eax,DWORD PTR [esi+0x18a4]
  84f288:	89 86 a0 18 00 00    	mov    DWORD PTR [esi+0x18a0],eax
  84f28e:	f6 86 d8 19 00 00 01 	test   BYTE PTR [esi+0x19d8],0x1
  84f295:	0f 84 04 01 00 00    	je     0x84f39f
  84f29b:	33 c0                	xor    eax,eax
  84f29d:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f2a0:	8d be b0 18 00 00    	lea    edi,[esi+0x18b0]
  84f2a6:	8b 0f                	mov    ecx,DWORD PTR [edi]
  84f2a8:	3b 4f 10             	cmp    ecx,DWORD PTR [edi+0x10]
  84f2ab:	74 15                	je     0x84f2c2
  84f2ad:	8b 13                	mov    edx,DWORD PTR [ebx]
  84f2af:	51                   	push   ecx
  84f2b0:	50                   	push   eax
  84f2b1:	8b 82 94 00 00 00    	mov    eax,DWORD PTR [edx+0x94]
  84f2b7:	53                   	push   ebx
  84f2b8:	ff d0                	call   eax
  84f2ba:	8b 0f                	mov    ecx,DWORD PTR [edi]
  84f2bc:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84f2bf:	89 4f 10             	mov    DWORD PTR [edi+0x10],ecx
  84f2c2:	83 c0 01             	add    eax,0x1
  84f2c5:	83 c7 04             	add    edi,0x4
  84f2c8:	83 f8 04             	cmp    eax,0x4
  84f2cb:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84f2ce:	72 d6                	jb     0x84f2a6
  84f2d0:	8b 86 d0 18 00 00    	mov    eax,DWORD PTR [esi+0x18d0]
  84f2d6:	3b 86 d4 18 00 00    	cmp    eax,DWORD PTR [esi+0x18d4]
  84f2dc:	74 18                	je     0x84f2f6
  84f2de:	8b 13                	mov    edx,DWORD PTR [ebx]
  84f2e0:	50                   	push   eax
  84f2e1:	8b 82 9c 00 00 00    	mov    eax,DWORD PTR [edx+0x9c]
  84f2e7:	53                   	push   ebx
  84f2e8:	ff d0                	call   eax
  84f2ea:	8b 8e d0 18 00 00    	mov    ecx,DWORD PTR [esi+0x18d0]
  84f2f0:	89 8e d4 18 00 00    	mov    DWORD PTR [esi+0x18d4],ecx
  84f2f6:	8b 96 f0 18 00 00    	mov    edx,DWORD PTR [esi+0x18f0]
  84f2fc:	3b 96 d8 18 00 00    	cmp    edx,DWORD PTR [esi+0x18d8]
  84f302:	8d be d8 18 00 00    	lea    edi,[esi+0x18d8]
  84f308:	75 54                	jne    0x84f35e
  84f30a:	8b 86 f4 18 00 00    	mov    eax,DWORD PTR [esi+0x18f4]
  84f310:	3b 86 dc 18 00 00    	cmp    eax,DWORD PTR [esi+0x18dc]
  84f316:	75 46                	jne    0x84f35e
  84f318:	8b 8e f8 18 00 00    	mov    ecx,DWORD PTR [esi+0x18f8]
  84f31e:	3b 8e e0 18 00 00    	cmp    ecx,DWORD PTR [esi+0x18e0]
  84f324:	75 38                	jne    0x84f35e
  84f326:	8b 96 fc 18 00 00    	mov    edx,DWORD PTR [esi+0x18fc]
  84f32c:	3b 96 e4 18 00 00    	cmp    edx,DWORD PTR [esi+0x18e4]
  84f332:	75 2a                	jne    0x84f35e
  84f334:	d9 86 00 19 00 00    	fld    DWORD PTR [esi+0x1900]
  84f33a:	d9 86 e8 18 00 00    	fld    DWORD PTR [esi+0x18e8]
  84f340:	da e9                	fucompp
  84f342:	df e0                	fnstsw ax
  84f344:	f6 c4 44             	test   ah,0x44
  84f347:	7a 15                	jp     0x84f35e
  84f349:	d9 86 04 19 00 00    	fld    DWORD PTR [esi+0x1904]
  84f34f:	d9 86 ec 18 00 00    	fld    DWORD PTR [esi+0x18ec]
  84f355:	da e9                	fucompp
  84f357:	df e0                	fnstsw ax
  84f359:	f6 c4 44             	test   ah,0x44
  84f35c:	7b 41                	jnp    0x84f39f
  84f35e:	8b 03                	mov    eax,DWORD PTR [ebx]
  84f360:	8b 88 bc 00 00 00    	mov    ecx,DWORD PTR [eax+0xbc]
  84f366:	57                   	push   edi
  84f367:	53                   	push   ebx
  84f368:	ff d1                	call   ecx
  84f36a:	8b 17                	mov    edx,DWORD PTR [edi]
  84f36c:	8b 47 04             	mov    eax,DWORD PTR [edi+0x4]
  84f36f:	8b 4f 08             	mov    ecx,DWORD PTR [edi+0x8]
  84f372:	89 96 f0 18 00 00    	mov    DWORD PTR [esi+0x18f0],edx
  84f378:	8b 57 0c             	mov    edx,DWORD PTR [edi+0xc]
  84f37b:	89 86 f4 18 00 00    	mov    DWORD PTR [esi+0x18f4],eax
  84f381:	8b 47 10             	mov    eax,DWORD PTR [edi+0x10]
  84f384:	89 8e f8 18 00 00    	mov    DWORD PTR [esi+0x18f8],ecx
  84f38a:	8b 4f 14             	mov    ecx,DWORD PTR [edi+0x14]
  84f38d:	89 96 fc 18 00 00    	mov    DWORD PTR [esi+0x18fc],edx
  84f393:	89 86 00 19 00 00    	mov    DWORD PTR [esi+0x1900],eax
  84f399:	89 8e 04 19 00 00    	mov    DWORD PTR [esi+0x1904],ecx
  84f39f:	c7 86 d8 19 00 00 00 00 00 00 	mov    DWORD PTR [esi+0x19d8],0x0
  84f3a9:	5f                   	pop    edi
  84f3aa:	5e                   	pop    esi
  84f3ab:	5b                   	pop    ebx
  84f3ac:	8b e5                	mov    esp,ebp
  84f3ae:	5d                   	pop    ebp
  84f3af:	c3                   	ret
```

### B. Entire adapter method 0x0084FBC0–0x0084FBDF

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

### C. Entire adapter method 0x0084FBF0–0x0084FC0F

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

### D. Entire adapter initializer 0x00850100–0x0085017E

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
