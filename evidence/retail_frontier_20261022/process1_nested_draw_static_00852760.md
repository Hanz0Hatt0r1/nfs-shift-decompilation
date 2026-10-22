# Process 1 — retail nested render method 0x00852760 (bounded, v753)

**Date:** 2026-10-22. **Source image:** Need for Speed Shift PC retail 1.02, PE32 x86, ImageBase 0x00400000.  
**Original PE SHA-256 (verified from supplied SHIFT.exe):** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Evidence:** user's unabridged retail function block; original SHIFT.exe and SHIFT_objdump_full.txt, PE .rdata vtable DWORDs, PE d3d9.dll import names; supplied v753 controlled P-code replay summary. **No runtime run, P-code change, renderer implementation change or field forcing was performed.**

## Main finding: transitive DrawIndexedPrimitive is statically proven, execution in v753 is not

**0x00852760 itself does not contain a directly named D3D9 DrawPrimitive/DrawIndexedPrimitive/DrawUP import or direct draw command.** It conditionally calls three nested methods `0x00850F10`, `0x00851730`, `0x008521F0`. **These methods do contain executable calls through an adapter's +0x148 virtual slot** (e.g. `0x00851B5F`). The adapter pointer is not inferred from matching offsets: original constructor/initializer code explicitly creates the adapter at `wrapper+0x1F7C`, writes the adapter vptr `0x00B1BBA8`, and publishes its address in `wrapper+0x478`. PE .rdata gives `[0x00B1BBA8+0x148]=0x0084FD60`.

The **actual adapter implementation 0x0084FD60** forwards *all six DrawIndexedPrimitive parameters* through **`[underlyingDevice.vptr+0x148]`**. The underlying device pointer is the output of the device creation operation (IDirect3D9 `CreateDevice`-shaped call) and was stored in `adapter+8` by `0x0084E2C0`. The inner call is the D3D9 **IDirect3DDevice9::DrawIndexedPrimitive** COM-vtable slot (+0x148; index 82), as corroborated by the exact seven-DWORD stdcall shape and creation provenance, **not** solely a guessed meaning of an offset. This proves a *conditional executable retail route to a guest DrawIndexedPrimitive submission*. It **does not prove that any gate was satisfied or that a draw was attempted in v753**.

## ABI, entry effects and returns for 0x00852760

- **ECX = nested object** (ESI saved from ECX at 0x0085276B). **EDX = optional callback function pointer** (EBX saved at 0x00852772). **One stack DWORD `[EBP+8]` = callback context**; consumed by `RET 4`. The original wrapper caller `0x0054BEC2–0x0054BEC6` passes `EDX=0`, pushes stack DWORD 0, so the optional callback at 0x00852873 is **skipped** on this known static caller path.
- x86 fastcall-like/thiscall-like custom ECX+EDX+one-stack-argument ABI; do not invent a source-level C++ declaration. EBP, EBX, ESI and (on deep path) EDI are saved/restored.
- `0x00852766` pushes pointer `0x00B1C2A4`, `0x0085276D` pushes color `0xFFFF0000`, then `0x00852778` calls **0x00923628**. The PE IAT identifies `0x00923628: jmp [0x00AA65E4]` as **d3d9.dll!D3DPERF_BeginEvent**. All normal exits call `0x00923622: jmp [0x00AA65E0]` = **D3DPERF_EndEvent**; these are instrumentation markers, not Draw* commands.
- `0x00852774`: unconditionally writes BYTE `[this+9]=1` before the first guard, *including both short return paths*.
- `[this+0x98]==0` at 0x0085277D => EndEvent and **AL=1** at 0x0085278C, `RET 4` (successful no-work outcome; does **not** prove draw).
- Else `BYTE [this+6]==0` at 0x00852795 => EndEvent and **AL=0** at 0x008527A1, `RET 4`.
- Else (both guards pass): `BYTE [this+6]=0` at 0x008527AB, one-shot consumption of that flag, followed by resource/device/state/callback sequence. Failures share `0x008528D5–0x008528E2`: EndEvent, **AL=0**, `RET 4`; final non-negative HRESULT reaches `0x008528E5–0x008528F4`: EndEvent, **AL=1**, `RET 4`.
- **Return is a low-byte status**, not a reliable count of triangles/draws. Code writes AL (or carries high EAX bits from preceding call), and callers test AL. Flags `+6,+8,+9` and pointers `+0x54,+0x58,+0x98,+0x9C,+0xA8,+0xAC` are object state, resource handles/bindings by their uses; exact original field names are not established.

