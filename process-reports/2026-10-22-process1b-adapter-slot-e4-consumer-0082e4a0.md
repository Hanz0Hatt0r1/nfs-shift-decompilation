# Process 1 — retail adapter slot +0xE4, consumer 0x0082E4A0

**Audit date:** 2026-10-22 UTC. **PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **Independently checked original PE SHA-256:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Source: original `SHIFT.exe`, the uploaded full `SHIFT_objdump_full.txt`, PE `.rdata`, and the previously closed getter provenance [commit `087f598d61a2c043bd3aa088c596fffe76c7c84e`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process1b-wrapper-adapter-getter-0082e110.md). No code changes, no runtime replay or renderer edits. The actual delivery timestamp of the current user message is **not exposed in accessible message metadata**; the earliest independently observed UTC clock after receipt was **2026-10-22 05:28:20 UTC** (not asserted to equal delivery time). No invented send timestamp.

## Bounded conclusion

**The actual PE vtable target is `0x0084E750`, a conditional adapter-side `SetRenderState` wrapper, *not* `BeginStateBlock`.** The original PE .rdata DWORD at **`0x00B1BC8C = 0x00B1BBA8 + 0xE4`**, file offset **`0x0071A68C`**, has bytes **`50 E7 84 00`**, hence `0x0084E750`. Neighboring +0xE8 at `0x00B1BC90` holds `0x0084E7C0`, which is a distinct function.

**On the ordinary initialized path**, the consumer's `ECX=wrapper` meets the getter precondition `BYTE[wrapper+0x5E8]!=0`: getter returns `DWORD[wrapper+0x478]` which constructor flow assigned `wrapper+0x1F7C`, whose primary vptr `0x00B1BBA8` is set by `0x00850100`. Thus the two executable virtual calls at **0x0082E4D5 / 0x0082E4FB** resolve to the actual adapter `0x0084E750`, with **explicit pushed adapter receiver**, not ECX=this. This is a conditional constructor/vtable path, not a dynamic proof of current vptr or execution in any P-code replay. If getter falls back to zero, the consumer does **not** null-check EAX before `[EAX]`; the safe branch assumes completed initialization.

Neither the consumer nor target writes **`BYTE[adapter+4]`** or calls adapter primary `+0xF0 → 0x0084FBC0`; no direct or transitive Draw* is demonstrated in the **specified two-function path**. Target **reads** adapter+4 and uses that byte to choose cache/dirty-queue synchronization vs underlying-device `SetRenderState`. This is a bounded negative conclusion and does not audit other setters or successors.

## 1. ABI and exact target implementation, 0x0084E750

**Stack ABI:** `[EBP+8]=adapter`, `[EBP+0xC]=renderStateID`, `[EBP+0x10]=value`; standard three-DWORD callee-cleanup via **`RET 0xC`** on **both** exits. Entry ECX/EDX are not this pointer/args. EBP is saved/restored; function allocates no local stack slots.

### `BYTE[adapter+4]!=0` — deferred/cached path

- `0x0084E75F`: ECX=`stateID`; `0x0084E762` **writes `DWORD[adapter+0xC+stateID*4]=value`**. This is desired render-state storage, **not** byte+4.
- `0x0084E766`: read `BYTE[adapter+0x9E4+stateID]`. If it is zero, branch `0x0084E76E → 0x0084E77A` enqueues the state. If nonzero, check `BYTE[adapter+0xAB6+stateID]` at `0x0084E770`: **zero → `0x0084E796` without enqueue; nonzero → enqueue**. Boolean condition for enqueue: `dirty1==0 OR dirty2!=0`.
- `0x0084E77A`: when queued, **write `BYTE[adapter+0x9E4+stateID]=1`**. `0x0084E782–0x0084E78F`: `i=DWORD[adapter+0xB88]`; **write `DWORD[adapter+0x69C+4*i]=stateID`**, then **increment `DWORD[adapter+0xB88]`**. There is no bounds check on `stateID` or pending count here.
- `0x0084E796`: **XOR EAX,EAX** guarantees full EAX=0 and `RET 0xC`, independent of whether enqueue occurred. No guest COM call in this path.

