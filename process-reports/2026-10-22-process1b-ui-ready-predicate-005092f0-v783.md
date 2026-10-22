# Process 1b — bounded UI-worker readiness write at 0x005092F0 and direct helper 0x00508860 (retail + v783)

**Date:** 2026-10-22. **Source binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`. **SHA-256 independently verified against `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Both complete instruction blocks were compared with GNU `objdump -D -M intel -w` output on the original PE. This report contains **no code edit, runtime/P-code edit, renderer/guest-state work, forced guest-state, replay or game execution**.

**Exactly bounded scope:** full writer `0x005092F0–0x0050939E`, its **directly called** helper `0x00508860–0x00508882` and existing user-supplied *controlled-replay v783 provenance*. Other direct outgoing calls are identified only as dispatch boundaries; their bodies, unrelated consumers and all global writers/callers are **not analyzed**. Prior adapter +0x118 task remains stopped and is not resumed. The report draws no inference about actual menu/race rendering.

## 1. Main finding

The retail writer `0x005092F0` takes its **original object in incoming ECX** and copies it into EDI (`0x005092F6`). It first calls a predicate/helper `0x00554050` with **ECX=originalObject+8** (`LEA EBX,[EDI+8]` and `MOV ECX,EBX`). At `0x00509302`, **only the returned low byte AL is tested**:

- If **AL is nonzero**, `0x00509304: JE` is **not** taken. The function returns `EAX=0` through `0x00509306–0x0050930D`. **No readiness-byte write is reached**.
- If **AL is zero**, `JE 0x0050930E` is taken. At **`0x00509314: C6 47 2D 00 — MOV BYTE PTR [EDI+0x2D],0`**, the writer **unconditionally clears `BYTE[originalObject+0x2D]`** before its list/iterator traversal. This is the only instruction in the *entire writer* that directly stores the readiness byte.
- There is **no instruction in writer `0x005092F0–0x0050939E` that writes `BYTE[originalObject+0x2D]=1`**. Its normal completion sets **a different field `DWORD[originalObject+0x28]=1`** (`0x00509371`). An alternative branch tests `BYTE[originalObject+0xAC]` and ultimately returns `EAX=1`. Neither instruction is evidence of setting readiness `+0x2D` to one.

**Precise causal bound:** the observed *writer's own* zero store can occur only after `0x00554050` returned `AL==0`. The independently supplied v783 provenance saying the last recorded write to `ECX+0x2D` was this `0` store supports that this branch ran for the recorded object/event. It does **not** establish why the earlier predicate returned zero, whether all other possible writers were absent globally, whether `+0x2D` was ever nonzero, or why progress stopped at 30.

## 2. Writer ABI, entry registers, stack, branches and returns

**ABI from original bytes:**

- **Incoming ECX = `O` (original UI-worker object/receiver)**. `0x005092F6: MOV EDI,ECX` preserves this pointer in EDI across downstream calls, assuming standard callee-saved ABI. The original `EDX` value is **not read as an input argument**; EDX is later populated with a local address, then O, then constant 1 for other calls. No `[EBP+8]` or higher input argument is read by this writer; there is **no byte-proven explicit stack parameter**.
- Prologue `PUSH EBP; MOV EBP,ESP; PUSH ECX; PUSH EBX; PUSH EDI`. `PUSH ECX` reserves one 4-byte local at `[EBP-4]`, and the code later passes its **address**, `EDX=&[EBP-4]`, to list-cursor helpers; the initial value saved by `PUSH ECX` is not itself consumed as an input.
- `EBX=O+8` identifies the embedded list/container-like field *by use shape*, not a fully proven C++ type. `EBX` and `EDI` are callee-saved; ESI is additionally saved after the readiness-byte write and restored on either corresponding exit.
- The writer has plain **`RET`**, not `RET N`, on all three exits: `0x0050930D`, `0x0050937F`, `0x0050939E`. `MOV ESP,EBP; POP EBP; RET` releases the one local DWORD and restores the call frame. The writer has no stack-argument cleanup count.
- Return `EAX=0` on (a) predicate-true early exit and (b) normal post-traversal completion, after `DWORD[O+0x28]=1`. Return `EAX=1` on the `BYTE[O+0xAC]!=0` branch, following an indirect virtual call on an object returned by `0x0040B870`. These are **literal integers**, not evidence of HRESULT or of the boolean meaning of UI readiness. No other return value is exposed by this function.

