# Process 1 — retail primary adapter slot +0x104, wrapper 0x0084E860

**Date:** 2026-10-22. **Original PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Verified against the mounted original `/mnt/data/SHIFT.exe` using `sha256sum`. Exact code re-disassembled directly from the PE with `objdump -D -Mintel -w` and cross-checked against the uploaded full `SHIFT_objdump_full.txt`.

**Exact boundary:** `0x0084E860–0x0084E8C3`, its primary-adapter vtable cell, ordinary already-established constructor/device provenance, and one adjacent next-slot address. No global vtable/caller sweep, runtime replay, renderer, guest-state forcing, code edits or changes to P2. The preceding accepted `+0x100` reader report is used only for its exact common cache-slot address, not repeated.

## 1. Main determination

The original retail `.rdata` value at `0x00B1BCAC = 0x00B1BBA8 + 0x104` contains **`60 E8 84 00`**, i.e. target **`0x0084E860`**. Its **three explicit incoming stack DWORDs** are `adapter`, `stage` and `texturePointer`. On `BYTE[adapter+4]!=0` the function stores the raw `texturePointer` DWORD into the indexed adapter cache, extends the tracked index interval using unsigned comparisons, sets the `0x4` bit in an adapter DWORD mask and returns exactly `EAX=0`. When the byte is zero, it invokes the underlying `IDirect3DDevice9` receiver through its **dynamic virtual slot `+0x104`**, forwarding both caller method arguments unchanged, and returns its EAX unchanged.

**API-level interpretation:** `IDirect3DDevice9::SetTexture(DWORD Stage, IDirect3DBaseTexture9 *pTexture)`, HRESULT-returning COM interface method, **index 65** (`0x104/4`). This name is justified by *both* the previously byte-proven `IDirect3D9::CreateDevice` device-pointer provenance and the exact two-parameter stack shape plus standard interface ordering. The original PE does not itself encode the COM method's source-level name or runtime EIP. Official API signature: https://learn.microsoft.com/en-us/windows/win32/api/d3d9helper/nf-d3d9helper-idirect3ddevice9-settexture ; Microsoft texture-resource ownership remarks: https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/direct3d9/texture-resources.md .

## 2. Entry ABI, control flow, cleanup and HRESULT

Full retail machine block is reproduced **without omissions** in Appendix A.

| Wrapper argument | Proven machine-code source / usage | API-facing interpretation |
|---|---|---|
| `[EBP+0x08]` | EAX loaded at `0x0084E863`; `[EAX+4]` branch test, indexed writes / `[EAX+8]` device load | Explicit stack **adapter receiver**, not ECX=this |
| `[EBP+0x0C]` | ECX at `0x0084E86F` for indexed store/bounds; EDX at `0x0084E8B3` for device call | `DWORD Stage`, full 32-bit unchanged |
| `[EBP+0x10]` | EDX loaded **before** branch at `0x0084E86A`; stored into cache or pushed on device path at `0x0084E8B2` | `IDirect3DBaseTexture9 *pTexture` under D3D9 API |

`PUSH EBP; MOV EBP,ESP` establishes frame without local allocation, and either `0x0084E8AA: RET 0x0C` or `0x0084E8C1: RET 0x0C` cleans **12 bytes** from the adapter-wrapper caller's stack. EBP restored in both exits; EAX, ECX, EDX are volatile working registers; ESI/EDI/EBX untouched.

`0x0084E866: CMP BYTE[adapter+4],0`, `0x0084E86D: JE 0x0084E8AD`:
- **zero** (JE taken): direct device-call branch;
- **nonzero**: cache-write / dirty-tracking branch.

In the cached branch the only status construction is `0x0084E8A7: XOR EAX,EAX`, returning **full EAX=0**, irrespective of input stage/texture validity. It performs no HRESULT or success check. Under the COM D3D_OK convention zero means success, but that is an *unconditional synthetic status*, not evidence of a successful device operation.

