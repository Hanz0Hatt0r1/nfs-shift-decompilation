# Process 1 — retail primary adapter slot +0x114 / cached sampler-state setter 0x0084E980

**Date:** 2026-10-22. **Scope:** one original PE32 x86 wrapper `0x0084E980–0x0084E9FC` (last `RET 0x10` starts `0x0084E9FA`), its exact adapter primary vtable cell, established constructor/device-pointer provenance, and one next-slot anchor. No broader vtable/caller/field-writer sweep; do not reopen prior `+0x110` analysis. No code/runtime/P-code/renderer/guest-state edits, replay, forcing, game launch, or P2 modifications.

**Binary:** Need for Speed SHIFT PC retail 1.02; ImageBase `0x00400000`. **Reverified SHA-256 of mounted original `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Source instruction bytes independently disassembled from the SHA-matched PE with `objdump -D -Mintel -w --start-address=0x84e980 --stop-address=0x84ea35` and reconciled with the complete uploaded `SHIFT_objdump_full.txt`. Exact original `.rdata` DWORDs checked by mapping PE file offset `0x006A4A00 + (VA-0x00AA6000)`, not estimated from the method offset.

## 1. Bounded conclusion and table target

Original adapter constructor `0x00850100` writes primary vptr `0x00B1BBA8`. The cell at **`0x00B1BCBC = 0x00B1BBA8+0x114`** has original bytes **`80 E9 84 00`** at PE file offset **`0x0071A6BC`**: its DWORD is **`0x0084E980`**. This resolves the **static adapter wrapper**, not any dynamic Direct3D device COM function pointer.

The wrapper is a **cached-or-forwarded three-method-argument setter**:
- `BYTE[adapter+4]!=0`: write raw `Value` into `DWORD[adapter+0xF8C+4*index]`, where **`index=((Sampler<<4)+Type) mod 2^32`**. If the corresponding valid/queued marker **`BYTE[adapter+0x178C+index]`** was zero, set it to 1, append a packed sampler/type DWORD to `adapter+0x138C` using count `adapter+0x188C` and increment count. **In either marker case**, OR **`0x4`** into `DWORD[adapter+0x19D8]` and return **EAX=0**. No COM call on this branch.
- `BYTE[adapter+4]==0`: obtain the previously byte-proven `IDirect3DDevice9*` from `DWORD[adapter+8]`; dispatch through the **dynamic** `DWORD[device.vptr+0x114]` with three unmodified method inputs plus device receiver; return the COM method's EAX **unaltered**.
- Both paths finish with **`RET 0x10`**, callee-cleanup of the wrapper's **four incoming DWORDs**, including stack receiver.

**API-level identity:** `IDirect3DDevice9::SetSamplerState(DWORD Sampler, D3DSAMPLERSTATETYPE Type, DWORD Value)`, D3D9 interface method index **69** (`69*4=0x114`). This is grounded by the proven CreateDevice-produced COM receiver **plus** standard D3D9 interface order and **exact three-value forwarding ABI**, not inferred solely from the matching offset. Official Windows SDK method definition: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-setsamplerstate . The retail PE carries **no source-level symbol**, no typed enum checks, and no fixed runtime COM EIP for this external method.

## 2. Exact wrapper ABI, branch conditions, caller cleanup

The complete original 41-instruction function is reproduced verbatim, with bytes, in Appendix A.

| Wrapper incoming location | Actual byte-derived use | API-level name |
|---|---|---|
| `[EBP+0x08]` | `0x0084E983: EAX=[EBP+8]`, used for `[EAX+4]`, cache, queued-byte, queue/count/dirty, and `[EAX+8]` device | adapter, explicit **stack receiver** (not entry ECX=this) |
| `[EBP+0x0C]` | `0x0084E98C: ECX=[EBP+0xC]`, left-shift by 4; also used in packed queue; reloaded `0x0084E9EC` | Sampler (arg1) |
| `[EBP+0x10]` | `0x0084E990: ESI=[EBP+0x10]`, added into index and OR-packed in queue; reloaded `0x0084E9E8` | Type (arg2) |
| `[EBP+0x14]` | `0x0084E999: EDI=[EBP+0x14]` and cached store; reloaded `0x0084E9DF` | Value (arg3) |

**Flag gate:** `0x0084E986: CMP BYTE PTR [EAX+4],0`, `0x0084E98A: JE 0x0084E9DF`. Nonzero falls through to cached setter. Zero jumps to underlying-device call.

**Cached exit:** `0x0084E9D8: XOR EAX,EAX` after queue/dirty bookkeeping, then restore ESI and EBP; restore EDI earlier at `0x0084E9D7`; **`0x0084E9DC: RET 0x10`**. This is a **synthesized full EAX=0** regardless of cache index validity or whether the queued-byte was already set. No local success test, HRESULT check or COM invocation on this path.

**Direct forwarding exit:** `0x0084E9F7: CALL EAX`, followed only by `POP EBP` at `0x0084E9F9` and `RET 0x10` at `0x0084E9FA`. **EAX is forwarded unchanged**. Calling it HRESULT is the *external D3D9 ABI interpretation*; no return-code normalization or error branch occurs in this wrapper.

Nonvolatile ESI and EDI are pushed only on the cached path and restored there; direct branch uses neither. EBP is saved/restored both paths. No frame locals are allocated, no extra-stack cleanup inside cached branch and no other calls.

## 3. Flag-nonzero branch: exact cache, marker, queue and dirty bits

All addresses below are relative to the **same stack-passed adapter** from `[EBP+8]`; no global object-type inference from coincident offsets.

### 3.1 Raw value and index

- At `0x0084E98C` read `Sampler` into ECX, at `0x0084E990` read `Type` into ESI, at `0x0084E993` copy Sampler to EDX, at `0x0084E995` **`SHL EDX,4`**, and `0x0084E99C` **`ADD EDX,ESI`**.
- Therefore **`index = ((Sampler << 4) + Type) mod 2^32`** (x86 32-bit arithmetic), with stride 16 per sampler only at the arithmetic level.
- `0x0084E999` loads the third incoming DWORD `Value` into EDI; **`0x0084E99E` writes `DWORD[adapter+0xF8C+index*4]=Value`** (original opcode `89 BC 90 8C 0F 00 00`). This is **exactly the address** read in the accepted neighboring cached sampler-state getter; not evidence of any live synchronized value.
- **No check** of Sampler, Type, index sign/range/overflow, table capacity or Value validity occurs before this write.

### 3.2 Marker branch: new queue entry vs existing marker

- `0x0084E9A5` compares **`BYTE[adapter+0x178C+index]`** with zero. A byte at that offset is used as a marker for *whether this index has been enqueued*, based on this function's own flow; it is not proven to mean an initialized/valid COM object or to have a particular startup value.
- If marker is **nonzero**: `0x0084E9AD: JNE 0x0084E9D0` skips marker-write, queue append and counter increment. The raw cache value *has already been overwritten*, and the dirty-mask OR *still executes*.
- If marker is **zero**: `0x0084E9AF` writes **`BYTE[adapter+0x178C+index]=1`**; `0x0084E9B7` reads **`count=DWORD[adapter+0x188C]`**; `0x0084E9BD: SHL ECX,16`; `0x0084E9C0: OR ECX,ESI`. This produces **`packed=((Sampler<<16) | Type) mod 2^32`** with **NO masking of Type to 16 bits**; arbitrary Type high bits could overlap the Sampler portion. `0x0084E9C2` appends **`DWORD[adapter+0x138C+4*count]=packed`**; `0x0084E9C9` increments **`DWORD[adapter+0x188C] += 1`** with normal 32-bit overflow semantics.
- At the join **`0x0084E9D0`**, **`DWORD[adapter+0x19D8] |= 0x4`** (opcode `83 88 D8 19 00 00 04`), preserving other mask bits, **regardless of whether the entry was enqueued this time**. This is distinct from the **byte `adapter+4`**, which the function *reads but does not set or clear*.

The mask `+0x19D8` and bit `0x4` match the previously proven texture/sampler state-sync helper's batch gating; this target alone does **not** establish that a later sync/Draw call executes.

### 3.3 Exact pseudocode of local stores (not reconstructed game source)

```c
uint32_t sampler = arg1, type = arg2, value = arg3;
uint32_t index = (sampler << 4) + type; // modulo 2^32
*(uint32_t *)(adapter + 0xF8C + 4u * index) = value;
if (*(uint8_t *)(adapter + 0x178C + index) == 0) {
    *(uint8_t *)(adapter + 0x178C + index) = 1;
    uint32_t count = *(uint32_t *)(adapter + 0x188C);
    uint32_t packed = (sampler << 16) | type; // NO Type & 0xffff
    *(uint32_t *)(adapter + 0x138C + 4u * count) = packed;
    ++*(uint32_t *)(adapter + 0x188C);
}
*(uint32_t *)(adapter + 0x19D8) |= 4;
return 0; // exact EAX=0
```

**Bounds and validation are absent locally:** no conditional bound against the indexed cache/marker arrays, no queue-capacity check of `count`, no guarding `count+1` overflow, no mask of Type, no validation of state enum/value, no check that the flag+4 and marker/queue were initialized correctly. The conditional marker test is **not** an index bounds test. Any externally documented sampler capabilities/API parameter rules do **not** become executable checks just because the forwarded COM method defines valid input ranges.

## 4. Flag-zero branch: exact device receiver and outgoing arguments

At `0x0084E9DF`:
- `EDX=[EBP+0x14]=Value`;
- `0x0084E9E2: EAX=DWORD[adapter+8]=D`;
- `0x0084E9E5: ECX=DWORD[D]=V` (dynamic underlying device vptr);
- `0x0084E9E7: PUSH Value`;
- `0x0084E9E8–0x0084E9EB: PUSH Type`;
- `0x0084E9EC–0x0084E9EF: PUSH Sampler`;
- `0x0084E9F0: PUSH D` (COM receiver);
- `0x0084E9F1: EAX=DWORD[V+0x114]`;
- **`0x0084E9F7: CALL EAX`**.

Thus the COM callee enters with four DWORDs: **`[ESP+4]=D`, `[ESP+8]=Sampler`, `[ESP+0xC]=Type`, `[ESP+0x10]=Value`** (after machine CALL's pushed return address). Standard COM stdcall cleans its own outgoing four-DWORD frame. The adapter wrapper independently cleans the *original incoming* four DWORDs via `RET 0x10`. No double stack cleanup.

Proven prior PE provenance: `0x00850109` places primary vptr `0x00B1BBA8` into the constructed adapter, `0x0085010F` sets `[adapter+8]` to supplied device; created device supplied by the already byte-traced `IDirect3D9::CreateDevice` output `[EDI]` at `0x00833095`, passed via `0x0084E2C0` and written at `0x0084E2DD`. `0x008330B7` publishes the embedded adapter pointer. **This is not a claim that the exact live pointer, dynamic device vptr or COM implementation EIP was observed.**

**Distinguish dispatches:** primary **adapter** slot `+0x114 → fixed retail executable `0x0084E980`, versus the **underlying device** slot `+0x114 → dynamically installed COM implementation pointer. Equal offsets do not identify equal receiver or function.

The API SetSamplerState signature has precisely **three input values**, not an output pointer. If the underlying call succeeds, setting a sampler state can mutate the **device's** sampler configuration per D3D9 contract, but this is **external COM behavior**, not a direct write to adapter cache in the zero-flag branch. No HRESULT check is performed here; the actual runtime result is unknown.

## 5. Bounded side effects / PE vs API / runtime evidence

**Direct original PE-byte stores, cached branch only:** raw DWORD cache value at `adapter+0xF8C+4*index`; optional byte marker `adapter+0x178C+index=1`; optional packed-word append to `adapter+0x138C+4*count`; optional count increment at `adapter+0x188C`; unconditional mask OR at `adapter+0x19D8`. No writes to `BYTE[adapter+4]`, even though this byte decides between paths. No local texture object AddRef/Release, pointer ownership transfer, allocated object, underlying device call or output pointer in this cached branch.

**Direct calls in entire function:** exactly **one** indirect call, `0x0084E9F7`, on the **zero flag** forwarding branch; it is an API-classified `IDirect3DDevice9::SetSamplerState`, **not** BeginStateBlock/EndStateBlock or Draw*. No primary adapter slot `+0xF0`, no direct D3D9 Draw* import, no primitive dispatch in this wrapper. The cached branch does **not** call the device, so a later flush is a distinct unproven event, not automatically a successful state change in the device.

**PE-byte established:** SHA; actual original vtable `0x00B1BCBC→0x0084E980`, full code; explicit stack ABI, cached key arithmetic and *all* field addresses and conditional/unconditional stores; COM forwarding order; both `RET 0x10` exits; zero EAX cached return and unchanged EAX forwarded; no bounds or error checks.

**External API interpretation:** Microsoft defines `IDirect3DDevice9::SetSamplerState(DWORD, D3DSAMPLERSTATETYPE, DWORD)` returning HRESULT. The name and API validity/possible device-side effects follow proven IDirect3DDevice9 receiver, slot 69 and three parameter ABI; the PE has neither source type information nor direct import symbol for this vtable dispatch. External reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-setsamplerstate .

**Runtime:** no new replay, execution, guest instrumentation or state modification. User-supplied earlier bounded v757 replay measured *different* selected Begin/End/Draw targets for 360 host frames (zero events); it **does not establish whether `0x0084E980` ever executed**, what cache values were live, or what D3D9 HRESULT would be returned. No global reachability claim.

**Unresolved, not investigated:** true valid Sampler/Type index domain, queue capacities and initializer values, whether queued changes ever flush, live adapter/device pointer/vptr, real callsites, aliases, dynamic COM method EIP and HRESULT, complete resource ownership lifecycle.

## 6. Exactly one next evidence-backed target

**`0x0084FCF0`**, the next **primary adapter slot `+0x118`**, proven directly by original PE `.rdata`: **`DWORD[0x00B1BCC0]=0x0084FCF0`** (little-endian bytes `F0 FC 84 00`). Its original short function checks `BYTE[adapter+4]` and, when nonzero, **directly calls `0x0084F000`** before forwarding to **`underlyingDevice.vptr+0x118`**. This is a precise, separate opportunity to test a concrete deferred-state flush gate in the next task without broad sweeps or presuming dynamic execution. **No other next target is proposed.** Importantly, the next PE function in *linear address order*, `0x0084EA00`, is **not** asserted to be the next adapter vtable slot; this entry was read from `.rdata`.

## Appendix A — full original wrapper 0x0084E980–0x0084E9FC (41 decoded instructions, both RETs)

```asm
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
  84e9af:	c6 84 02 8c 17 00 00 01 	mov    BYTE PTR [edx+eax*1+0x178c],0x1
  84e9b7:	8b 90 8c 18 00 00    	mov    edx,DWORD PTR [eax+0x188c]
  84e9bd:	c1 e1 10             	shl    ecx,0x10
  84e9c0:	0b ce                	or     ecx,esi
  84e9c2:	89 8c 90 8c 13 00 00 	mov    DWORD PTR [eax+edx*4+0x138c],ecx
  84e9c9:	83 80 8c 18 00 00 01 	add    DWORD PTR [eax+0x188c],0x1
  84e9d0:	83 88 d8 19 00 00 04 	or     DWORD PTR [eax+0x19d8],0x4
  84e9d7:	5f                   	pop    edi
  84e9d8:	33 c0                	xor    eax,eax
  84e9da:	5e                   	pop    esi
  84e9db:	5d                   	pop    ebp
  84e9dc:	c2 10 00             	ret    0x10
  84e9df:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84e9e2:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e9e5:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e9e7:	52                   	push   edx
  84e9e8:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e9eb:	52                   	push   edx
  84e9ec:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e9ef:	52                   	push   edx
  84e9f0:	50                   	push   eax
  84e9f1:	8b 81 14 01 00 00    	mov    eax,DWORD PTR [ecx+0x114]
  84e9f7:	ff d0                	call   eax
  84e9f9:	5d                   	pop    ebp
  84e9fa:	c2 10 00             	ret    0x10
