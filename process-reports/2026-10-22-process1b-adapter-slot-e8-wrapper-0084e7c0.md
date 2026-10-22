# Process 1 — retail adapter +0xE8 getter wrapper (0x0084E7C0)

**Date:** 2026-10-22. **Scope:** exclusively the original retail PE adapter vtable `+0xE8` method `0x0084E7C0`, its two local branches, stack ABI, established adapter/device provenance and bounded negative tests. No global byte-field or setter sweep, renderer implementation, P-code/runtime modifications, field forcing or new replay. This is a **new task**, not a revision or repeat of the completed `+0xE4` study.

**Binary:** Need for Speed SHIFT PC retail 1.02; PE32 x86; ImageBase `0x00400000`. **Verified original SHA-256:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Original `SHIFT.exe` was SHA-256 checked in this task, and `objdump -D -M intel -w` independently reproduced the user-supplied `0x0084E7C0–0x0084E7F5` machine-code block. `.rdata` dump independently checked in this task. The prior `0x0082E4A0/+0xE4` report's initialized wrapper/adapter provenance is reused as stated, not reanalyzed.

**Timing provenance:** the precise delivery/startedAt UTC metadata for this turn is not exposed to the available tooling. Therefore no delivery timestamp or inferred 12-minute deadline UTC value is manufactured here. This report is committed as part of the response to the live request.

## Core conclusion

**The original PE proves a three-stack-DWORD adapter method with a local cached-value read when `BYTE[adapter+4]!=0` and a device-vtable forwarding call when `BYTE[adapter+4]==0`.** Under the previously verified standard `IDirect3D9::CreateDevice` pointer provenance, its device call has precisely the `IDirect3DDevice9::GetRenderState(D3DRENDERSTATETYPE, DWORD*)` ABI: underlying device interface index **58**, vtable offset **0xE8**. The identity is supported by both interface object provenance and exact two-argument call shape, **not inferred from the slot number alone**.

**No direct or indirect Draw* call, BeginStateBlock call, or direct write of `BYTE[adapter+4]` appears in this target block.** Any runtime entry, actual device method code address, runtime HRESULT, and pointer alias outcomes are outside the evidence here.

## 1. Primary adapter vtable and device provenance

The original PE contains primary adapter vptr `0x00B1BBA8` initialized at **`0x00850109`** by `0x00850100`. The `.rdata` DWORD at **`0x00B1BC90 = 0x00B1BBA8+0xE8`** is original bytes **`C0 E7 84 00`**, decoded little-endian as **`0x0084E7C0`**. For context, `0x00B1BC8C` contains `0x0084E750` (the *different* neighboring slot `+0xE4`; no renewed analysis of that target).

The original constructor `0x00850100` at **`0x0085010F`** puts its stack-provided pointer in **`DWORD[adapter+8]`**, and at **`0x00850176`** writes **`BYTE[adapter+4]=0`**. An independently checked initialization route **`0x00833095–0x0083309E → 0x0084E2C0`** supplies the device returned via the preceding `IDirect3D9::CreateDevice` call, and `0x0084E2DD` stores it in adapter+8. The wrapper publishes embedded `wrapper+0x1F7C` as `[wrapper+0x478]` at **`0x008330B7`** and sets `BYTE[wrapper+0x5E8]=1` at **`0x008330D0`**. The verified getter `0x0082E110` on that initialized path reads `[wrapper+0x478]` and returns the constructed adapter pointer.

**Distinct vptrs:** the adapter primary table at `0x00B1BBA8` dispatches **to this executable wrapper**. Inside its zero-flag branch, **`device=[adapter+8]` and `DWORD[device]` is the separate, externally provided D3D9 COM device vptr**. Its actual runtime function pointer at `device.vptr+0xE8` is not fixed to a retail PE code address and cannot be resolved further from static `.rdata`; only its interface/ABI identity is justified.

## 2. ABI, stack offsets, cleanup, register effects