In the device branch `0x0084E8BE: CALL EAX` is followed by `POP EBP` and `RET 0xC` only. **Underlying COM EAX is passed through untouched**; it is HRESULT by interface contract, without testing, mapping, retrying or forcing success.

## 3. Flag-nonzero branch: exact cache writes, low/high bounds and dirty mask

Entry conditions: `BYTE[adapter+4] != 0`. No direct call occurs in this branch.

1. `0x0084E86A` loads **`texturePointer = DWORD[EBP+0x10]`** into EDX. `0x0084E86F` loads `stage=DWORD[EBP+0x0C]` into ECX. **`0x0084E872` writes `DWORD[adapter+0x1908+4*stage] = texturePointer`**. This is *exactly* the indexed DWORD address read by previously verified `0x0084E800`, primary slot `+0x100`. This branch **overwrites a 32-bit pointer value**; it does not dereference it or validate object type.
2. `0x0084E879` loads `oldLow=DWORD[adapter+0x1988]` into EDX; `0x0084E87F: CMP EDX,ECX`, `0x0084E881: JB 0x0084E885`, `0x0084E883: MOV EDX,ECX`. **Unsigned** `JB` yields `newLow=min_unsigned(oldLow,stage)`, written back at **`0x0084E885`**. Equality likewise produces the identical value.
3. `0x0084E88B` loads `oldHigh=DWORD[adapter+0x198C]` into EDX. `0x0084E891: ADD ECX,1` produces `stagePlusOne = (stage+1) mod 2^32`. `0x0084E894: CMP EDX,ECX`; `0x0084E896: JBE 0x0084E89A`; otherwise `0x0084E898: MOV ECX,EDX`. Thus **`newHigh=max_unsigned(oldHigh,stagePlusOne)`** using the *wrapped* increment, written to `DWORD[adapter+0x198C]` at **`0x0084E8A1`**. The stored bound is an exclusive-end candidate by the `stage+1` arithmetic, **not** a verified array-capacity/contract guarantee.
4. **`0x0084E89A: OR DWORD[adapter+0x19D8],0x4`** sets mask bit 2, leaving all other bits unchanged; it does **not** set `BYTE[adapter+4]` or clear previously dirty states. In earlier bounded `0x0084F000` analysis the same `adapter+0x19D8` bit was associated with texture/sampler synchronization, but this function alone proves only the OR mutation, **not that a later flush executes**.
5. `0x0084E8A7: XOR EAX,EAX` and `RET 0xC` after restoring EBP.

Equivalent **32-bit unsigned arithmetic** (descriptive pseudocode, not literal compiled source):

~~~c
*(uint32_t *)(adapter + 0x1908 + 4u*stage) = texturePointer;
uint32_t low = *(uint32_t *)(adapter + 0x1988);
*(uint32_t *)(adapter + 0x1988) = (low < stage) ? low : stage;
uint32_t oldHigh = *(uint32_t *)(adapter + 0x198C);
uint32_t stagePlusOne = stage + 1u; // modulo 2^32
*(uint32_t *)(adapter + 0x19D8) |= 0x4;
*(uint32_t *)(adapter + 0x198C) =
    (oldHigh <= stagePlusOne) ? stagePlusOne : oldHigh;
return 0;
~~~

**Bounds/validation:** zero explicit checks for maximum `stage`, cache count or valid texture pointer. The indexed write occurs **before** any comparison with low/high, and those comparisons *update tracking fields*; they **do not protect cache indexing**. In particular, `adapter+0x1988` is only `0x80` bytes after `adapter+0x1908`, but **this proximity is not proof that the valid stage range is exactly 0..31**. Out-of-range indexes can address unrelated memory; no safety guarantee is provided by this method. `Stage=0xFFFFFFFF` causes modulo overflow in `stage+1`; no overflow guard. No clip/saturation of stage to API-defined sampler ranges.

**Cached-resource ownership:** **no `IUnknown::AddRef` or `IUnknown::Release` call, no pointer-type check, no old-pointer release, no allocation and no resource destruction in the cached branch**. It stores the incoming raw value. Do not infer long-term ownership or a leak without separately verifying the cache lifecycle. The adjacent getter's AddRef behavior does not prove reference-count management by this setter.

