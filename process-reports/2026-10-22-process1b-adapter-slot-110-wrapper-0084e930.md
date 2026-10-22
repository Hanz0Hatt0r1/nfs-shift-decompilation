# Process 1 — original retail primary adapter slot +0x110, wrapper 0x0084E930

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **SHA-256 original `/mnt/data/SHIFT.exe` (independently checked):** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Scope:** only executable `0x0084E930–0x0084E974`, adapter primary-vtable `+0x110`, already-established constructor/device-pointer provenance, and one PE-backed next-slot anchor. The complete machine-code block was independently checked with `objdump -D -Mintel -w` on the mounted original retail PE and matched the uploaded full `SHIFT_objdump_full.txt`. The `.rdata` DWORDs were checked from original file offsets. No repeated investigation of `+0x10C`, no global vtable/caller/setter sweep, no source/runtime/P-code/renderer/guest-state changes, no replay or claims of live execution. This is a **static report**, not new runtime evidence.

## 1. Answer and exact primary-vtable resolution

**Original PE data:** primary adapter vptr = **`0x00B1BBA8`**, set in retail constructor `0x00850100`. `DWORD[0x00B1BCB8] = DWORD[0x00B1BBA8+0x110] = 0x0084E930`; the original `.rdata` bytes at that VA/file offset `0x0071A6B8` are **`30 E9 84 00`**. This uniquely resolves the **static adapter primary-vtable entry**, not the dynamic underlying device implementation.

**Exact block behavior:**
- **`BYTE[adapter+4] != 0`:** compute a two-argument index, read the indexed DWORD at `adapter+0xF8C+4*index`, store that value to the caller-provided `DWORD* outputPointer`, and return **`EAX=0`**. There is no nested call on this branch.
- **`BYTE[adapter+4] == 0`:** load the underlying D3D9 COM device pointer from `[adapter+8]`; load its *dynamic device vptr*; invoke `device.vptr+0x110` with **device**, **arg1**, **arg2**, **arg3** in x86 COM stdcall stack order. EAX from device call is returned **unchanged**. This branch performs no local output store.
- Both return paths have **`RET 0x10`**, cleaning four incoming stack DWORDs (adapter receiver + three method arguments).
- There is **no proven direct write** to any adapter state/cache/dirty field or `BYTE[adapter+4]` in this body; the cache path only **reads** the indexed adapter DWORD and writes to a caller-supplied output pointer. Aliasing of that output pointer into adapter storage is unproven.
- No Begin/EndStateBlock, Draw*, state mutation via another adapter virtual method, or direct Draw* import in this wrapper. This is a **bounded** result.

**API-level identification:** `IDirect3DDevice9::GetSamplerState(DWORD Sampler, D3DSAMPLERSTATETYPE Type, DWORD *pValue)` (D3D9 vtable slot **68** = `0x110/4`). The name, types, HRESULT and [out] direction of `pValue` are supported by **(i)** existing CreateDevice-produced `IDirect3DDevice9*` provenance, **(ii)** the official D3D9 interface order, and **(iii)** the precise three-argument outgoing ABI. None of those types/names is present in the instructions themselves; a slot-offset coincidence alone would not establish the method. Microsoft official reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-getsamplerstate . The actual COM method implementation **EIP is unresolved** because it is fetched from the live device vtable, not from the adapter's retail PE table.

## 2. Four-DWORD incoming stack ABI and both returns

Retail prologue is `0x0084E930: PUSH EBP` and `0x0084E931: MOV EBP,ESP`. The adapter pointer is **passed on the stack, not as ECX=this**. No stack-local allocation or nonvolatile EBX/ESI/EDI use. At function entry, a return-address DWORD is at `[ESP]` and the following four caller-supplied DWORDs are at `[ESP+4..+0x10]`. After frame setup:

| Stack location | Byte-grounded use | API name (external inference) |
|---|---|---|
| `[EBP+0x08]` | `0x0084E933: EAX=DWORD[EBP+8]` → adapter, read `BYTE[adapter+4]` and `DWORD[adapter+8]` | explicit adapter receiver |
| `[EBP+0x0C]` | `0x0084E93C: ECX=DWORD[EBP+0xC]`, left shift four; `0x0084E964` loads same DWORD as first device method argument | `DWORD Sampler` |
| `[EBP+0x10]` | `0x0084E942` adds the DWORD to cache index; `0x0084E960` reloads for second outgoing device argument | `D3DSAMPLERSTATETYPE Type` |
| `[EBP+0x14]` | `0x0084E94C` loads pointer for cached output store; `0x0084E957` loads it for COM forwarding | `DWORD *pValue` |

The cached epilogue: `0x0084E951: XOR EAX,EAX`; `0x0084E953: POP EBP`; `0x0084E954: RET 0x10`, machine instruction bytes `C2 10 00`. This returns **full zero EAX** no matter what cache value was copied or whether the output pointer was valid. It **does not** verify the cached data or call downstream to confirm the value.

The zero-flag epilogue: `0x0084E96F: CALL EAX` followed by `0x0084E971: POP EBP` and `0x0084E972: RET 0x10`. Nothing after the call modifies EAX: **raw EAX passthrough**. Calling the result HRESULT is grounded in D3D9 ABI, not in a local error test. Neither path checks HRESULT sign, equality, success, null pointer or data range. Two normal exits, no extra error path.

## 3. Cached branch: exact address/arithmetics, output and checks

**Entry condition:** `0x0084E936: CMP BYTE PTR [EAX+4],0`; `0x0084E93A: JE 0x0084E957` transfers to device when **zero**. **Nonzero** falls through to cached branch.

Original instructions (reproduced in the full appendix):
1. `0x0084E93C: ECX = DWORD[EBP+0x0C]`.
2. `0x0084E93F: SHL ECX,4` → `(arg1 << 4) mod 2^32`.
3. `0x0084E942: ADD ECX,DWORD[EBP+0x10]` → `index = ((arg1*16)+arg2) mod 2^32`.
4. `0x0084E945: MOV EDX,DWORD[adapter+ECX*4+0xF8C]` → **read** one 32-bit cache value from **`adapter+0xF8C+4*((arg1<<4)+arg2)`** (32-bit x86 addressing, modulo 2^32).
5. `0x0084E94C: EAX=DWORD[EBP+0x14]` = outputPointer.
6. **`0x0084E94F: MOV DWORD[EAX],EDX`** → store cache DWORD to **`*outputPointer`**.
7. `0x0084E951: XOR EAX,EAX`; POP EBP; RET 0x10.

Semantically useful—but **not reconstructed source**—32-bit pseudocode:

~~~c
uint32_t index = (sampler << 4) + type;        // uint32_t wrap
uint32_t value = *(uint32_t *)(adapter + 0xF8C + 4 * index);
*(uint32_t *)outputPointer = value;
return 0;
~~~

The machine code has **no local bounds check** on the Sampler/Type argument ranges, index/table length, or potential wraparound; no mask constraining `type` to 0..15; no exception, null-pointer, valid-cache or output-pointer check. The stride of 16 entries per sampler is inferred from the explicit `SHL 4`, not evidence of how many samplers are allocated/valid in the surrounding object. Signedness is not tested by comparisons here; it is the raw 32-bit bit pattern that supplies addressing. Do **not** import presumed API-valid ranges as an executable bounds check in this adapter.

The only explicit memory write in this cached branch is through caller-controlled `outputPointer`, not through the adapter base. An arbitrary caller **could** pass an alias into adapter/cache/flag memory; no such caller or alias is established in the bounded source. Consequently "**no proved adapter write**" is more precise than a universal noninterference guarantee.

## 4. Device forwarding branch and API interface boundary

**Entry condition:** `BYTE[adapter+4]==0`, conditional jump at `0x0084E93A` enters `0x0084E957`.