### 2.1 Guard and early return (0x005092F0–0x0050930D)

1. `EDI=O`, `EBX=O+8`.
2. `0x005092FB: ECX=EBX`; `0x005092FD: CALL 0x00554050`.
3. `0x00509302: TEST AL,AL`; `0x00509304: JE 0x0050930E`.
4. If `AL!=0`, `POP EDI; XOR EAX,EAX; POP EBX; MOV ESP,EBP; POP EBP; RET`. The byte at `O+0x2D` is **not touched** in this branch.

The call to `0x00554050` itself is a proven dispatch, but its *body/semantic predicate* is **not** analyzed in this report. The guard's **returned AL value** alone determines whether writer executes the clear.

### 2.2 Clear and list traversal (0x0050930E–0x0050936F)

The zero-AL path begins with `PUSH ESI` and then prepares `EDX=&local`, `ECX=O+8`; the `MOV BYTE PTR [O+0x2D],0` happens **before `CALL 0x0067DB80`**, not after the iteration. The list/cursor-looking calls and exact pointer tests are:

- `0x00509318: CALL 0x0067DB80` with `ECX=O+8`, `EDX=&[EBP-4]`; subsequently **`ESI=DWORD[EAX]`** at `0x0050931D`.
- `0x00509324: CALL 0x004F5EB0` with the same incoming ECX/EDX shape; at `0x00509329`, compare **`ESI`** to **`DWORD[EAX]`**, set `AL=(ESI!=DWORD[EAX])`, test it, and jump to tail processing if equal.
- On unequal-pointer entry at **`0x00509332`**, load **`ECX=DWORD[ESI+0x0C]`** (a separate item/list-associated object) and **`EDX=O`**, then make the **direct `CALL 0x00508860`** at **`0x00509337`**. This call is separately audited in section 3.
- Immediately afterward, **`0x0050933C: CMP BYTE PTR [O+0xAC],0`**; if **nonzero**, branch to special exit `0x00509380`.
- Otherwise **`EAX=DWORD[ESI+4]`**. If nonzero, replace ESI with EAX; if zero, ESI is left as-is. Repeat `CALL 0x004F5EB0` with `ECX=O+8`, `EDX=&local`; compare ESI with `DWORD[EAX]` and jump back to `0x00509332` while different.
- Once either comparison gives equality, at `0x00509361` call **`0x0067DB80`** again with `ECX=O+8`, `EDX=&local`; read `EAX=DWORD[EAX]`, then `ECX=DWORD[EAX+0x0C]`; call **`0x005088A0`** at `0x0050936B`. The outgoing call is **not** analyzed here. Next the writer restores ESI, explicitly **writes `DWORD[O+0x28]=1`** at `0x00509371`, returns `EAX=0`.

Do **not** infer an exact C++ container class or guarantee of iteration progress from a pointer-chain shape. The external list-cursor method results/side effects are unknown. Notably, neither condition that terminates this bounded loop sets `BYTE[O+0x2D]` to one *within the writer*.

### 2.3 Special exit when originalObject+0xAC is nonzero

After helper `0x00508860`, the writer compares `BYTE[O+0xAC]` with zero. If nonzero:
- `0x00509380: CALL 0x0040B870`, then `ESI=DWORD[EAX]`, `ECX=EAX` and `EAX=DWORD[ESI+0x44]`.
- `0x0050938C: MOV EDX,1`; `0x00509391: CALL EAX`. **ECX is the newly returned object's pointer**, not the original writer O; EDX is exactly 1. The indirect target/implementation and its effects are unresolved.
- `POP ESI; POP EDI; MOV EAX,1; POP EBX; MOV ESP,EBP; POP EBP; RET`. Therefore **returns 1 explicitly regardless of the indirect call's EAX**. This exit does not set `DWORD[O+0x28]=1` or `BYTE[O+0x2D]=1` in its own instructions.

