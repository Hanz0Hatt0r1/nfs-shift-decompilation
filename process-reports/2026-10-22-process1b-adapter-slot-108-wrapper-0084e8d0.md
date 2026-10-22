# Process 1 — retail primary adapter slot +0x108, wrapper 0x0084E8D0

**Date:** 2026-10-22 (UTC). **Binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **Original PE SHA-256 (reverified against `SHIFT.exe`):** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Exact scope:** original retail executable block `0x0084E8D0–0x0084E8F3`, primary adapter virtual slot `+0x108`, the previously established constructor/created-device pointer join and one adjacent vtable-slot anchor. All code bytes below are taken from the uploaded full `SHIFT_objdump_full.txt` and independently checked with PE `objdump -D -Mintel -w`. The adapter table DWORDs were independently read from original PE `.rdata`; no global vtable/caller/supplier/writer sweep. The already accepted slot `+0x104` report supplies bounded context; it is not repeated.

**No code changes, runtime or guest-state writes, replay, renderer changes, game-launch claims or P2 changes.** Only a Markdown report is added under `process-reports/`.

## 1. Direct answer and confidence boundary

**PE-byte fact:** At primary adapter vptr `0x00B1BBA8`, `DWORD[0x00B1BCB0] = DWORD[0x00B1BBA8+0x108] = 0x0084E8D0`. Original bytes at `0x00B1BCB0` are `D0 E8 84 00`. This connects the *adapter primary table* to the actual retail wrapper implementation. The function receives **four stack DWORDs**, does **not branch**, reads `D=DWORD[adapter+8]`, and makes exactly **one** indirect call to `F=DWORD[DWORD[D]+0x108]` with the receiver `D` plus three arguments pushed in original order (right-to-left on the stack). It returns the device callee's EAX unchanged via `RET 0x10`.

**API identification, not a symbol embedded in PE:** The object at `adapter+8` has original `IDirect3DDevice9*` provenance through the proven `IDirect3D9::CreateDevice` initialization path. For that interface, virtual slot **66** (`0x108 / 4`) is **`IDirect3DDevice9::GetTextureStageState(DWORD Stage, D3DTEXTURESTAGESTATETYPE Type, DWORD *pValue)`**. This is corroborated by an exact method signature of **three explicit DWORD arguments**, of which the last is forwarded without dereference as a potential output pointer, and the known D3D9 interface ordering. It must not be inferred from slot offset in isolation. Official reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-gettexturestagestate and an independently published ordered interface declaration: https://cycrow.co.uk/websvn/filedetails.php?path=%2FDirect3D-Hook%2Fsrc%2FHook%2FMyDirect3DDevice9.h&repname=spk&rev=11 .

**Not resolved:** The function pointer actually contained in the **dynamic underlying device vtable** `DWORD[DWORD[D]+0x108]` is **not** a fixed original PE implementation EIP; no specific address or invocation at runtime is asserted. Neither the object at `adapter+8` nor any parameter has been sampled in a live replay in this task.

## 2. Exact incoming stack ABI, outgoing order and cleanup

The full byte-exact 16-instruction retail function is in Appendix A. `0x0084E8D0: PUSH EBP; 0x0084E8D1: MOV EBP,ESP`. **Incoming ECX=this is not used** for the adapter receiver; the receiver is explicit on the stack. No local stack allocation, no nonvolatile EBX/ESI/EDI operations.

| Incoming on wrapper stack | PE-evidenced use | Interface interpretation |
|---|---|---|
| `[EBP+0x08]` | `0x0084E8D6: EAX=[EBP+8]`, then `0x0084E8D9: EAX=[EAX+8]` | **adapter receiver**, supplies `IDirect3DDevice9*` |
| `[EBP+0x0C]` | `0x0084E8E3: EDX=[EBP+0xC]`, then `0x0084E8E6: PUSH EDX` | `DWORD Stage` (first COM method parameter) |
| `[EBP+0x10]` | `0x0084E8DF: EDX=[EBP+0x10]`, then `0x0084E8E2: PUSH EDX` | `D3DTEXTURESTAGESTATETYPE Type` (second COM method parameter) |
| `[EBP+0x14]` | `0x0084E8D3: EDX=[EBP+0x14]`, then `0x0084E8DE: PUSH EDX` | `DWORD* pValue` (third COM method parameter, output according to API) |

Actual instructions and value preservation:

1. `0x0084E8D3` loads **arg3** (potential output pointer) into EDX; `0x0084E8D6` loads adapter; `0x0084E8D9` loads `D=[adapter+8]`; `0x0084E8DC` loads `V=[D]` into ECX. No manipulation of arg3 occurs.
2. `0x0084E8DE: PUSH arg3`; `0x0084E8DF–0x0084E8E2: PUSH arg2`; `0x0084E8E3–0x0084E8E6: PUSH arg1`; `0x0084E8E7: PUSH D`. Thus the nested COM call enters with **`[ESP+4]=D`, `[ESP+8]=Stage`, `[ESP+0xC]=Type`, `[ESP+0x10]=pValue`** after CALL pushed its return address.
3. `0x0084E8E8: EAX=[V+0x108]`; `0x0084E8EE: CALL EAX`. Only this **one** CALL exists in the wrapper, and only the dynamic external vtable slot is used.
4. `0x0084E8F0: POP EBP`; `0x0084E8F1: RET 0x10` (encoded bytes `C2 10 00`, final instruction spans through `0x0084E8F3`). The wrapper cleans its **own four stack DWORDs (16 bytes)**. The nested COM method separately cleans its own **four outgoing DWORDs**, if it follows the IDirect3DDevice9 stdcall ABI. These are separate call frames, so there is no double cleanup.
5. No instruction after the indirect CALL modifies EAX. Therefore **raw EAX passthrough** is byte-proven, while calling it **HRESULT** depends on the IDirect3DDevice9 API identity. There is **no sign/equality check**, bool coercion or HRESULT normalization; no retry, fallthrough, recovery or alternate epilogue.

The code performs no local null check of `adapter`, `D`, `V` or `pValue`. It neither dereferences the supplied output pointer nor validates `Stage`/`Type`. An invalid address could fault in the wrapper's unavoidable pointer dereferences; this function has no handling code.

## 3. Exact bounded pointer provenance (not a slot-number shortcut)

The ordinary constructor `0x00850100` stores **`DWORD[adapter]=0x00B1BBA8`** at `0x00850109`; `0x0085010F` stores constructor's supplied device pointer in **`DWORD[adapter+8]`**. The accepted retail initializer path `0x0083304D–0x0083306C` invokes a method of its `IDirect3D9` receiver through interface slot `+0x40` with a CreateDevice-compatible output; `0x00833095–0x0083309E` passes the created device pointer from `[EDI]` into adapter helper `0x0084E2C0`, whose instruction `0x0084E2DD` stores the created pointer in adapter+8. The wrapper publishes the constructed embedded adapter `wrapper+0x1F7C` to `[wrapper+0x478]` at `0x008330B7`.

The proven Join for this path is:

```text
IDirect3D9::CreateDevice output
      → constructor-supplied IDirect3DDevice9* D
      → DWORD[adapter+8] = D
      → this wrapper 0x0084E8D9 reads D
      → V = DWORD[D]  (dynamic underlying device vptr)
      → F = DWORD[V+0x108]  (dynamic COM method)
      → call F(D, Stage, Type, pValue)
```

**Two distinct virtual dispatch domains:** static PE `adapter.vptr+0x108=0x0084E8D0` chooses *this wrapper*, whereas the **dynamic device.vptr+0x108** chooses *a D3D9 COM implementation*. Equal displacement does not equate receiver identity or executable targets. No dynamic pointer value, vptr invariance after construction, or game run is assumed.

The external D3D9 signature indicates Stage and Type inputs plus **`DWORD* pValue` output** (not an input state change). The standard API reference states Stage is zero-based with documented upper bound 7 for the device API; **this target contains no stage range check of its own**, and that API bound is not a proof that the wrapper enforced or exercised such a constraint. On a valid underlying call the API may write a DWORD through pValue and return `D3D_OK`, or report an error such as `D3DERR_INVALIDCALL`, but none of those effects/results is evidenced to have happened here.

## 4. Local effects and bounded negative conclusions

**Direct writes to adapter / cache / flags:** zero. Unlike the accepted neighboring cached SetTexture method, this wrapper has **no flag test** `BYTE[adapter+4]` and **no** write/read to `adapter+0x1908`, `+0x1988`, `+0x198C`, `+0x19D8`, nor any other adapter field beyond the initial **read of `adapter+8`**. It does **not** implement cached texture-stage-state reads. There is **no cache/dirty queue mutation**, validation or local state write.

**Calls:** exactly **one** indirect external call, `0x0084E8EE`, through `device.vptr+0x108`. Since the provenance/ABI identifies **GetTextureStageState**, it is **not** a BeginStateBlock/EndStateBlock nor a Draw* operation. No other direct/indirect CALL is present; no event, frame, draw or guest dispatch counter is inferred.