## 4. Flag-zero branch: exact underlying device forwarding

The outgoing receiver is **`D = DWORD[adapter+8]`**, proven from prior original retail `IDirect3D9::CreateDevice`/constructor path, not merely from a matching pointer offset. At `0x0084E8AD: EAX=[adapter+8]`; `0x0084E8B0: ECX=[D]` obtains *dynamic underlying device vtable* `V`.

Exact argument order:

~~~asm
0084e8ad: 8b 40 08              mov eax,DWORD PTR [eax+0x8]        ; D
0084e8b0: 8b 08                 mov ecx,DWORD PTR [eax]            ; V
0084e8b2: 52                    push edx                          ; texturePointer
0084e8b3: 8b 55 0c              mov edx,DWORD PTR [ebp+0xc]       ; stage
0084e8b6: 52                    push edx                          ; stage
0084e8b7: 50                    push eax                          ; D
0084e8b8: 8b 81 04 01 00 00     mov eax,DWORD PTR [ecx+0x104]    ; F
0084e8be: ff d0                 call eax
~~~

So at the callee's entry its stack is `[ESP+4]=D` (COM this), `[ESP+8]=stage`, `[ESP+0xC]=texturePointer`. Device COM stdcall cleans this *separate* invocation frame with 12 bytes; the wrapper independently cleans its own original three stack args via `RET 0xC`. There is no extra transformation of `stage` or `texturePointer`. Dynamic `F = DWORD[DWORD[D]+0x104]` **is not a known fixed PE EIP**, and has not been observed at runtime.

D3D9 GetTexture is index 64; **SetTexture is index 65**, the corresponding two-input-argument operation. Confirmed `IDirect3DDevice9` receiver provenance + **method arity/order** + slot identity together support `IDirect3DDevice9::SetTexture(DWORD, IDirect3DBaseTexture9*)`. The API contract allows texture assignment and potential internal reference-count management by the *device method*. Microsoft's Direct3D9 Texture Resources documentation states that SetTexture increments the assigned texture's reference count. **Those effects are API-level behavior, not evidence that this wrapper's cached branch AddRefs, that COM ran, or what happened for any particular HRESULT.**

## 5. Strict bounded effects and evidence tiers

**PE-byte proven:**
- Adapter primary vptr from constructor `0x00850100` and exact `.rdata` DWORD `[0x00B1BCAC]=0x0084E860` (bytes `60 e8 84 00`).
- `[EBP+8]` adapter, `[EBP+0xC]` stage, `[EBP+0x10]` texturePointer; both exits `RET 0xC`; cached EAX=0; forwarding EAX passed through; branch on `BYTE[adapter+4]`.
- Cached stores **`[adapter+0x1908+stage*4]`, `[adapter+0x1988]`, `[adapter+0x198C]`**; OR `0x4` into `[adapter+0x19D8]`. **None of these writes targets `BYTE[adapter+4]`.**
- No local AddRef, Release, BeginStateBlock/EndStateBlock call, Draw* call or read/draw import; **the only CALL in this entire method** is `0x0084E8BE` to underlying `device.vptr+0x104` on the zero-flag branch. No dynamic COM vptr or texture-pointer validity test.
- No stage bounds check; unsigned min/max bounds bookkeeping does not validate the indexed array store.

**API identification / documented effects:** SetTexture, input Stage/pTexture, HRESULT, and reference count implications are inferred from the previously established IDirect3DDevice9 object provenance plus the exact known D3D9 interface method order / official API. This is not a named imported PE call.

**Runtime observation:** no replay/game start was performed or claimed. Earlier bounded user-supplied v757 traces targeted different Begin/End/Draw EIPs and cannot support any execution or live state assertion for `0x0084E860`. The PE does not show whether either branch executes, the real device pointer address, actual HRESULT, or texture lifetime.