Byte-level value flow:
- `0x0084E957: EDX=outputPointer` from `[EBP+0x14]`.
- `0x0084E95A: EAX=DWORD[adapter+8]` → underlying `D`.
- `0x0084E95D: ECX=DWORD[D]` → dynamic device vptr `V`.
- `0x0084E95F: PUSH EDX` → outputPointer.
- `0x0084E960–0x0084E963: PUSH DWORD[EBP+0x10]` → type.
- `0x0084E964–0x0084E967: PUSH DWORD[EBP+0x0C]` → sampler.
- `0x0084E968: PUSH EAX` → COM receiver `D`.
- `0x0084E969: EAX=DWORD[V+0x110]` and **`0x0084E96F: CALL EAX`**.

On entry to called COM method (after CALL pushes its return address): **`[ESP+4]=D`, `[ESP+8]=sampler`, `[ESP+0xC]=type`, `[ESP+0x10]=outputPointer`**. The **nested** COM stdcall frame contains four DWORDs and is callee-cleaned separately; the adapter wrapper's own original four DWORDs are cleaned by its `RET 0x10`. There is no stack argument rewriting, index packing or conversion on the forwarding path.

The previous bounded retail constructor/helper path establishes `D=IDirect3DDevice9*` by a `CreateDevice`-compatible call and subsequent store to `[adapter+8]`. An adapter virtual lookup of **`primaryVptr+0x110 = 0x0084E930`** (in original PE) therefore **must not** be confused with the distinct **`D.vptr+0x110`** read inside the wrapper. The latter is a COM method pointer supplied by Direct3D implementation, not an original PE code address.

At the official API level, `GetSamplerState` reads a sampler-state value, takes `Sampler`/`Type` as inputs and `DWORD* pValue` as output, and returns HRESULT. The D3D9 documentation also notes that it does not return device state from a `D3DCREATE_PUREDEVICE`; **this is a documented device capability caveat**, not a branch/test executed by this wrapper. No runtime device flags were measured here. API source: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-getsamplerstate .

## 5. Local effects, confidence and excluded runtime claims

**PE-byte established:** verified SHA-256; exact primary table entry at `0x00B1BCB8`; complete 27 decoded instruction function; stack arguments and both `RET 0x10`; local nonzero-byte cached read/output store/EAX=0; device pointer/vptr and precise slot `+0x110` with outgoing argument order; raw HRESULT passthrough; absence of direct adapter/cache/dirty stores, extra calls and validation.

**API-level inference:** standard `IDirect3DDevice9::GetSamplerState(DWORD,D3DSAMPLERSTATETYPE,DWORD*)`, index 68, HRESULT and [out] direction. Proven device provenance + method index + ABI justify this identification; a bare offset alone is inadequate. Source-level field/type names and dynamic COM implementation address are **not** in PE bytes.

**Bounded negative findings:** no direct write of `BYTE[adapter+4]`, no cached state mutation or dirty-mask update, no primary BeginStateBlock/EndStateBlock call, and no Draw* call/import. Only cached output-pointer store or device virtual `+0x110` appears. There is no proof of invocation in the game, success/failure or actual value of sampler state; lack of a direct Draw* call **within this wrapper** is not proof of global render-path reachability.

**Runtime observations:** the earlier user-provided controlled v757 P-code trace covers other selected Begin/EndStateBlock/Draw* targets over 360 host frames. It does **not** instrument the current method, cannot provide its call count, and does not demonstrate its execution. No replay, guest-state forcing, game launch or code changes occurred in this assignment.

**Unresolved / out of bounds:** actual live receiver/vptr, output-pointer validity and alias, sampler/type values and valid cache capacity, dynamics of queried state, actual COM address/HRESULT, all callers/writers, any other adapter or P2 functions.

## 6. Exactly one next evidence-backed target