The independent state-sync helper previously classified `adapter+0x69C` as pending render-state IDs and `adapter+0x0C` as current state values; this target's exact write/read behavior supports that classification. No evidence that this setter updates the applied cache `adapter+0x354+4*stateID` (it does not write it). A subsequent state-sync routine may update that cache; do not assume a later call happened.

### `BYTE[adapter+4]==0` — immediate underlying-device path

- `0x0084E79C`: `device=DWORD[adapter+8]` (previously traced through retail `IDirect3D9::CreateDevice` and adapter initialization; **not** inferred from arbitrary +8).
- `0x0084E79F`: `vptr=DWORD[device]`.
- `0x0084E7A1–0x0084E7A7`: **push value, push renderStateID, push device**, load `F=DWORD[vptr+0xE4]`.
- `0x0084E7AD`: indirect device COM call with *two* explicit method parameters. This is **`IDirect3DDevice9::SetRenderState(D3DRENDERSTATETYPE, DWORD)`**, supported together by device creation provenance, standard D3D9 interface method ordering (slot index 57, byte offset 0xE4), **and actual argument count/order**. It is *not* classified by offset alone.
- `0x0084E7AF–0x0084E7B0`: `POP EBP; RET 0xC`; **EAX is unchanged after COM call**, so HRESULT or device-defined result is returned to the consumer without normalization and without checking success in this wrapper.

The target never writes +4 in either branch, invokes no `[adapter.vptr+0xF0]`, and invokes no D3D9 Draw* method.

## 2. Full consumer ABI, branches, register / value flow, return

**`0x0082E4A0`: ECX = wrapper; DL = branch selector; no explicit stack parameters; returns via `RET`**. `PUSH ESI; MOV ESI,ECX` preserves wrapper across getter and virtual callee. It modifies AL to indicate success/failure, but **does not necessarily normalize the high 24 bits of EAX**: `MOV AL,1` and `XOR AL,AL` affect *only AL*.

**Gates**, evaluated in order:
1. `0x0082E4A3–0x0082E4AA`: if `BYTE[wrapper+0x1350]==0`, go directly to **AL=1 return** at `0x0082E505`.
2. `0x0082E4AC–0x0082E4B3`: if `BYTE[0x00B8E200]==0`, likewise AL=1.
3. Only when **both flags nonzero**, `0x0082E4B5–0x0082E4B7`: `TEST DL,DL`; nonzero selects first branch, zero the second.

| Selector | Getter call | `stateID` source | `value` source | Full virtual call / result check |
|---|---|---|---|---|
| **DL != 0** | `0x0082E4B9` | `DWORD[wrapper+0x1354]` at `0x0082E4C7` | `DWORD[wrapper+0x135C]` at `0x0082E4BE` | `0x0082E4D5: CALL [adapter.vptr+0xE4]`; `0x0082E4D7: TEST EAX,EAX` |
| **DL == 0** | `0x0082E4DF` | `DWORD[wrapper+0x1358]` at `0x0082E4ED` | `DWORD[wrapper+0x1360]` at `0x0082E4E4` | `0x0082E4FB: CALL [adapter.vptr+0xE4]`; `0x0082E4FD: TEST EAX,EAX` |

**Both calls** place the arguments in the **same** underlying adapter ABI order: `PUSH value; PUSH stateID; PUSH adapter` (reverse stack order). The getter is invoked with ECX still wrapper (reached straight from `MOV ESI,ECX`, absent ECX clobber on the gate path). The getter's nonzero branch can return the fully initialized embedded adapter; consumers dereference `[EAX]` and use `vptr+0xE4` with **no null guard**.

**Boolean handling is exact EAX==0**, not signed HRESULT<0:
- if adapter method returns **EAX==0**, `JE 0x0082E505`, and consumer returns **AL=1**;
- if adapter method returns **EAX!=0** (negative HRESULT *or* any other nonzero result), consumer returns **AL=0**, at `0x0082E4DB–0x0082E4DE` or `0x0082E501–0x0082E504`.
- if either outer guard is false, consumer does **not** invoke getter/adapter; returns **AL=1**.
- The caller normalizes only the low byte AL; do not assert full EAX is always precisely 0 or 1 on every branch. Whether callers test AL or full EAX is outside this bounded scope.

**Immediate writes by `0x0082E4A0`:** none to `adapter+4`, +5, +0xB88 or render-state arrays. It reads wrapper fields, calls getter and target; target performs state-cache writes when enabled. No direct Draw* or BeginStateBlock call in the executable consumer body.