## 3. Direct helper 0x00508860: complete ABI, pointer provenance and writes

**Call site:** writer `0x00509332–0x00509337`:

~~~asm
00509332: 8b 4e 0c              mov    ecx,DWORD PTR [esi+0xc] ; L = [node+0xC]
00509335: 8b d7                 mov    edx,edi                 ; O = writer receiver
00509337: e8 24 f5 ff ff        call   0x508860
~~~

This proves the helper's exact incoming register values **on this call path**: **ECX=L=DWORD[listNode+0xC]**, **EDX=O=originalObject**. There is **no explicit pushed stack argument**. The helper has a plain `RET`.

In the helper:
1. `PUSH ESI; MOV ESI,ECX` — save ESI and retain object L.
2. `EAX=DWORD[L]` — read L's vptr/dispatch table pointer.
3. **`0x00508865: MOV DWORD[L+0xE8],EDX`**, i.e. store **O** into a field of **L**, *not* into `O+0x2D`.
4. `EDX=DWORD[DWORD[L]+4]` (`0x0050886B`), **`CALL EDX`** at `0x0050886E`. **ECX still equals L**, so this is a register-receiver virtual call **L.vptr+4** with no explicit stack arguments prepared by this helper; the ABI/semantics of the actual dynamic target cannot be determined from the offset alone.
5. `TEST EAX,EAX`; if **EAX!=0**, jump directly to restore ESI and `RET`.
6. If **EAX==0**, **`0x00508874: MOV DWORD[L+0xE4],EAX`** stores **0**, and **`0x0050887A: MOV BYTE[L+0xEC],1`** stores **1**. Then restore ESI; `RET`.
7. **Return EAX unchanged** from that indirect call (zero on the two-extra-write path, nonzero on the skip path); no local remapping or HRESULT meaning is provable. Calling this status bool/HRESULT without the virtual callee body would be an inference.

**Critical separation:** these are writes relative to **L**, the list-associated object. **None is addressed as `BYTE[O+0x2D]`.** The fact that helper writes **`BYTE[L+0xEC]=1`** when its virtual method returns zero is **not evidence** of a readiness-byte `1` write to `O+0x2D`. The writer explicitly passes O into `L+0xE8`, showing two distinct **roles** (source worker pointer and list-associated object pointer), but PE bytes alone do **not formally guarantee their storage never overlaps**. If arbitrary invalid/offset-alias pointer values were supplied, writes could theoretically overlap O's storage. No such alias is evidenced by the v783 data or these two functions. This report states **no *direct or proven aliasing* helper write to O+0x2D**, not a universal no-alias assertion.

Do not identify `L.vptr+4` as `IUnknown::AddRef` merely because of its slot offset. The receiver is a list object with unknown dynamic type, not the already-proven D3D9 device. Virtual-call target EIP, reference count, allocation, scheduling and downstream effects are unresolved.

## 4. Evidence ledger and v783 causality boundary

### 4.1 Original retail PE bytes — independently verified

- Both original complete target blocks in Appendices A/B are SHA-verified PE source, not decompiled pseudocode.
- Writer's only direct `O+0x2D` store: **`0x00509314: BYTE[O+0x2D]=0`**, only when predicate `AL==0`.
- Writer's normal post-traversal store: **`DWORD[O+0x28]=1`**. Special branch read **`BYTE[O+0xAC]`**, not a write. No positive `O+0x2D` setter exists in either complete block.
- Helper's three possible fields: always **`DWORD[L+0xE8]=O`**; additionally if its virtual call returns EAX==0, **`DWORD[L+0xE4]=0`** and **`BYTE[L+0xEC]=1`**. The virtual method is called with register **ECX=L**, no stack arguments pushed locally.
- Writer returns 0/0/1 on the guard/normal/special paths. Helper returns its virtual method's EAX, with no explicit 0/1 conversion.
- The actual runtime values of original O's pointers and helper L, except as supplied in user trace, are not encoded in the static PE.