**`0x0084E980` — primary adapter slot `+0x114`.** Verified original `.rdata` DWORD at **`0x00B1BCBC`** is **`0x0084E980`** (bytes `80 E9 84 00`). Its initial instruction sequence tests the same `BYTE[adapter+4]` and its cached branch has an explicit store to the **same indexed address** `adapter+0xF8C+4*((sampler<<4)+type)` at **`0x0084E99E`**. This is one justified, **separately scoped** next target for exact setter/dirty-queue and device-slot ABI analysis, not a global setter search. No complete semantic audit of `0x0084E980` is made here.

## Appendix A — full original retail target 0x0084E930–0x0084E974 (27 disassembled lines, both RETs)

~~~asm
  84e930:	55                   	push   ebp
  84e931:	8b ec                	mov    ebp,esp
  84e933:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e936:	80 78 04 00          	cmp    BYTE PTR [eax+0x4],0x0
  84e93a:	74 1b                	je     0x84e957
  84e93c:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84e93f:	c1 e1 04             	shl    ecx,0x4
  84e942:	03 4d 10             	add    ecx,DWORD PTR [ebp+0x10]
  84e945:	8b 94 88 8c 0f 00 00 	mov    edx,DWORD PTR [eax+ecx*4+0xf8c]
  84e94c:	8b 45 14             	mov    eax,DWORD PTR [ebp+0x14]
  84e94f:	89 10                	mov    DWORD PTR [eax],edx
  84e951:	33 c0                	xor    eax,eax
  84e953:	5d                   	pop    ebp
  84e954:	c2 10 00             	ret    0x10
  84e957:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84e95a:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e95d:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e95f:	52                   	push   edx
  84e960:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e963:	52                   	push   edx
  84e964:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e967:	52                   	push   edx
  84e968:	50                   	push   eax
  84e969:	8b 81 10 01 00 00    	mov    eax,DWORD PTR [ecx+0x110]
  84e96f:	ff d0                	call   eax
  84e971:	5d                   	pop    ebp
  84e972:	c2 10 00             	ret    0x10
~~~

## Appendix B — original constructor 0x00850100–0x00850180, provenance context only

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

## Appendix C — narrow original vtable / next setter anchor

~~~text
.rdata VA 0x00B1BCB4: 00 E9 84 00 -> 0x0084E900 (primary adapter +0x10C)
.rdata VA 0x00B1BCB8: 30 E9 84 00 -> 0x0084E930 (primary adapter +0x110)
.rdata VA 0x00B1BCBC: 80 E9 84 00 -> 0x0084E980 (primary adapter +0x114)
~~~

~~~asm
  84e980:	55                   	push   ebp
  84e981:	8b ec                	mov    ebp,esp
  84e983:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e986:	80 78 04 00          	cmp    BYTE PTR [eax+0x4],0x0
  84e98a:	74 53                	je     0x84e9df
  84e98c:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84e98f:	56                   	push   esi
  84e990:	8b 75 10             	mov    esi,DWORD PTR [ebp+0x10]
  84e993:	8b d1                	mov    edx,ecx
  84e995:	c1 e2 04             	shl    edx,0x4
  84e998:	57                   	push   edi
  84e999:	8b 7d 14             	mov    edi,DWORD PTR [ebp+0x14]
  84e99c:	03 d6                	add    edx,esi
  84e99e:	89 bc 90 8c 0f 00 00 	mov    DWORD PTR [eax+edx*4+0xf8c],edi
  84e9a5:	80 bc 02 8c 17 00 00 00 	cmp    BYTE PTR [edx+eax*1+0x178c],0x0
  84e9ad:	75 21                	jne    0x84e9d0
~~~

## Appendix D — only essential original device-pointer publication bytes

~~~asm
00833095: 8b 17                   mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00      lea    ecx,[esi+0x1f7c]
0083309d: 52                      push   edx
0083309e: e8 1d b2 01 00         call   0x84e2c0
0084e2dd: 89 46 08               mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00      lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00      mov    DWORD PTR [esi+0x478],eax
~~~

**Deliverable:** this one Markdown file only. No source/runtime/P-code/renderer/guest-state or P2 modifications, PR or replay.