## 3. Proven pointer/vtable origin (not offset-only)

Constructor/initializer original PE confirms `0x00850109: DWORD[adapter]=0x00B1BBA8`, `0x0085010F: DWORD[adapter+8]=incomingDevice`, `0x00850176: BYTE[adapter+4]=0`. An ordinary wrapper device initialization at **0x008330B1–0x008330D0** sets `adapterPointer=wrapper+0x1F7C`, stores it to `[wrapper+0x478]`, and raises `BYTE[wrapper+0x5E8]=1`. The getter's original **0x0082E119: MOV EAX,[ECX+0x478]** returns precisely that pointer on the enabled path. This establishes **identity of the *constructed* adapter for the two target callsites**. The byte data at `0x00B1BC8C` then supplies the actual virtual target. Dynamically swapped pointer/vtable or inactive initialization are not asserted away.

The **device** virtual `+0xE4` inside `0x0084E750` is distinct from the **adapter** virtual `+0xE4` in `0x0082E4A0`; the first resolves to the D3D9 COM method *after* adapter wrapper dispatch. Likewise adapter `+0xF0` points to `0x0084FBC0` but **is not fetched anywhere in this bounded path**. The presence of a vtable entry is not an outgoing call.

## 4. PE facts vs runtime and inference

**Direct retail PE-byte facts:** exact SHA, DWORD `[0x00B1BC8C]=0x0084E750` (bytes `50 E7 84 00`); complete code/ABI of `0x0084E750` and `0x0082E4A0`, two branch conditions, field read/write offsets, pending-state enqueue policy, explicit stack args, return handling, and all reachable direct/indirect calls *within these two functions*. Previously verified retail initialization establishes standard object provenance.

**Classification inference supported by ABI:** COM call via the CreateDevice-produced device vptr+0xE4 is `IDirect3DDevice9::SetRenderState`, corroborated by two arguments and known D3D9 method ordering. `0x0084E750` implements immediate-or-deferred render-state setting, as directly supported by the cache and queue writes; this does not establish a later flush or frame rendering.

**Runtime observations from earlier user context only:** v757 captured 360 frames with zero selected Begin/End/forwarder/Draw events. **Neither `0x0082E4A0` nor `0x0084E750` is stated to be instrumented in that replay**, so no positive or negative runtime execution claim is made here. No replay was run now.

**Unknown / deliberately out of scope:** values of wrapper state IDs `+0x1354/+0x1358` in a real frame, whether gated consumer branch executed, whether `BYTE[adapter+4]` could later be set nonzero by other methods, bounds/capacity safety of state queue, any Draw* invocation outside the assigned two functions. No global adapter field-writer search, no gate forcing, and no changes to P1/P2 conditions.

## 5. One next evidence-backed target

**`0x0084E7C0`** — the immediately adjacent, **independently verified** adapter primary vtable `+0xE8` function (`[0x00B1BC90]=0x0084E7C0`). Its byte-visible logic tests the **same `BYTE[adapter+4]`**, returns a state value from the same `adapter+0xC+stateID*4` array on the cached branch, and delegates to `underlyingDevice.vptr+0xE8` otherwise (D3D9 GetRenderState-shaped). A bounded exact read/consumer analysis would establish whether readback is consistent with writes from this setter without reopening the global +4 writer audit.

## Appendix — complete original retail objdump blocks, with bytes

The blocks below are taken from the original PE/complete objdump and are **not** reconstituted pseudocode.

### A. Full vtable target `0x0084E750–0x0084E7B0` (29 decoded instruction lines, final RET spans 0x0084E7B0–0x0084E7B2)