**Unresolved:** caller-provided `stage` and `texturePointer` values, whether any dynamic override of primary or device vptr occurs, correct array capacity, true min/max initialization, completeness of cache ownership/release handling, actual GPU/D3D9 state. No global sweep of setters, callers or pointer producers is done.

## 6. Exactly one next evidence-backed target

**`0x0084E8D0`** — next adjacent **primary adapter slot `+0x108`**. Original `.rdata` at **`0x00B1BCB0`** contains **`D0 E8 84 00`** (little-endian `0x0084E8D0`). Its initial PE bytes receive explicit stack arguments and forward via dynamic **`underlyingDevice.vptr+0x108`**, with three method arguments in addition to the device receiver. It is the **single** bounded next ABI/API-provenance target. Its full behavior and semantic name are not asserted as findings of the current task.

## Appendix A — entire original retail target block (33 decoded instructions, including bytes)

~~~asm
  84e860:	55                   	push   ebp
  84e861:	8b ec                	mov    ebp,esp
  84e863:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e866:	80 78 04 00          	cmp    BYTE PTR [eax+0x4],0x0
  84e86a:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e86d:	74 3e                	je     0x84e8ad
  84e86f:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84e872:	89 94 88 08 19 00 00 	mov    DWORD PTR [eax+ecx*4+0x1908],edx
  84e879:	8b 90 88 19 00 00    	mov    edx,DWORD PTR [eax+0x1988]
  84e87f:	3b d1                	cmp    edx,ecx
  84e881:	72 02                	jb     0x84e885
  84e883:	8b d1                	mov    edx,ecx
  84e885:	89 90 88 19 00 00    	mov    DWORD PTR [eax+0x1988],edx
  84e88b:	8b 90 8c 19 00 00    	mov    edx,DWORD PTR [eax+0x198c]
  84e891:	83 c1 01             	add    ecx,0x1
  84e894:	3b d1                	cmp    edx,ecx
  84e896:	76 02                	jbe    0x84e89a
  84e898:	8b ca                	mov    ecx,edx
  84e89a:	83 88 d8 19 00 00 04 	or     DWORD PTR [eax+0x19d8],0x4
  84e8a1:	89 88 8c 19 00 00    	mov    DWORD PTR [eax+0x198c],ecx
  84e8a7:	33 c0                	xor    eax,eax
  84e8a9:	5d                   	pop    ebp
  84e8aa:	c2 0c 00             	ret    0xc
  84e8ad:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e8b0:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e8b2:	52                   	push   edx
  84e8b3:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e8b6:	52                   	push   edx
  84e8b7:	50                   	push   eax
  84e8b8:	8b 81 04 01 00 00    	mov    eax,DWORD PTR [ecx+0x104]
  84e8be:	ff d0                	call   eax
  84e8c0:	5d                   	pop    ebp
  84e8c1:	c2 0c 00             	ret    0xc
~~~

## Appendix B — full original constructor `0x00850100–0x0085017E`, provenance only

~~~asm
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
~~~

## Appendix C — next slot byte anchor, not a new audit

~~~text
.rdata VA 0x00B1BCA8 bytes 00 E8 84 00 -> 0x0084E800  (primary adapter +0x100)
.rdata VA 0x00B1BCAC bytes 60 E8 84 00 -> 0x0084E860  (primary adapter +0x104)
.rdata VA 0x00B1BCB0 bytes D0 E8 84 00 -> 0x0084E8D0  (primary adapter +0x108)
~~~

~~~asm
  84e8d0:	55                   	push   ebp
  84e8d1:	8b ec                	mov    ebp,esp
  84e8d3:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84e8d6:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e8d9:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e8dc:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e8de:	52                   	push   edx
  84e8df:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e8e2:	52                   	push   edx
  84e8e3:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e8e6:	52                   	push   edx
  84e8e7:	50                   	push   eax
  84e8e8:	8b 81 08 01 00 00    	mov    eax,DWORD PTR [ecx+0x108]
  84e8ee:	ff d0                	call   eax
~~~

**Submission:** add this Markdown report only; no source code changes, runtime changes, replay, renderer or guest state modifications.