**Wrapper callee**: entry stack carries **three DWORDs**, all cleaned by this wrapper's **`RET 0x0C`** (both branches). A standard stack-passed receiver, **not ECX=this**. The prologue/epilogue saves and restores EBP only; **no local stack allocation**, no EBX/ESI/EDI use. It changes EAX, ECX, EDX as volatile work registers. There are exactly **two normal returns**, at byte addresses `0x0084E7DB` and `0x0084E7F5` (each `RET 0xC` instruction includes two subsequent operand bytes). No exception/error alternative or nested local helper exists in the bounded block.

| Stack location | Argument | Role proved by original instructions |
|---|---|---|
| `[EBP+0x08]` | **adapter** | used to read byte +4, DWORD cache base +0xC and underlying device pointer +8 |
| `[EBP+0x0C]` | **stateID** | used as 32-bit `ECX` index in `[adapter+stateID*4+0xC]`, or pushed as first explicit COM method argument |
| `[EBP+0x10]` | **outputPointer** | receives one DWORD in cached branch, or is passed as second explicit COM argument |

At original callsite `0x0084E7CF`, indexing is `DWORD PTR [EAX+ECX*4+0xC]`; there is **no mask, signed/unsigned bounds comparison, index normalization, table length check or pointer validation in this function**. A raw 32-bit index `stateID` controls address arithmetic. The code does not prove a particular caller's permissible index range or whether every possible index denotes valid cached memory.

## 3. Cached branch: BYTE[adapter+4] != 0

Control flow:
1. `0x0084E7C3`: `EAX=adapter`. `0x0084E7C6: CMP BYTE[adapter+4],0`. `0x0084E7CA: JE 0x0084E7DE` **only if zero**; otherwise fall through to cached branch.
2. `0x0084E7CC: ECX=[EBP+0xC]` = stateID.
3. `0x0084E7CF: EDX=DWORD[adapter+0xC+4*stateID]`.
4. `0x0084E7D3: EAX=[EBP+0x10]` = outputPointer; **`0x0084E7D6: DWORD[outputPointer]=EDX`**, the **sole** explicit data write (apart from prologue stack housekeeping) on this path.
5. `0x0084E7D8: XOR EAX,EAX` gives exactly full **`EAX=0`**, regardless of cached value; then POP EBP and RET 0xC at `0x0084E7DB`.

There is **no call** on this path, hence no direct device query or output status from device. The target neither changes its cached entry nor adjusts any dirty flag. The interpretation as a state-value cache is anchored by the literal read pattern and earlier verified setter's write to the **same indexed DWORD region**; no source-level class field or API type is inferred merely from proximity.

**Alias qualification:** source bytes do not contain an explicit `MOV BYTE[adapter+4],...`. In principle, an externally chosen `outputPointer=adapter+4` could make the generic `MOV DWORD [outputPointer],EDX` alias this address. Such an alias is **not demonstrated by any bounded caller evidence**; the intended contract is an output DWORD supplied by caller. Therefore the result is **no proved adapter+4 writer**, not a universal memory-noninterference claim.

## 4. Direct device forwarding branch: BYTE[adapter+4] == 0

At `0x0084E7CA`, `JE` enters `0x0084E7DE`:
- `0x0084E7DE:` EDX=`outputPointer`.
- `0x0084E7E1:` EAX=`DWORD[adapter+8]` = underlying COM device `D`.
- `0x0084E7E4:` ECX=`DWORD[D]` = underlying device vptr `V`.
- `0x0084E7E6:` `PUSH outputPointer`.
- `0x0084E7E7–0x0084E7EA:` `PUSH stateID`.
- `0x0084E7EB:` `PUSH D` as underlying COM `this`.
- `0x0084E7EC:` EAX=`DWORD[V+0xE8]`; **`0x0084E7F2: CALL EAX`**.
- `0x0084E7F4–0x0084E7F5:` POP EBP; RET 0xC.