### 4.2 Supplied v783 controlled-replay observation — not independently reproduced

**Provenance as stated by the user** (no replay performed here): **360 frames, exit code 0, Vulkan validation errors 0**. At `0x0054BB20`, `DWORD[param+0x1F04]=0`; progress reached **30**. Child `0x00508EA0` returned 0 **1010 times**; `0x00508E90` returned 0 **1010 times**; `0x00508EC0` was **not invoked**. For **ECX=0x27DFA5FC**, the byte **`BYTE[ECX+0x2D]=0`**, and its most recent provenance write was **one byte 0 from writer `0x005092F0`**, **dispatch 461058**, **caller 0x0054B8B0**, **return 0x0054BAC8**, **thread 0x00175C45**.

**Narrow supported joint conclusion:** given the recorded provenance store attributed to this writer and the byte-accurate instruction `0x00509314`, that observed zero is explained as a **writer-imposed reset**. For the reset instruction to have executed in this function, the initial predicate's returned **AL had to be zero** on that traversal. Writer-local code contains **no later positive readiness-byte write**; helper-local code writes to a *different pointer base* L. Therefore the observed `O+0x2D=0` is consistent with a reset that remained the latest tracked write in v783.

**What neither source proves:** the meaning of `+0x2D` as an official readiness state (the term is observational); why the initial predicate was zero; whether the UI worker's lack of readiness *caused* progress=30 or the two child functions' zero returns; whether `0x00508EC0` would have run after different states; whether any function **elsewhere** writes O+0x2D=1; whether menu/race was reached; real Draw* or GPU activity. The supplied v783 trace describes **a selected finite replay**, not universal execution/nonexecution in other runs.

### 4.3 Interpretive categories

- **Direct PE facts:** exact tests/jumps, offsets, writes, argument/register passing and returns above.
- **Grounded structural inference:** O+8 is container-like because it is supplied to cursor-style helpers; L is list-associated because the node's +0xC field supplies it. Neither object has a proven public C++ type or ownership contract from this bounded region.
- **Runtime observation (user supplied):** v783 values/frames and last-write attribution, as given; not recomputed or claimed as a newly executed game.
- **Unresolved:** full predicate semantics, independent readiness-setter provenance, downstream list/virtual method effects, object aliasing, causality of progress plateau.

## 5. Exactly one next evidence-backed target

**`0x00554050`**, the writer's **direct predicate** at `0x005092FD`. The original caller passes **`ECX=O+8`**, then tests the returned **AL**; its value **precisely determines whether `BYTE[O+0x2D]` is reset to zero** or not. A separate *single-target bounded* PE audit of `0x00554050` and its input predicate field/value is the strongest next step to identify the immediate gating condition, **without** global scans of callers or writers. Its body is **not analyzed as part of this assignment**. **No second next target is proposed.**

## Appendix A — full original retail writer 0x005092F0–0x0050939E

