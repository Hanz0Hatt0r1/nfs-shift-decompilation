# Process 1b — bounded candidate/list handler 0x0064EF60

**Date of analysis:** 2026-10-22, approximately 10:41–10:45 UTC. **Binary identity:** original Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. SHA-256 (supplied as locally verified for the retail PE): `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. **Source:** *only the complete original objdump provided with this assignment*; no new binary scan or runtime execution. The entire provided block, including instruction bytes, is reproduced in Appendix A.

**Exact range and length:** entry `0x0064EF60`, last instruction `RET 4` starts `0x0064F08A` and occupies `0x0064F08A–0x0064F08C`. End exclusive `0x0064F08D`; length **`0x12D = 301` bytes**. The analysis is deliberately bounded to this body and outgoing callee call/ABI boundaries. No global caller/writer sweep, no callee body review, and no source/runtime/P-code/renderer/guest-state modifications, replay, native Windows/Wine launch, rendered menu or race claims.

## 1. Established incoming ABI and return

The previously audited direct call at **`0x0064F303: CALL 0x0064EF60`** comes from `0x0064F270`. It is preceded by **`PUSH ESI`** at `0x0064F300` (where upstream ESI was the selected **candidate**), and **`MOV ECX,EDI`** at `0x0064F301` (where EDI was receiver **C**, originally the **old DWORD[O+0x38]**). Its return EIP is **`0x0064F308`**. It pushes **exactly one explicit DWORD argument**.

At entry:

| Machine input | Proven source | Used by body |
|---|---|---|
| **ECX** | **`C = old DWORD[O+0x38]`** in established upstream chain | `0x0064EF6A: MOV EBX,ECX`; EBX is persistent receiver field base |
| **`[EBP+8]`** | **candidate**, pushed at `0x0064F300` | `0x0064EF66: MOV ESI,[EBP+8]`; ESI is mutable current list-element pointer |
| **EDX** | Not freshly established before upstream direct call | The present body does **not** use original entry EDX as a proved independent input; later callees/loads overwrite it |
| **`[EBP+4]`** | Call-site return | **`0x0064F308`** |

The full prologue is `PUSH EBP; MOV EBP,ESP; PUSH ECX; PUSH EBX; PUSH ESI; MOV ESI,[EBP+8]; PUSH EDI; MOV EBX,ECX`. `PUSH ECX` reserves an EBP-relative DWORD local at **`[EBP-4]`**, which the routine subsequently writes as zero. This *is not* an explicit outgoing call argument. EBX, ESI and EDI are preserved/restored by the function.

There is **one normal exit**, after the potential merge/list-link work, with **`MOV EAX,ESI`** at `0x0064F083`, then `POP ESI; POP EBX; MOV ESP,EBP; POP EBP; RET 4` at `0x0064F085–0x0064F08A` (EDI was popped at `0x0064F082`). Thus the full returned **EAX is the final current ESI pointer** on this path, not a normalized Boolean or HRESULT; **`RET 4` cleans precisely the caller-pushed 4-byte candidate parameter**. No caller-side `ADD ESP,4` follows `0x0064F303`. The instruction `MOV EAX,ESI` explicitly establishes the normal return value even if nested calls changed EAX.

## 2. Exact branches and dataflow

Define **O** = original UI setup owner; **C=EBX** = old DWORD[O+0x38]; **N=ESI** = current candidate/list-element pointer; **P=EDI** = candidate neighbor selected by the current branch; **Q** = any read outgoing pointer or link. **C, N, P, O are *not interchangeable*.** A runtime alias is possible but no equality is proven from these PE instructions.

### 2.1 Loop head and optional outgoing registration-like calls

~~~asm
0064ef6c: c7 45 fc 00 00 00 00  mov    DWORD PTR [ebp-0x4],0x0
0064ef73: f6 83 10 01 00 00 02  test   BYTE PTR [ebx+0x110],0x2
0064ef7a: 74 23                 je     0x64ef9f
0064ef7c: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
0064ef7f: 8b 0d 20 89 b8 00     mov    ecx,DWORD PTR ds:0xb88920
0064ef85: 50                    push   eax
0064ef86: 51                    push   ecx
0064ef87: 32 c9                 xor    cl,cl
0064ef89: e8 92 7a 00 00        call   0x656a20
0064ef8e: 8b c8                 mov    ecx,eax
0064ef90: e8 ab 7b f3 ff        call   0x586b40
0064ef95: 8b 56 0c              mov    edx,DWORD PTR [esi+0xc]
0064ef98: 8b c8                 mov    ecx,eax
0064ef9a: e8 81 73 00 00        call   0x656320
~~~

The local DWORD is initialized zero once at `0x0064EF6C`, then the **loop head is `0x0064EF73`**. The flag **bit 1, mask 0x02, of BYTE[C+0x110]** controls three call boundaries; on zero, jump directly to neighbor testing at `0x0064EF9F`. On nonzero, read **DWORD[N+4]** and global **DWORD[0x00B88920]**, push those DWORDs in **N+4 then global** order, and execute calls described in Section 4. **`XOR CL,CL`** changes *only* the low eight bits of ECX: the outgoing ECX for the first call is the loaded global DWORD with **CL cleared**, **not necessarily whole ECX=0**. The two earlier PUSHes remain part of the caller's stack preparation until a callee/equivalent mechanism consumes them; the body itself contains no `ADD ESP,8`. Because two intermediate callees occur before `0x0064EF9A`, their uninspected stack behavior cannot be promoted to a source-language prototype.

### 2.2 Backward-like neighbor merge and loop backedge

At `0x0064EF9F` **`P=DWORD[N+0x18]`**; `ECX=0`; if **P==0** (`0x0064EFA6 JE`) or **BYTE[P+0x28] & 0x02 ==0** (`0x0064EFAC JE`), skip to forward neighbor selection `0x0064EFEF`.

If **P!=0 and its bit 0x02 is set**:
1. `PUSH P; ECX=C; CALL 0x0064EEF0` at `0x0064EFB1`, return **`0x0064EFB6`**. Its result is not checked.
2. **READ DWORD[N]**, then **READ/MODIFY/WRITE DWORD[P] += DWORD[N]** (`0x0064EFB6–0x0064EFB8`).
3. **READ DWORD[N+0x1C]**, write **DWORD[P+0x1C]** to that value (`0x0064EFBA–0x0064EFBF`). If nonzero, **WRITE DWORD[that_next+0x18]=P** (`0x0064EFC4`); otherwise **WRITE DWORD[C+0x10C]=P** (`0x0064EFC9`).
4. If **BYTE[N+0x28] & 0x20 != 0**, **READ DWORD[N+0x0C]**, write **DWORD[that_value−4]=0** (`0x0064EFD8`), then **READ/MODIFY/WRITE WORD[N+0x28] &= 0xFFDF** (`0x0064EFDF`), clearing bit 5.
5. **PUSH N; CALL 0x00657440** at `0x0064EFE6`, return **`0x0064EFEB`**, no caller ESP adjustment. At this call the full ECX is **not freshly set** after `0x0064EEF0` and thus unknown; do not assign ECX=C without callee proof.
6. **`MOV ESI,EDI`** at `0x0064EFEB` replaces current **N with P**, followed by **`JMP 0x0064EF73`** at `0x0064EFED` — the sole explicit **backedge**. The flag test and candidate logic may repeat. Exact iteration count/termination for arbitrary memory is not established; the user-supplied v791 replay does not document execution of this path.

The merge shape is **consistent with coalescing adjacent link records**, but this is a **structural inference**, not a verified C++ allocator type, destructor or resource ownership.

### 2.3 Forward-like neighbor merge

At `0x0064EFEF` load **`P=DWORD[N+0x1C]`**. If **P==0** or **BYTE[P+0x28] & 0x02==0**, `0x0064EFF4/FA` branch to `0x0064F023`, which sets **P=DWORD[EBP−4]=0**. If **P!=0 and bit 0x02 set**:
1. **PUSH P; ECX=C; CALL 0x0064EEF0** at `0x0064EFFF`, return **`0x0064F004`**.
2. READ **DWORD[P]**, and **READ/MODIFY/WRITE DWORD[N] += DWORD[P]** at `0x0064F004–0x0064F006`.
3. READ **DWORD[P+0x1C]**, **WRITE DWORD[N+0x1C]** with it at `0x0064F008–0x0064F00D`.
4. If that neighbor is nonzero, **WRITE DWORD[next+0x18]=N** (`0x0064F012`); otherwise **WRITE DWORD[C+0x10C]=N** (`0x0064F019`). Both paths explicitly set **ECX=0** before joining `0x0064F026`.
5. P remains the selected forward neighbor until final `0x0064F06F` test and possible `CALL 0x00657440`.

Neither merge path directly knows the original O base address. In particular, the **field N+0x14 used below is not O+0x14**.

### 2.4 Link insertion, count-like field and final flags

The list/link stage at `0x0064F026` reads **`H=DWORD[C+0x100]`** and compares with **ECX=0**.

- If **H!=0**: **WRITE DWORD[H+0x10]=N**; **WRITE DWORD[N+0x10]=0**; **WRITE DWORD[N+0x14]=H**. This links N to H through the observed field offsets.
- If **H==0**: **WRITE DWORD[N+0x10]=0**, **WRITE DWORD[N+0x14]=0**, and **WRITE DWORD[C+0x104]=N**.
- Both cases: **READ/MODIFY/WRITE DWORD[C+0xE8] += 1** at `0x0064F04D`; **WRITE DWORD[C+0x100]=N** at `0x0064F054`; READ **DWORD[N]**, then **READ/MODIFY/WRITE DWORD[C+0xEC] += DWORD[N]** at `0x0064F05C`.

Next **READ WORD[N+0x28]**, compute `(old WORD & 0xFFFB) | 0x0002` and **WRITE WORD[N+0x28]** at `0x0064F074`. This **clears bit 2 (0x04), sets bit 1 (0x02), and preserves unrelated bits**. Separately **WRITE DWORD[N+4]=0** at `0x0064F071`. These are 16-bit and 32-bit accesses respectively, not edits of an owner readiness bit.

If the forward selected **P!=0**, then **PUSH P; ECX=C; CALL 0x00657440** at `0x0064F07D` with return `0x0064F082`. Otherwise skip it. Finally POP EDI, **EAX=N**, restore nonvolatile state, **RET 4**.

The offsets `C+0x100`/`C+0x104`/`C+0x10C` and candidate ±list link fields are consistent with linked collection/bookkeeping; `DWORD[C+0xE8]` is a single increment per normal invocation, `DWORD[C+0xEC]` accumulates the candidate's leading DWORD. **Actual element-count invariants, object type, whether C is itself heap-owned, and object semantic meaning are not established**.

## 3. Exhaustive explicit memory effects (apart from ordinary PUSH/POP/CALL/RET stack accesses)

**C-relative accesses (C=EBX):**

| EIP | Operation and width | Branch/condition |
|---|---|---|
| `0x0064EF73` | READ BYTE[C+0x110], TEST mask 0x02 | At each loop iteration |
| `0x0064EFC9 / 0x0064F019` | WRITE DWORD[C+0x10C]=P or N | When merged element has no further link |
| `0x0064F026` | READ DWORD[C+0x100] | Final insertion stage |
| `0x0064F047` | WRITE DWORD[C+0x104]=N | Only if old C+0x100==0 |
| `0x0064F04D` | READ-MODIFY-WRITE DWORD[C+0xE8]+=1 | All normal insertion paths |
| `0x0064F054` | WRITE DWORD[C+0x100]=N | All normal insertion paths |
| `0x0064F05C` | READ-MODIFY-WRITE DWORD[C+0xEC]+=DWORD[N] | All normal insertion paths |

**Candidate/current-node N=ESI reads/writes** (ESI can change in the backward-merge loop):

| EIP | Operation and width |
|---|---|
| `0x0064EF7C` | READ DWORD[N+4] (conditional C flag) |
| `0x0064EF9F; 0x0064EFEF` | READ DWORD[N+0x18], DWORD[N+0x1C] |
| `0x0064EFB6; 0x0064F05A` | READ DWORD[N] |
| `0x0064EFBA; 0x0064EFD5; 0x0064F008` | READ DWORD[N+0x1C], DWORD[N+0xC] (when bit5), or WRITE DWORD[N+0x1C] (forward merge) |
| `0x0064EFCF` | READ BYTE[N+0x28], TEST 0x20 |
| `0x0064EFDF` | READ-MODIFY-WRITE WORD[N+0x28] &=0xFFDF when bit5 set |
| `0x0064F006` | READ-MODIFY-WRITE DWORD[N]+=DWORD[P] on forward merge |
| `0x0064F033/0x0064F041` | WRITE DWORD[N+0x10]=0 (both head branches) |
| `0x0064F03C/0x0064F044` | WRITE DWORD[N+0x14]=old H or 0 |
| `0x0064F071` | WRITE DWORD[N+4]=0 |
| `0x0064F062; 0x0064F074` | READ WORD[N+0x28], then WRITE WORD[N+0x28] with bit2 clear and bit1 set |

**Other directly accessed addresses:**

| EIP | Operation |
|---|---|
| `0x0064EF6C; 0x0064F023` | WRITE zero and later READ local DWORD[EBP−4] |
| `0x0064EF66` | READ incoming stack argument DWORD[EBP+8] |
| `0x0064EF7F` | READ global DWORD[0x00B88920] |
| `0x0064EFA8; 0x0064EFF6` | READ BYTE[P+0x28], TEST mask 0x02 |
| `0x0064EFB8` | READ-MODIFY-WRITE DWORD[P]+=DWORD[N] |
| `0x0064EFBF` | WRITE DWORD[P+0x1C]=DWORD[N+0x1C] |
| `0x0064EFC4; 0x0064F012` | WRITE DWORD[next+0x18]=P or N |
| `0x0064EFD8` | WRITE DWORD[DWORD[N+0xC]−4]=0 (bit5 condition) |
| `0x0064F004` | READ DWORD[P] |
| `0x0064F008` | READ DWORD[P+0x1C] |
| `0x0064F030` | WRITE DWORD[H+0x10]=N if H!=0 |
| `0x0064F05A` | READ DWORD[N], used for accumulator |

**Implicit stack memory:** the prologue saves EBP/EBX/ESI/EDI and reserves the one local DWORD with PUSH ECX; PUSH before direct calls writes argument DWORDs, CALL pushes return EIPs, POP/RET reads them. These are distinct from C/N/O field accesses. No directly evidenced write to owner O's vptr, O+0x14 or O+0x2D exists in this body. Possible address alias between O and C/N/P/H or nested callee effects is **unknown**.

## 4. Every direct outgoing call boundary (bodies intentionally not audited)

There are **7 direct CALL instructions** in this body. Return EIP is the next original instruction:

| Site → target | Return EIP | Proven immediately prepared register/stack state |
|---|---|---|
| `0x0064EF89 → 0x00656A20` | `0x0064EF8E` | ECX=(DWORD[0x00B88920] & 0xFFFFFF00), only CL zeroed; two earlier pushes: DWORD[N+4], global DWORD; EDX not newly established |
| `0x0064EF90 → 0x00586B40` | `0x0064EF95` | ECX=return EAX of 0x00656A20; no further PUSH; same prepared stack context |
| `0x0064EF9A → 0x00656320` | `0x0064EF9F` | ECX=return EAX of 0x00586B40, EDX=DWORD[N+0xC]; prepared args first=global DWORD, second=DWORD[N+4] if earlier callees preserve that stack layout |
| `0x0064EFB1 → 0x0064EEF0` | `0x0064EFB6` | ECX=C, one pushed argument P=DWORD[N+0x18] |
| `0x0064EFE6 → 0x00657440` | `0x0064EFEB` | one pushed argument N (current ESI); ECX not freshly restored after 0x0064EEF0 and hence not provably C; EDX was loaded from DWORD[N] before intervening local stores |
| `0x0064EFFF → 0x0064EEF0` | `0x0064F004` | ECX=C, one pushed argument P=DWORD[N+0x1C] |
| `0x0064F07D → 0x00657440` | `0x0064F082` | ECX=C freshly set; one pushed argument P (nonzero forward neighbor) |

The two calls to `0x0064EEF0` are distinct static sites but the **same callee**, each passed C and one eligible neighbor pointer. The two calls to `0x00657440` pass one current/selected node pointer in their stack argument, but the full ECX is demonstrably C only at the later site.

**Stack discipline:** this body has no local post-CALL `ADD ESP` instructions after these one-arg/two-arg outgoing preparations. For a normally balanced path, the callees must restore the appropriate stack position (often via callee cleanup), but **actual callee RET opcodes and semantic argument consumption are not proven here**. The intermediate calls between the pair of PUSHes and `0x0064EF9A` further limit certainty about exact callee stack layout, as noted above. No callee implementation is inferred from a name.

## 5. Evidence limits, readiness relevance and bounded interpretation

**Original objdump facts:** the function directly maintains **C-relative linked/container fields** `+0x100, +0x104, +0x10C, +0xE8, +0xEC`; selects and combines N/P using links `+0x18/+0x1C` and size-like DWORD[N]; writes N links `+0x10/+0x14`; conditionally zeros memory through N+0xC; clears/sets specific bits in **WORD[N+0x28]**. It contains a single backward branch from `0x0064EFED` to `0x0064EF73`, has seven direct callsites, normal returned **EAX=N**, and callee-cleaning **RET 4**. All these facts are original-PE instruction claims; semantic labels such as "linked container", "adjacent merge" and "size-like" are **inferences**, not verified source types.

**Object separation:** original owner O is **not supplied as a register receiver to this body**. C=old DWORD[O+0x38] is an independent pointer-sized value. **The C+0xE8 increment is not the original owner count at O+0x14**; the **N+0x14 link write is not O+0x14**; **N+0x28 flags are not O+0x2D readiness**. No direct original-owner vptr access/installation occurs. Unknown pointer aliasing or effects of `0x00656A20, 0x00586B40, 0x00656320, 0x0064EEF0` or `0x00657440` could touch other state, but no such effects are demonstrated by this function alone.

**Replay provenance:** the separately supplied v791 P-code guest observation reported original O+0x14=9 and writer `0x005092F0` clearing BYTE[O+0x2D]. No supplied v791 event establishes this cleanup chain or the present handler actually executed. This report **neither attributes the observed readiness byte clear to this handler nor proposes this handler as a fix**. No native Windows/Wine game launch, visible menu/race or original renderer reachability is claimed.

**Bounded conclusion:** this handler takes one candidate under C, conditionally coalesces linked neighbors, inserts the resulting pointer at the C+0x100-linked side, increments a C-relative counter and accumulator, and returns the resulting pointer. It **does not provide a direct byte-grounded producer for O+0x14 or O+0x2D**.

## 6. Exactly one next evidence-backed target

**`0x0064EEF0`** — the one direct helper used at **both** neighbor-merge sites `0x0064EFB1` and `0x0064EFFF`, each with **ECX=C** and **one pushed selected neighbor pointer P**, before the current function rewrites link/size fields. This is the strongest bounded next target because its direct effects could establish whether selected neighbors are detached from the very C-relative structure being rebuilt. Analyze **only this one helper's complete original PE function body and its immediate outgoing ABI boundaries** in a separate assignment; do not infer its effects now, expand to other callees, or run replay.

## Appendix A — complete supplied retail function 0x0064EF60–0x0064F08C

~~~asm
0064ef60: 55                    push   ebp
0064ef61: 8b ec                 mov    ebp,esp
0064ef63: 51                    push   ecx
0064ef64: 53                    push   ebx
0064ef65: 56                    push   esi
0064ef66: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0064ef69: 57                    push   edi
0064ef6a: 8b d9                 mov    ebx,ecx
0064ef6c: c7 45 fc 00 00 00 00  mov    DWORD PTR [ebp-0x4],0x0
0064ef73: f6 83 10 01 00 00 02  test   BYTE PTR [ebx+0x110],0x2
0064ef7a: 74 23                 je     0x64ef9f
0064ef7c: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
0064ef7f: 8b 0d 20 89 b8 00     mov    ecx,DWORD PTR ds:0xb88920
0064ef85: 50                    push   eax
0064ef86: 51                    push   ecx
0064ef87: 32 c9                 xor    cl,cl
0064ef89: e8 92 7a 00 00        call   0x656a20
0064ef8e: 8b c8                 mov    ecx,eax
0064ef90: e8 ab 7b f3 ff        call   0x586b40
0064ef95: 8b 56 0c              mov    edx,DWORD PTR [esi+0xc]
0064ef98: 8b c8                 mov    ecx,eax
0064ef9a: e8 81 73 00 00        call   0x656320
0064ef9f: 8b 7e 18              mov    edi,DWORD PTR [esi+0x18]
0064efa2: 33 c9                 xor    ecx,ecx
0064efa4: 3b f9                 cmp    edi,ecx
0064efa6: 74 47                 je     0x64efef
0064efa8: f6 47 28 02           test   BYTE PTR [edi+0x28],0x2
0064efac: 74 41                 je     0x64efef
0064efae: 57                    push   edi
0064efaf: 8b cb                 mov    ecx,ebx
0064efb1: e8 3a ff ff ff        call   0x64eef0
0064efb6: 8b 16                 mov    edx,DWORD PTR [esi]
0064efb8: 01 17                 add    DWORD PTR [edi],edx
0064efba: 8b 46 1c              mov    eax,DWORD PTR [esi+0x1c]
0064efbd: 85 c0                 test   eax,eax
0064efbf: 89 47 1c              mov    DWORD PTR [edi+0x1c],eax
0064efc2: 74 05                 je     0x64efc9
0064efc4: 89 78 18              mov    DWORD PTR [eax+0x18],edi
0064efc7: eb 06                 jmp    0x64efcf
0064efc9: 89 bb 0c 01 00 00     mov    DWORD PTR [ebx+0x10c],edi
0064efcf: f6 46 28 20           test   BYTE PTR [esi+0x28],0x20
0064efd3: 74 10                 je     0x64efe5
0064efd5: 8b 46 0c              mov    eax,DWORD PTR [esi+0xc]
0064efd8: c7 40 fc 00 00 00 00  mov    DWORD PTR [eax-0x4],0x0
0064efdf: 66 81 66 28 df ff     and    WORD PTR [esi+0x28],0xffdf
0064efe5: 56                    push   esi
0064efe6: e8 55 84 00 00        call   0x657440
0064efeb: 8b f7                 mov    esi,edi
0064efed: eb 84                 jmp    0x64ef73
0064efef: 8b 7e 1c              mov    edi,DWORD PTR [esi+0x1c]
0064eff2: 3b f9                 cmp    edi,ecx
0064eff4: 74 2d                 je     0x64f023
0064eff6: f6 47 28 02           test   BYTE PTR [edi+0x28],0x2
0064effa: 74 27                 je     0x64f023
0064effc: 57                    push   edi
0064effd: 8b cb                 mov    ecx,ebx
0064efff: e8 ec fe ff ff        call   0x64eef0
0064f004: 8b 0f                 mov    ecx,DWORD PTR [edi]
0064f006: 01 0e                 add    DWORD PTR [esi],ecx
0064f008: 8b 47 1c              mov    eax,DWORD PTR [edi+0x1c]
0064f00b: 85 c0                 test   eax,eax
0064f00d: 89 46 1c              mov    DWORD PTR [esi+0x1c],eax
0064f010: 74 07                 je     0x64f019
0064f012: 89 70 18              mov    DWORD PTR [eax+0x18],esi
0064f015: 33 c9                 xor    ecx,ecx
0064f017: eb 0d                 jmp    0x64f026
0064f019: 89 b3 0c 01 00 00     mov    DWORD PTR [ebx+0x10c],esi
0064f01f: 33 c9                 xor    ecx,ecx
0064f021: eb 03                 jmp    0x64f026
0064f023: 8b 7d fc              mov    edi,DWORD PTR [ebp-0x4]
0064f026: 8b 83 00 01 00 00     mov    eax,DWORD PTR [ebx+0x100]
0064f02c: 3b c1                 cmp    eax,ecx
0064f02e: 74 11                 je     0x64f041
0064f030: 89 70 10              mov    DWORD PTR [eax+0x10],esi
0064f033: 89 4e 10              mov    DWORD PTR [esi+0x10],ecx
0064f036: 8b 93 00 01 00 00     mov    edx,DWORD PTR [ebx+0x100]
0064f03c: 89 56 14              mov    DWORD PTR [esi+0x14],edx
0064f03f: eb 0c                 jmp    0x64f04d
0064f041: 89 4e 10              mov    DWORD PTR [esi+0x10],ecx
0064f044: 89 4e 14              mov    DWORD PTR [esi+0x14],ecx
0064f047: 89 b3 04 01 00 00     mov    DWORD PTR [ebx+0x104],esi
0064f04d: 83 83 e8 00 00 00 01  add    DWORD PTR [ebx+0xe8],0x1
0064f054: 89 b3 00 01 00 00     mov    DWORD PTR [ebx+0x100],esi
0064f05a: 8b 06                 mov    eax,DWORD PTR [esi]
0064f05c: 01 83 ec 00 00 00     add    DWORD PTR [ebx+0xec],eax
0064f062: 66 8b 56 28           mov    dx,WORD PTR [esi+0x28]
0064f066: 66 81 e2 fb ff        and    dx,0xfffb
0064f06b: 66 83 ca 02           or     dx,0x2
0064f06f: 3b f9                 cmp    edi,ecx
0064f071: 89 4e 04              mov    DWORD PTR [esi+0x4],ecx
0064f074: 66 89 56 28           mov    WORD PTR [esi+0x28],dx
0064f078: 74 08                 je     0x64f082
0064f07a: 57                    push   edi
0064f07b: 8b cb                 mov    ecx,ebx
0064f07d: e8 be 83 00 00        call   0x657440
0064f082: 5f                    pop    edi
0064f083: 8b c6                 mov    eax,esi
0064f085: 5e                    pop    esi
0064f086: 5b                    pop    ebx
0064f087: 8b e5                mov    esp,ebp
0064f089: 5d                    pop    ebp
0064f08a: c2 04 00              ret    0x4
~~~

**Report-only.** No source/runtime/P-code/renderer/guest-state changes, no new replay, no game-execution claims.