## Direct call inventory (exact addresses and use)

| Callsite(s) in 0x00852760 | Direct callee | Evidence-based role |
|---|---|---|
| 0x00852778 | **0x00923628** | Imported D3DPERF_BeginEvent |
| 0x00852786, 0x0085279B, 0x00852847, 0x00852857, 0x00852867, 0x008528D5, 0x008528E5 | **0x00923622** | Imported D3DPERF_EndEvent; mid-function EndEvent calls do not imply final return |
| 0x008527AF | 0x0082C050 | Singleton/resource cache initialization; detailed meaning requires callee |
| 0x008527B6 | 0x0082A660 | Receives ECX=EAX returned by 0x0082C050, result ignored |
| 0x008527BB | 0x0082C0B0 | Resource/state helper with no explicit input arguments |
| 0x008527C6, 0x0085287B, 0x008528BD | **0x0082E110** | ECX=wrapper `[0x00C26058]`; if BYTE [wrapper+0x5E8]!=0 returns `[wrapper+0x478]`, otherwise wrapper error callback and returns EAX=0 |
| 0x00852813 | 0x0082E510 | ECX=wrapper, EDX=[this+0xA8]; updates/compares wrapper `+0x70C` and delegates an interface setter |
| 0x0085283A | **0x00850F10** | Conditional nested setup/draw method; called only if `BYTE [this+8]==0`, AL checked |
| 0x0085284E | **0x00851730** | Nested setup/**DrawIndexedPrimitive-bearing** method, AL checked |
| 0x0085285E | **0x008521F0** | Nested setup/**DrawIndexedPrimitive-bearing** method, AL checked |
| 0x008528B2 | **0x00852FF0** | ECX=returned wrapper slot+0x100 object, EDX=0, stack `&[EBP-4]`; if index 0 exists, writes one DWORD from `[ECX+0x34]` indexed array to the local; AL ignored |

This is an exhaustive **direct rel32 CALL** inventory for assigned block. `0x00923622/28` are genuine PE import thunks, not direct D3D9 Draw imports.

## Exact indirect-call/dataflow inventory inside 0x00852760

1. **0x008527CD–0x008527D8:** EDI=device adapter from `0x0082E110`; `F=[EDI.vptr+0x9C]`; `push 0; push EDI; call F`. Signed EAX<0 jumps to error exit. Standard adapter class vptr `0x00B1BBA8` resolves slot +0x9C to **0x0084E680**, its depth-stencil binding adapter, not a Draw.
2. **0x008527E2–0x008527FD:** only when `[this+0x54]!=0`; `F=[EDI.vptr+0x88]`; args (from caller push order) `this+0x54, 0, this+0x58, 0, 0`, plus receiver EDI; signed failure check. Standard adapter slot +0x88 resolves to **0x00850010**. This is a blit/StretchRect-shaped operation, not direct Draw.
3. **0x00852818–0x00852828:** `F=[EDI.vptr+0x1A0]`; `push [this+0xAC]; push EDI; call F`; signed HRESULT failure check. Standard adapter slot +0x1A0 resolves to **0x0084EDB0** (index-buffer/SetIndices-shaped setter), not Draw.
4. **0x00852870–0x00852873:** if entry **EDX/EBX != 0**, `ECX=[EBP+8]`, `CALL EBX` (no explicit stack push). Dynamic callback target and side effects **unknown**. On the known upstream caller `0x0054BEC6` the argument EDX=0 makes it unreachable *for that entry*; no global claim about other callers.
5. **0x00852880–0x00852892:** EAX=device adapter returned by another `0x0082E110`; `F=[EAX.vptr+0x94]`; `push [this+0x9C]; push 0; push EAX; call F`; signed failure check. Standard adapter slot +0x94 = **0x0084E5A0** (SetRenderTarget-shaped).
6. **0x0085289E–0x008528AC:** `ECX=[0x00C26058]`; `F=[wrapper.vptr+0x100]`; `EDX=0`, `push &local[EBP-4]`, call F. For standard wrapper vptr `0x00B18D38` slot +0x100 points to **0x0082DAE0**; the returned pointer becomes ECX for `0x00852FF0`. This is a resource getter path, not by itself Draw.
7. **0x008528C2–0x008528CF:** another adapter via `0x0082E110`; `F=[adapter.vptr+0x9C]`; `push local[EBP-4]; push adapter; call F`. The original implementation `0x00852FF0` only writes local when index0 < count `[ECX+0x2C]`; its AL is not checked here. Signed EAX>=0 goes to success return. This is depth-stencil restore, not Draw.

**Important reliability detail:** `[EBP-4]` is not explicitly initialized in the assigned 0x00852760 prologue (`push ecx` reserves four bytes); if `0x00852FF0` returns false without writing that pointer, caller nonetheless passes its unchanged local to final adapter +0x9C. This is a byte-level observation; do not posit any particular runtime value or bug without a trace.

## DrawIndexedPrimitive proof: actual constructor→adapter→guest COM method, not offset inference

The guest's initial device/wrapper source is `[0x00C26058]`. This path needs the original wrapper's ordinary initialized state. All following are direct PE-byte relationships, not evidence they were executed in v753.

**Construction of the adapter and underlying D3D9 device identity:**

- `0x0083252A`: `LEA ECX,[wrapper+0x1F7C]`; `0x00832541`: `CALL 0x00850100`. In `0x00850109`, this initializer writes **DWORD [adapter]=0x00B1BBA8**.
- `0x0083304D–0x0083306C`: a Direct3D9 interface from `[wrapper+8]` is called through **vtable+0x40**, with the seven-pointer/argument stdcall shape of IDirect3D9::CreateDevice and output `EDI`. This establishes provenance of the created device pointer (not solely a guessed vtable name). After a successful creation, `0x00833095: mov edx,[edi]`; `0x00833097: lea ecx,[wrapper+0x1F7C]`; `0x0083309D: push edx`; `0x0083309E: call 0x0084E2C0`. At **0x0084E2DD**: `mov [adapter+8],eax` where EAX was the stack argument from `[EDI]`. Thus the adapter holds the underlying D3D9 device at **adapter+8**.
- `0x008330B1–0x008330B7`: wrapper receives **`[wrapper+0x478]=wrapper+0x1F7C`**; `0x008330D0` sets BYTE `[wrapper+0x5E8]=1`. `0x0082E110`, used by the 0x00852760 family, returns `[wrapper+0x478]` when that flag is nonzero. This is a concrete pointer identity chain, **not** an inference that every vtable +0x148 is a draw.

**A concrete draw call in a direct callee:**

```asm
0085174c: 8b 0d 58 60 c2 00     mov ecx,DWORD PTR ds:0xc26058
00851752: e8 b9 c9 fd ff        call 0x82e110
0085175c: 8b f8                 mov edi,eax
...                            ; guarded branches and other setup; no alternate write of EDI on continuing path
00851b4a: 8b 07                 mov eax,DWORD PTR [edi]
00851b4c: 8b 88 48 01 00 00     mov ecx,DWORD PTR [eax+0x148]
00851b52: 6a 02                 push 0x2
00851b54: 6a 00                 push 0x0
00851b56: 6a 04                 push 0x4
00851b58: 6a 00                 push 0x0
00851b5a: 6a 00                 push 0x0
00851b5c: 6a 04                 push 0x4
00851b5e: 57                    push edi
00851b5f: ff d1                 call ecx
```

The **known adapter primary vptr 0x00B1BBA8** at +0x148 resolves to the real PE function **0x0084FD60**, because `DWORD[0x00B1BCF0]=0x0084FD60`. In `0x0084FD60`, if adapter `BYTE +4` is nonzero it first calls `0x0084F000`, then unconditionally loads **EAX=[adapter+8] (underlying device)**, obtains its vptr, pushes the original six stack arguments, pushes EAX as COM receiver, and does **`CALL DWORD[underlyingDevice.vptr+0x148]` at 0x0084FD98**; `RET 0x1C`. By IDirect3DDevice9 interface ordering and the independently traced CreateDevice provenance, this final slot is **DrawIndexedPrimitive**. The arguments used in the concrete call are `PrimitiveType=4 (D3DPT_TRIANGLELIST)`, `BaseVertexIndex=0`, `MinVertexIndex=0`, `NumVertices=4`, `StartIndex=0`, `PrimitiveCount=2`: a two-triangle, indexed quad-shaped draw.

**Other exact callsite witnesses in direct callees:** `0x00850F10` includes `CALL [adapter.vptr+0x148]` at **0x0085129A**, **0x008514D9**, **0x008516F4**; `0x00851730` at **0x00851B5F**, **0x00851D9E**, **0x00851F9F**, **0x008521AF**; `0x008521F0` at **0x00852554**. Their individual reachability depends on each function's guards; the initial method 0x00852760 gates the calls to these routines. These are *static possible paths*, not observed v753 draws.

**Exact limits of the proof:** A conditional call chain *to the D3D9 COM DrawIndexedPrimitive slot* is established for correctly initialized retail objects. The original PE cannot prove what host-side import bridge/method implementation does with an actual call. The v753 trace of **0 events**, including the target 0x00852760, cannot establish runtime entry of any nested draw helper during that bounded replay.

## Runtime evidence v753 and confidence

User-supplied v753 P-code controlled replay: 360 host frames, host-frame-loop, no blocker, game-data v661, manifest v659; guest trace enabled, nontruncated, targeted `0x00852760` and DrawPrimitive, DrawIndexedPrimitive, DrawPrimitiveUP, DrawIndexedPrimitiveUP. **Trace event count=0**, `guest_draw_translation=false`, 360 clear and 360 present submissions. This means **neither the selected method entry nor any of the four selected Draw* guest targets was observed in that bounded run**. It is not proof of unreachable static code, nor causal proof that any particular gate prevents rendering. The earlier parent true-branch analysis does not establish entry to this nested method in v753.

**PE-byte confirmed:** all instructions and exit tests of assigned block; imported `D3DPERF_` names; direct callee list; strict callback register/stack contract; complete constructor→`wrapper+0x478`→adapter vtable→device pointer provenance; concrete `0x00851730` draw callsite; adapter proxy `0x0084FD60` forwarding to underlying device's DrawIndexedPrimitive COM method with matching argument count and values.

**Inference/uncertainty:** user-visible 2-triangle quad likely relates to rendering UI geometry, but its screen placement/ownership is not established. No claim of scene drawing, menus appearing, v753 dynamic success, or causal diagnosis of absent Draw*. Dynamic per-frame allocation, device reset/replacement and the deeper routines' other branches are outside this bounded analysis.

## Exactly one next bounded target

**0x0084FD60** — the **concrete adapter DrawIndexedPrimitive forwarding entry**. Read-only guest trace at this function's entry can record receiver (`adapter`), adapter vptr, `[adapter+8]` underlying device pointer, six stack arguments and caller EIP; any observed hit can then be compared with actual DrawIndexedPrimitive import events. Do **not** force upstream gates/flags or patch renderer code. If not observed, report the bounded negative result without declaring draw impossible.

## Full retail machine-code block: 0x00852760–0x008528F4

This is the entire supplied function, including its final three-byte `RET 4` instruction beginning at 0x008528F2 and ending at 0x008528F4. All bytes read from the complete retail objdump matched the user's supplied executable block.

```asm
852760:	55                   	push   ebp
  852761:	8b ec                	mov    ebp,esp
  852763:	51                   	push   ecx
  852764:	53                   	push   ebx
  852765:	56                   	push   esi
  852766:	68 a4 c2 b1 00       	push   0xb1c2a4
  85276b:	8b f1                	mov    esi,ecx
  85276d:	68 00 00 ff ff       	push   0xffff0000
  852772:	8b da                	mov    ebx,edx
  852774:	c6 46 09 01          	mov    BYTE PTR [esi+0x9],0x1
  852778:	e8 ab 0e 0d 00       	call   0x923628
  85277d:	83 be 98 00 00 00 00 	cmp    DWORD PTR [esi+0x98],0x0
  852784:	75 0f                	jne    0x852795
  852786:	e8 97 0e 0d 00       	call   0x923622
  85278b:	5e                   	pop    esi
  85278c:	b0 01                	mov    al,0x1
  85278e:	5b                   	pop    ebx
  85278f:	8b e5                	mov    esp,ebp
  852791:	5d                   	pop    ebp
  852792:	c2 04 00             	ret    0x4
  852795:	80 7e 06 00          	cmp    BYTE PTR [esi+0x6],0x0
  852799:	75 0f                	jne    0x8527aa
  85279b:	e8 82 0e 0d 00       	call   0x923622
  8527a0:	5e                   	pop    esi
  8527a1:	32 c0                	xor    al,al
  8527a3:	5b                   	pop    ebx
  8527a4:	8b e5                	mov    esp,ebp
  8527a6:	5d                   	pop    ebp
  8527a7:	c2 04 00             	ret    0x4
  8527aa:	57                   	push   edi
  8527ab:	c6 46 06 00          	mov    BYTE PTR [esi+0x6],0x0
  8527af:	e8 9c 98 fd ff       	call   0x82c050
  8527b4:	8b c8                	mov    ecx,eax
  8527b6:	e8 a5 7e fd ff       	call   0x82a660
  8527bb:	e8 f0 98 fd ff       	call   0x82c0b0
  8527c0:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8527c6:	e8 45 b9 fd ff       	call   0x82e110
  8527cb:	8b f8                	mov    edi,eax
  8527cd:	8b 07                	mov    eax,DWORD PTR [edi]
  8527cf:	8b 88 9c 00 00 00    	mov    ecx,DWORD PTR [eax+0x9c]
  8527d5:	6a 00                	push   0x0
  8527d7:	57                   	push   edi
  8527d8:	ff d1                	call   ecx
  8527da:	85 c0                	test   eax,eax
  8527dc:	0f 8c f3 00 00 00    	jl     0x8528d5
  8527e2:	8b 46 54             	mov    eax,DWORD PTR [esi+0x54]
  8527e5:	85 c0                	test   eax,eax
  8527e7:	74 1e                	je     0x852807
  8527e9:	8b 4e 58             	mov    ecx,DWORD PTR [esi+0x58]
  8527ec:	8b 17                	mov    edx,DWORD PTR [edi]
  8527ee:	8b 92 88 00 00 00    	mov    edx,DWORD PTR [edx+0x88]
  8527f4:	6a 00                	push   0x0
  8527f6:	6a 00                	push   0x0
  8527f8:	51                   	push   ecx
  8527f9:	6a 00                	push   0x0
  8527fb:	50                   	push   eax
  8527fc:	57                   	push   edi
  8527fd:	ff d2                	call   edx
  8527ff:	85 c0                	test   eax,eax
  852801:	0f 8c ce 00 00 00    	jl     0x8528d5
  852807:	8b 96 a8 00 00 00    	mov    edx,DWORD PTR [esi+0xa8]
  85280d:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  852813:	e8 f8 bc fd ff       	call   0x82e510
  852818:	8b 8e ac 00 00 00    	mov    ecx,DWORD PTR [esi+0xac]
  85281e:	8b 07                	mov    eax,DWORD PTR [edi]
  852820:	8b 90 a0 01 00 00    	mov    edx,DWORD PTR [eax+0x1a0]
  852826:	51                   	push   ecx
  852827:	57                   	push   edi
  852828:	ff d2                	call   edx
  85282a:	85 c0                	test   eax,eax
  85282c:	0f 8c a3 00 00 00    	jl     0x8528d5
  852832:	80 7e 08 00          	cmp    BYTE PTR [esi+0x8],0x0
  852836:	75 14                	jne    0x85284c
  852838:	8b ce                	mov    ecx,esi
  85283a:	e8 d1 e6 ff ff       	call   0x850f10
  85283f:	84 c0                	test   al,al
  852841:	0f 84 8e 00 00 00    	je     0x8528d5
  852847:	e8 d6 0d 0d 00       	call   0x923622
  85284c:	8b ce                	mov    ecx,esi
  85284e:	e8 dd ee ff ff       	call   0x851730
  852853:	84 c0                	test   al,al
  852855:	74 7e                	je     0x8528d5
  852857:	e8 c6 0d 0d 00       	call   0x923622
  85285c:	8b ce                	mov    ecx,esi
  85285e:	e8 8d f9 ff ff       	call   0x8521f0
  852863:	84 c0                	test   al,al
  852865:	74 6e                	je     0x8528d5
  852867:	e8 b6 0d 0d 00       	call   0x923622
  85286c:	85 db                	test   ebx,ebx
  85286e:	74 05                	je     0x852875
  852870:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  852873:	ff d3                	call   ebx
  852875:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85287b:	e8 90 b8 fd ff       	call   0x82e110
  852880:	8b 96 9c 00 00 00    	mov    edx,DWORD PTR [esi+0x9c]
  852886:	8b 08                	mov    ecx,DWORD PTR [eax]
  852888:	52                   	push   edx
  852889:	6a 00                	push   0x0
  85288b:	50                   	push   eax
  85288c:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  852892:	ff d0                	call   eax
  852894:	85 c0                	test   eax,eax
  852896:	7c 3d                	jl     0x8528d5
  852898:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85289e:	8b 01                	mov    eax,DWORD PTR [ecx]
  8528a0:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  8528a6:	8d 55 fc             	lea    edx,[ebp-0x4]
  8528a9:	52                   	push   edx
  8528aa:	33 d2                	xor    edx,edx
  8528ac:	ff d0                	call   eax
  8528ae:	33 d2                	xor    edx,edx
  8528b0:	8b c8                	mov    ecx,eax
  8528b2:	e8 39 07 00 00       	call   0x852ff0
  8528b7:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8528bd:	e8 4e b8 fd ff       	call   0x82e110
  8528c2:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  8528c5:	8b 08                	mov    ecx,DWORD PTR [eax]
  8528c7:	52                   	push   edx
  8528c8:	50                   	push   eax
  8528c9:	8b 81 9c 00 00 00    	mov    eax,DWORD PTR [ecx+0x9c]
  8528cf:	ff d0                	call   eax
  8528d1:	85 c0                	test   eax,eax
  8528d3:	7d 10                	jge    0x8528e5
  8528d5:	e8 48 0d 0d 00       	call   0x923622
  8528da:	5f                   	pop    edi
  8528db:	5e                   	pop    esi
  8528dc:	32 c0                	xor    al,al
  8528de:	5b                   	pop    ebx
  8528df:	8b e5                	mov    esp,ebp
  8528e1:	5d                   	pop    ebp
  8528e2:	c2 04 00             	ret    0x4
  8528e5:	e8 38 0d 0d 00       	call   0x923622
  8528ea:	5f                   	pop    edi
  8528eb:	5e                   	pop    esi
  8528ec:	b0 01                	mov    al,0x1
  8528ee:	5b                   	pop    ebx
  8528ef:	8b e5                	mov    esp,ebp
  8528f1:	5d                   	pop    ebp
  8528f2:	c2 04 00             	ret    0x4
```

## Supporting full forwarding function: 0x0084FD60–0x0084FD9E

```asm
84fd60:	55                   	push   ebp
  84fd61:	8b ec                	mov    ebp,esp
  84fd63:	56                   	push   esi
  84fd64:	8b 75 08             	mov    esi,DWORD PTR [ebp+0x8]
  84fd67:	80 7e 04 00          	cmp    BYTE PTR [esi+0x4],0x0
  84fd6b:	74 07                	je     0x84fd74
  84fd6d:	8b ce                	mov    ecx,esi
  84fd6f:	e8 8c f2 ff ff       	call   0x84f000
  84fd74:	8b 55 20             	mov    edx,DWORD PTR [ebp+0x20]
  84fd77:	8b 46 08             	mov    eax,DWORD PTR [esi+0x8]
  84fd7a:	8b 08                	mov    ecx,DWORD PTR [eax]
  84fd7c:	52                   	push   edx
  84fd7d:	8b 55 1c             	mov    edx,DWORD PTR [ebp+0x1c]
  84fd80:	52                   	push   edx
  84fd81:	8b 55 18             	mov    edx,DWORD PTR [ebp+0x18]
  84fd84:	52                   	push   edx
  84fd85:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84fd88:	52                   	push   edx
  84fd89:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84fd8c:	52                   	push   edx
  84fd8d:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84fd90:	52                   	push   edx
  84fd91:	50                   	push   eax
  84fd92:	8b 81 48 01 00 00    	mov    eax,DWORD PTR [ecx+0x148]
  84fd98:	ff d0                	call   eax
  84fd9a:	5e                   	pop    esi
  84fd9b:	5d                   	pop    ebp
  84fd9c:	c2 1c 00             	ret    0x1c
```

**Scope guard:** The auxiliary forwarding body was read verbatim from retail objdump as positive pointer/callflow evidence, without claiming to have exhaustively analyzed each other nested resource routine. The preceding assigned 0x00852760 block is unabridged.