Thus the called COM frame is `[ESP+4]=D`, `[ESP+8]=stateID`, `[ESP+0xC]=outputPointer` at function entry (post-call return address at `[ESP]`). The actual D3D9 device method is expected to clean **12 bytes** (`this`+two arguments) via stdcall; the outer adapter wrapper independently cleans **its own 12 bytes** with `RET 0xC`.

**Return:** the original wrapper performs **no instructions that modify EAX after `CALL EAX`** except `POP EBP` and `RET 0xC`; the result from the underlying device reaches caller unchanged. In standard D3D9 signature this is an `HRESULT`, but no explicit HRESULT sign/equality check occurs here. The **underlying COM method** may write the output pointer or fail; its actual implementation and runtime result are not observable solely from the supplied PE bytes. No explicit output write is present in this wrapper's zero-flag branch.

**Identification:** a CreateDevice-produced IDirect3DDevice9 COM object, slot index `0xE8 / 4 = 58` and a method expecting exactly `stateID, pointer to DWORD output` jointly agree with **`IDirect3DDevice9::GetRenderState(D3DRENDERSTATETYPE, DWORD*)`**. Device target EIP is **not** resolved from retail PE; exact dynamic target remains unspecified. This is a qualified ABI-level interface identification, not invention of a linked PE helper.

## 5. Draw*/BeginStateBlock/+4 checks, bounded strictly to this function

There is exactly **one** CALL instruction in the complete target: `0x0084E7F2: CALL EAX`, through `[device.vptr+0xE8]`, with the *GetRenderState-compatible* two-argument contract. There are **zero** direct rel32 CALLs, **zero** CALLs to adapter primary `+0xF0` (previously identified as `0x0084FBC0`), **zero** Draw* slot callsites or imports, and **zero** instructions explicitly writing `BYTE[adapter+4]`. The cached path has a one-DWORD output store at caller-controlled pointer; no call anywhere on that branch.

The absence of an executable Draw*/Begin call here does **not** establish global absence from the game, the adapter class, neighboring vtable methods or other guest states. The function does not itself force or toggle its cache-enabled byte.

## 6. PE-byte facts vs prior runtime observation vs inference

**PE-byte established and independently checked:** exact original SHA and disassembly; vtable DWORD `0x00B1BC90 → 0x0084E7C0`; constructor vptr and underlying-device pointer fields; fixed stack argument positions and `RET 0xC` on both paths; no index bounds check; cached DWORD read and output DWORD store; unconditional EAX=0 cached return; forwarding argument pushes, device vptr dereference, underlying `+0xE8` dispatch; no explicit writes to flag +4 and no other CALLs.

**External standard COM interpretation plus proved pointer origin:** the underlying method is IDirect3DDevice9 GetRenderState, identified by the CreateDevice-derived device pointer, slot ordering **and** actual two-argument signature. The actual virtual function address comes from dynamically installed COM vptr, *not* original PE `.rdata`.

**Prior runtime observation only:** user-supplied v757 P-code replay of 360 host frames reported no events on its specific traced BeginStateBlock/Draw* target set. **It did not target `0x0084E7C0`** and does **not** prove this getter ran or did not run; no trace/replay was performed in this task. No claims of game launch, P-code dispatch count or rendered frames are made.

**Unknown:** actual runtime `adapter+4` value at any call, input state IDs, output pointer alias/validity, dynamic COM device target EIP, actual HRESULT, downstream callsites of `0x0084E7C0`, and the full range of callers/field writers (outside requested scope).

## 7. Exactly one next evidence-backed target

**`0x0084FBA0`**, the **next primary adapter vtable slot `+0xEC`**, because PE `DWORD[0x00B1BC94]=0x0084FBA0`. Its original start bytes show the same stack-passed adapter plus two more stack values and a forwarding operation through **`underlyingDevice.vptr+0xEC`**. This is a narrow, contiguous ABI/vtable provenance follow-up, not a global caller or field-writer audit. No semantic name is assigned until that complete function's bytes are checked in the next independent task.

## Appendix A — entire exact original function `0x0084E7C0–0x0084E7F5` (final RET instruction spans through `0x0084E7F7`)