```asm
  84e750:	55                   	push   ebp
  84e751:	8b ec                	mov    ebp,esp
  84e753:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84e756:	80 78 04 00          	cmp    BYTE PTR [eax+0x4],0x0
  84e75a:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84e75d:	74 3d                	je     0x84e79c
  84e75f:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  84e762:	89 54 88 0c          	mov    DWORD PTR [eax+ecx*4+0xc],edx
  84e766:	80 bc 01 e4 09 00 00 00 	cmp    BYTE PTR [ecx+eax*1+0x9e4],0x0
  84e76e:	74 0a                	je     0x84e77a
  84e770:	80 bc 01 b6 0a 00 00 00 	cmp    BYTE PTR [ecx+eax*1+0xab6],0x0
  84e778:	74 1c                	je     0x84e796
  84e77a:	c6 84 01 e4 09 00 00 01 	mov    BYTE PTR [ecx+eax*1+0x9e4],0x1
  84e782:	8b 90 88 0b 00 00    	mov    edx,DWORD PTR [eax+0xb88]
  84e788:	89 8c 90 9c 06 00 00 	mov    DWORD PTR [eax+edx*4+0x69c],ecx
  84e78f:	83 80 88 0b 00 00 01 	add    DWORD PTR [eax+0xb88],0x1
  84e796:	33 c0                	xor    eax,eax
  84e798:	5d                   	pop    ebp
  84e799:	c2 0c 00             	ret    0xc
  84e79c:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84e79f:	8b 08                	mov    ecx,DWORD PTR [eax]
  84e7a1:	52                   	push   edx
  84e7a2:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84e7a5:	52                   	push   edx
  84e7a6:	50                   	push   eax
  84e7a7:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  84e7ad:	ff d0                	call   eax
  84e7af:	5d                   	pop    ebp
  84e7b0:	c2 0c 00             	ret    0xc
```

### B. Full consumer `0x0082E4A0–0x0082E508` (39 decoded instruction lines)

```asm
  82e4a0:	56                   	push   esi
  82e4a1:	8b f1                	mov    esi,ecx
  82e4a3:	80 be 50 13 00 00 00 	cmp    BYTE PTR [esi+0x1350],0x0
  82e4aa:	74 59                	je     0x82e505
  82e4ac:	80 3d 00 e2 b8 00 00 	cmp    BYTE PTR ds:0xb8e200,0x0
  82e4b3:	74 50                	je     0x82e505
  82e4b5:	84 d2                	test   dl,dl
  82e4b7:	74 26                	je     0x82e4df
  82e4b9:	e8 52 fc ff ff       	call   0x82e110
  82e4be:	8b 96 5c 13 00 00    	mov    edx,DWORD PTR [esi+0x135c]
  82e4c4:	8b 08                	mov    ecx,DWORD PTR [eax]
  82e4c6:	52                   	push   edx
  82e4c7:	8b 96 54 13 00 00    	mov    edx,DWORD PTR [esi+0x1354]
  82e4cd:	52                   	push   edx
  82e4ce:	50                   	push   eax
  82e4cf:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  82e4d5:	ff d0                	call   eax
  82e4d7:	85 c0                	test   eax,eax
  82e4d9:	74 2a                	je     0x82e505
  82e4db:	32 c0                	xor    al,al
  82e4dd:	5e                   	pop    esi
  82e4de:	c3                   	ret
  82e4df:	e8 2c fc ff ff       	call   0x82e110
  82e4e4:	8b 96 60 13 00 00    	mov    edx,DWORD PTR [esi+0x1360]
  82e4ea:	8b 08                	mov    ecx,DWORD PTR [eax]
  82e4ec:	52                   	push   edx
  82e4ed:	8b 96 58 13 00 00    	mov    edx,DWORD PTR [esi+0x1358]
  82e4f3:	52                   	push   edx
  82e4f4:	50                   	push   eax
  82e4f5:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  82e4fb:	ff d0                	call   eax
  82e4fd:	85 c0                	test   eax,eax
  82e4ff:	74 04                	je     0x82e505
  82e501:	32 c0                	xor    al,al
  82e503:	5e                   	pop    esi
  82e504:	c3                   	ret
  82e505:	b0 01                	mov    al,0x1
  82e507:	5e                   	pop    esi
  82e508:	c3                   	ret
```

### C. Full getter `0x0082E110–0x0082E131` (10 decoded lines)

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

### D. Full adapter constructor `0x00850100–0x0085017E` (33 decoded lines)

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

### E. Original wrapper→embedded-adapter publication bytes (short, included solely as pointer-provenance anchor)

```asm
008330b1: 8d 86 7c 1f 00 00     lea eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov DWORD PTR [esi+0x478],eax
008330d0: c6 86 e8 05 00 00 01  mov BYTE PTR [esi+0x5e8],0x1
```