**Indirect output side effect caveat:** `pValue` is forwarded unchanged; **external COM** may write to the caller's pointed-to DWORD. This is **not** an instruction writing adapter memory in the retail wrapper. A caller might pass an alias to adapter storage, but **no such alias path is demonstrated**; the bounded finding is no **proven** adapter/cache/flag write, not a universal non-interference guarantee against unknown input pointer aliasing or external COM internals.

**No AddRef/Release or texture ownership operations** occur in the wrapper. No cache ownership implication can be inferred from neighboring methods or a name match. The standard GetTextureStageState API queries a stage-state value, not a texture object acquisition; it has no resource-pointer AddRef visible here.

## 5. Evidence ledger: PE / external API / runtime

**Original retail PE, directly checked:** exact SHA-256; `.rdata` value `[0x00B1BCB0]=0x0084E8D0` (original bytes `D0 E8 84 00`); full function `0x0084E8D0–0x0084E8F3` including 16 decoded instructions; all four explicit stack DWORD arguments and pushes; `[adapter+8]` device read; single `[device.vptr+0x108]` call; `RET 0x10` and raw EAX passthrough; no branches or memory stores in original block. Constructor byte provenance re-used and original constructor block reproduced below.

**External API-level inference (grounded):** IDirect3DDevice9::GetTextureStageState, virtual method index **66**, parameter types `DWORD Stage, D3DTEXTURESTAGESTATETYPE Type, DWORD* pValue`, output semantics and HRESULT. Interface method ordering plus correct four-DWORD COM stack frame and proven object type justify the name. Exact COM method EIP, its implementation and result are not derivable from retail PE.

**Prior runtime observations only:** user-supplied bounded v757 P-code replay selected Begin/EndStateBlock/Draw* targets (reported zero events during 360 host frames), **not** the current wrapper; it establishes nothing about whether `0x0084E8D0` ran. **No new replay, emulator/runtime execution, game launch or state-forcing action was performed**, and the PE is not evidence of actual execution.

**Unresolved:** current dynamic device pointer/vtable in any host frame, Stage/Type and pValue values from a real caller, caller aliases, actual HRESULT/pValue state, and downstream COM effects. Deliberately excluded: any global search of adapter setter methods, callers or writer graphs.

## 6. Exactly one next evidence-backed target

**`0x0084E900` — adjacent primary adapter slot `+0x10C`**. The original PE `.rdata` contains **`DWORD[0x00B1BCB4]=0x0084E900`** (bytes `00 E9 84 00`). Its immediate neighboring retail bytes already exhibit a three-explicit-argument forwarding shape to **`underlyingDevice.vptr+0x10C`**. A separate bounded ABI/API check can determine whether this is the corresponding texture-stage-state setter; **no semantics for that target are claimed proven in this report**. Exactly this one follow-up is proposed.

## Appendix A — entire original wrapper, machine bytes 0x0084E8D0–0x0084E8F3

```asm
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
  84e8f0:	5d                   	pop    ebp
  84e8f1:	c2 10 00             	ret    0x10
```

## Appendix B — entire original adapter constructor 0x00850100–0x00850180 (last RET starts 0x0085017E)

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

## Appendix C — original vtable neighboring cells and next target (anchor only)

```text
.rdata 0x00B1BCAC: 60 E8 84 00 → 0x0084E860  (primary adapter slot +0x104)
.rdata 0x00B1BCB0: D0 E8 84 00 → 0x0084E8D0  (primary adapter slot +0x108)
.rdata 0x00B1BCB4: 00 E9 84 00 → 0x0084E900  (primary adapter slot +0x10C)
```

```asm
  84e900:	55                   	push   ebp
  84e901:	8b ec                	mov    ebp,esp
  84e903:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84e906:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e909:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e90c:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e90e:	52                   	push   edx
  84e90f:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e912:	52                   	push   edx
  84e913:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e916:	52                   	push   edx
  84e917:	50                   	push   eax
  84e918:	8b 81 0c 01 00 00    	mov    eax,DWORD PTR [ecx+0x10c]
  84e91e:	ff d0                	call   eax
  84e920:	5d                   	pop    ebp
  84e921:	c2 10 00             	ret    0x10
```

## Appendix D — short original device-pointer provenance anchors (no renewed full class audit)

```asm
00833095: 8b 17                 mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea    ecx,[esi+0x1f7c]
0083309d: 52                    push   edx
0083309e: e8 1d b2 01 00        call   0x84e2c0
0084e2dd: 89 46 08              mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov    DWORD PTR [esi+0x478],eax
```

**Report only.** No executable, renderer, P1/P2 source, runtime state, P-code or guest-state file changes, and no replay or PR.