```asm
84e7c0:	55                   	push   ebp
  84e7c1:	8b ec                	mov    ebp,esp
  84e7c3:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e7c6:	80 78 04 00          	cmp    BYTE PTR [eax+0x4],0x0
  84e7ca:	74 12                	je     0x84e7de
  84e7cc:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84e7cf:	8b 54 88 0c          	mov    edx,DWORD PTR [eax+ecx*4+0xc]
  84e7d3:	8b 45 10             	mov    eax,DWORD PTR [ebp+0x10]
  84e7d6:	89 10                	mov    DWORD PTR [eax],edx
  84e7d8:	33 c0                	xor    eax,eax
  84e7da:	5d                   	pop    ebp
  84e7db:	c2 0c 00             	ret    0xc
  84e7de:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e7e1:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e7e4:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e7e6:	52                   	push   edx
  84e7e7:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e7ea:	52                   	push   edx
  84e7eb:	50                   	push   eax
  84e7ec:	8b 81 e8 00 00 00    	mov    eax,DWORD PTR [ecx+0xe8]
  84e7f2:	ff d0                	call   eax
  84e7f4:	5d                   	pop    ebp
  84e7f5:	c2 0c 00             	ret    0xc
```

## Appendix B — original adapter initializer `0x00850100–0x0085017E` (vptr, +8 and +4 provenance)

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

## Appendix C — original getter `0x0082E110–0x0082E131` (conditionally returns published adapter)

```asm
82e110:	80 b9 e8 05 00 00 00 	cmp    BYTE PTR [ecx+0x5e8],0x0
  82e117:	74 07                	je     0x82e120
  82e119:	8b 81 78 04 00 00    	mov    eax,DWORD PTR [ecx+0x478]
  82e11f:	c3                   	ret
  82e120:	8b 01                	mov    eax,DWORD PTR [ecx]
  82e122:	8b 80 e8 02 00 00    	mov    eax,DWORD PTR [eax+0x2e8]
  82e128:	ba 0a 00 00 00       	mov    edx,0xa
  82e12d:	ff d0                	call   eax
  82e12f:	33 c0                	xor    eax,eax
  82e131:	c3                   	ret
```

## Appendix D — verified adjacent +0xEC target's immediate bytes (anchor only; not analyzed as part of this task)

```asm
84fba0:	55                   	push   ebp
  84fba1:	8b ec                	mov    ebp,esp
  84fba3:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84fba6:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84fba9:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84fbac:	8b 08                	mov    ecx,DWORD PTR [eax]
  84fbae:	52                   	push   edx
  84fbaf:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84fbb2:	52                   	push   edx
  84fbb3:	50                   	push   eax
  84fbb4:	8b 81 ec 00 00 00    	mov    eax,DWORD PTR [ecx+0xec]
  84fbba:	ff d0                	call   eax
  84fbbc:	5d                   	pop    ebp
  84fbbd:	c2 0c 00             	ret    0xc
```

## Appendix E — retail .rdata vtable cell bytes and pointer publication

```text
.rdata VA 0x00B1BC8C: 50 e7 84 00  →  0x0084E750   (adapter slot +0xE4)
.rdata VA 0x00B1BC90: c0 e7 84 00  →  0x0084E7C0   (adapter slot +0xE8)
.rdata VA 0x00B1BC94: a0 fb 84 00  →  0x0084FBA0   (adapter slot +0xEC)
```

```asm
00833095: 8b 17                   mov edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00      lea ecx,[esi+0x1f7c]
0083309d: 52                      push edx
0083309e: e8 1d b2 01 00         call 0x84e2c0
008330b1: 8d 86 7c 1f 00 00      lea eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00      mov DWORD PTR [esi+0x478],eax
008330d0: c6 86 e8 05 00 00 01   mov BYTE PTR [esi+0x5e8],0x1
0084e2dd: 89 46 08               mov DWORD PTR [esi+0x8],eax
```

**Report-only submission.** No executable or runtime file changes, no PR, no replay, and no reopening canceled bounded tasks.