```

## Appendix B — original constructor 0x00850100–0x00850180, pointer provenance only

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

## Appendix C — exact adjacent primary vtable cells + bounded next method block

```text
.rdata 0x00B1BCB8: 30 E9 84 00 -> 0x0084E930   (adapter +0x110)
.rdata 0x00B1BCBC: 80 E9 84 00 -> 0x0084E980   (adapter +0x114)
.rdata 0x00B1BCC0: F0 FC 84 00 -> 0x0084FCF0   (adapter +0x118)
```

```asm
  84fcf0:	55                   	push   ebp
  84fcf1:	8b ec                	mov    ebp,esp
  84fcf3:	56                   	push   esi
  84fcf4:	8b 75 08             	mov    esi,DWORD PTR [ebp+0x8]
  84fcf7:	80 7e 04 00          	cmp    BYTE PTR [esi+0x4],0x0
  84fcfb:	74 07                	je     0x84fd04
  84fcfd:	8b ce                	mov    ecx,esi
  84fcff:	e8 fc f2 ff ff       	call   0x84f000
  84fd04:	8b 46 08             	mov    eax,DWORD PTR [esi+0x8]
  84fd07:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84fd0a:	8b 08                	mov    ecx,DWORD PTR [eax]
  84fd0c:	52                   	push   edx
  84fd0d:	50                   	push   eax
  84fd0e:	8b 81 18 01 00 00    	mov    eax,DWORD PTR [ecx+0x118]
  84fd14:	ff d0                	call   eax
  84fd16:	5e                   	pop    esi
  84fd17:	5d                   	pop    ebp
  84fd18:	c2 08 00             	ret    0x8
```

## Appendix D — only the previously established device-pointer publication instructions

```asm
00833095: 8b 17                    mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00       lea    ecx,[esi+0x1f7c]
0083309d: 52                       push   edx
0083309e: e8 1d b2 01 00          call   0x84e2c0
0084e2dd: 89 46 08                mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00       lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00       mov    DWORD PTR [esi+0x478],eax
```

**Report-only commit:** do not alter code/runtime/P-code/renderer/guest-state/P2 files, do not claim live game execution, do not perform global searches or replay.