~~~asm
005092f0: 55                    push   ebp
005092f1: 8b ec                 mov    ebp,esp
005092f3: 51                    push   ecx
005092f4: 53                    push   ebx
005092f5: 57                    push   edi
005092f6: 8b f9                 mov    edi,ecx
005092f8: 8d 5f 08              lea    ebx,[edi+0x8]
005092fb: 8b cb                 mov    ecx,ebx
005092fd: e8 4e ad 04 00        call   0x554050
00509302: 84 c0                 test   al,al
00509304: 74 08                 je     0x50930e
00509306: 5f                    pop    edi
00509307: 33 c0                 xor    eax,eax
00509309: 5b                    pop    ebx
0050930a: 8b e5                 mov    esp,ebp
0050930c: 5d                    pop    ebp
0050930d: c3                    ret
0050930e: 56                    push   esi
0050930f: 8d 55 fc              lea    edx,[ebp-0x4]
00509312: 8b cb                 mov    ecx,ebx
00509314: c6 47 2d 00           mov    BYTE PTR [edi+0x2d],0x0
00509318: e8 63 48 17 00        call   0x67db80
0050931d: 8b 30                 mov    esi,DWORD PTR [eax]
0050931f: 8d 55 fc              lea    edx,[ebp-0x4]
00509322: 8b cb                 mov    ecx,ebx
00509324: e8 87 cb fe ff        call   0x4f5eb0
00509329: 3b 30                 cmp    esi,DWORD PTR [eax]
0050932b: 0f 95 c0              setne  al
0050932e: 84 c0                 test   al,al
00509330: 74 2a                 je     0x50935c
00509332: 8b 4e 0c              mov    ecx,DWORD PTR [esi+0xc]
00509335: 8b d7                 mov    edx,edi
00509337: e8 24 f5 ff ff        call   0x508860
0050933c: 80 bf ac 00 00 00 00  cmp    BYTE PTR [edi+0xac],0x0
00509343: 75 3b                 jne    0x509380
00509345: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
00509348: 85 c0                 test   eax,eax
0050934a: 74 02                 je     0x50934e
0050934c: 8b f0                 mov    esi,eax
0050934e: 8d 55 fc              lea    edx,[ebp-0x4]
00509351: 8b cb                 mov    ecx,ebx
00509353: e8 58 cb fe ff        call   0x4f5eb0
00509358: 3b 30                 cmp    esi,DWORD PTR [eax]
0050935a: 75 d6                 jne    0x509332
0050935c: 8d 55 fc              lea    edx,[ebp-0x4]
0050935f: 8b cb                 mov    ecx,ebx
00509361: e8 1a 48 17 00        call   0x67db80
00509366: 8b 00                 mov    eax,DWORD PTR [eax]
00509368: 8b 48 0c              mov    ecx,DWORD PTR [eax+0xc]
0050936b: e8 30 f5 ff ff        call   0x5088a0
00509370: 5e                    pop    esi
00509371: c7 47 28 01 00 00 00  mov    DWORD PTR [edi+0x28],0x1
00509378: 5f                    pop    edi
00509379: 33 c0                 xor    eax,eax
0050937b: 5b                    pop    ebx
0050937c: 8b e5                 mov    esp,ebp
0050937e: 5d                    pop    ebp
0050937f: c3                    ret
00509380: e8 eb 24 f0 ff        call   0x40b870
00509385: 8b 30                 mov    esi,DWORD PTR [eax]
00509387: 8b c8                 mov    ecx,eax
00509389: 8b 46 44              mov    eax,DWORD PTR [esi+0x44]
0050938c: ba 01 00 00 00        mov    edx,0x1
00509391: ff d0                 call   eax
00509393: 5e                    pop    esi
00509394: 5f                    pop    edi
00509395: b8 01 00 00 00        mov    eax,0x1
0050939a: 5b                    pop    ebx
0050939b: 8b e5                 mov    esp,ebp
0050939d: 5d                    pop    ebp
0050939e: c3                    ret
~~~

## Appendix B — full original retail helper 0x00508860–0x00508882

~~~asm
00508860: 56                    push   esi
00508861: 8b f1                 mov    esi,ecx
00508863: 8b 06                 mov    eax,DWORD PTR [esi]
00508865: 89 96 e8 00 00 00     mov    DWORD PTR [esi+0xe8],edx
0050886b: 8b 50 04              mov    edx,DWORD PTR [eax+0x4]
0050886e: ff d2                 call   edx
00508870: 85 c0                 test   eax,eax
00508872: 75 0d                 jne    0x508881
00508874: 89 86 e4 00 00 00     mov    DWORD PTR [esi+0xe4],eax
0050887a: c6 86 ec 00 00 00 01  mov    BYTE PTR [esi+0xec],0x1
00508881: 5e                    pop    esi
00508882: c3                    ret
~~~

**Publication intent:** commit only this new Markdown report to branch `work/process-reports`. No edits to executables, source, runtime, guest state, P-code or renderer.
