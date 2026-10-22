# Process 1b — bounded candidate handler 0x0064F270

**PE identity and scope.** Need for Speed SHIFT PC retail 1.02, original `SHIFT.exe` PE32 x86, ImageBase `0x00400000`; reference SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` (**identity supplied by assignment**, not a claim of a new executable hash check). Target function starts at `0x0064F270`; last instruction starts at `0x0064F33A`, its three bytes occupy `0x0064F33A–0x0064F33C`, end-exclusive `0x0064F33D`; total size **0xCD = 205 bytes**. Analysis date 2026-10-22, UTC, performed during **2026-10-22T10:32:40Z–2026-10-22T10:34:34.499Z**. Source is **only the user-provided complete original objdump block** reproduced in Appendix A. No other function bodies were decompiled or inspected.

**Hard boundary:** audit only this 205-byte function, its exact incoming values established by the previous bounded `0x0064F090` study, and immediate outgoing call boundaries. Do not infer source-language types from field names. No global caller/writer/vtable sweep; no source/runtime/P-code/renderer/guest-state changes, new replay, Windows/Wine launch, menu, race, or retail drawing claims.

## 1. ABI, receiver and entry values

The only previously established incoming chain is **original owner O** → cleanup whose old `DWORD[O+0x38]` becomes **C** → `0x0064F090` → direct `CALL 0x0064F270` at `0x0064F1CA`. Two separate call preparations converge on that callsite:

| Producer path in 0x0064F090 | Register receiver and first stack argument | Second stack argument |
|---|---|---|
| First lookup success via `0x0062E2C0`, record pointer `R` | **`ECX=C`**, first **`candidate=DWORD[R]`** | second **`R`** |
| Fallback success via `0x00657560` | **`ECX=C`**, first **`candidate=EAX`** returned by fallback | second **`0`** |

The parent call pushes two DWORD arguments and expects a return to **`0x0064F1CF`**. Here **C ≠ necessarily original owner O**; C was a *pointer-sized value* previously loaded from `DWORD[O+0x38]`. Nor should `candidate` be conflated with record `R`. The outgoing `EDX` register at `0x0064F1CA` is not freshly established by its immediate call preparation and **is not proven a required incoming input** for this body: before first potential use the body overwrites EDX.

**Full local ABI from original instructions:**

~~~asm
0064f270: 55                    push   ebp
0064f271: 8b ec                 mov    ebp,esp
0064f273: 56                    push   esi
0064f274: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0064f277: 57                    push   edi
0064f278: 8b f9                 mov    edi,ecx
~~~

Thus **`EDI=C=entry ECX`**, **`ESI=candidate=DWORD[EBP+8]`**, and `[EBP+0xC]` is the second stack argument (R/0). The first operand dereferenced from candidate is `DWORD[candidate+0x20]`. No explicit local stack allocation. Saves/restores EBP, ESI and EDI.

**Two normal returns**: `0x0064F28C: RET 8` on mismatch and `0x0064F33A: RET 8` on main path. Both clean **two 32-bit incoming stack arguments (8 bytes)**. Plain caller has no matching `ADD ESP,8` after `0x0064F1CA`. Full EAX return has no single fixed status: mismatch forwards the post-`0x0064F250` EAX, while the long path may retain different downstream values or the C+0x110 value loaded/modified at its end. The caller's immediate continuation at `0x0064F1CF` tests **BL**, not EAX, so it does **not interpret this function's EAX** as a proven status.

## 2. Exact branches and direct side effects

### 2.1 Candidate's stored receiver field

At `0x0064F27A`, load **`P=DWORD[candidate+0x20]`** into ECX, compare P with **C** at `0x0064F27D`. `JE 0x0064F28F` selects the long path if P==C.

- **P!=C:** read **`EDX=DWORD[candidate+0x0C]`** at `0x0064F281`. **ECX remains P**, so direct `CALL 0x0064F250` at `0x0064F284` gets **ECX=P, EDX=DWORD[candidate+0x0C]**, no new PUSH arguments, return EIP **`0x0064F289`**. It then directly restores registers and `RET 8` at `0x0064F28C`. **This wrapper's possible nested `0x0064F090` execution is an outgoing boundary, not audited here.** There are no direct C/candidate stores in this local mismatch branch.
- **P==C:** enter the longer path at `0x0064F28F`.

### 2.2 Calls before candidate update: CL-only normalization

At `0x0064F28F` the instruction is **`XOR CL,CL`**, *not XOR ECX,ECX*. On this branch ECX=P=C, so the first call to `0x00656A20` receives **ECX=C & 0xFFFFFF00**, not necessarily zero. This call's EAX goes into ECX for `CALL 0x00586B40`. Its EAX result is dereferenced at `0x0064F29D` as **`DWORD[EAX+0x60]`**, with a zero comparison and **no local pointer validity test**. If that DWORD is nonzero, a **second** `XOR CL,CL; CALL 0x00656A20` and `MOV ECX,EAX; CALL 0x00586B40` occur. Since external calls may clobber ECX, the second call's entire ECX upper bits are not pinned; only **CL=0** is byte-proven.

Then **`DWORD[candidate+4]`** is read, and the code pushes that DWORD followed by literal **`0xFA`**. These **two stack DWORDs remain pushed during calls to `0x00656A20` and `0x00586B40`**; they are evidently prepared for later direct `CALL 0x00457CC0`, but the intermediate calls do see the changed stack position. The third `XOR CL,CL` again sets **only CL=0**, not all of ECX. Next `MOV ECX,EAX` from the third `0x00656A20` for `0x00586B40`, then **`EDX=DWORD[candidate+0xC]`**, **`ECX=EAX`** from `0x00586B40` for `CALL 0x00457CC0` at `0x0064F2CD`. The outgoing two stack args in callee order are **first=0xFA, second=DWORD[candidate+4]**. No explicit caller ESP cleanup follows this call, so normal stack balance requires **callee cleanup/equivalent**; its actual RET opcode is not established from the given source.

### 2.3 Candidate registration and conditional reset of a separate selected pointer

At `0x0064F2D2`, **PUSH candidate**, set **ECX=C**, and **CALL 0x00637A20** at `0x0064F2D5` (one pushed stack arg, no immediate caller cleanup). This is an outgoing boundary: the callee's memory effects remain unknown.

Then `0x0064F2DA: TEST BYTE[candidate+0x28],0x20` controls a conditional state adjustment:
- **bit 5 clear:** `JE 0x0064F300`; skip the direct zero stores and bit clear.
- **bit 5 set:** load **`Q=DWORD[EBP+0xC]`**, i.e. the *second* original stack argument. If **Q!=0**, select **`T=Q=R`** from the first-found-record path. If **Q==0**, select **`T=DWORD[candidate+0x0C]-8`**, subtracting 8 from the **pointer-sized DWORD value**, not from candidate itself.
- Directly store **`DWORD[T+4]=0`** at `0x0064F2ED` and **`DWORD[T]=0`** at `0x0064F2F4`. These are memory writes to **T** (R or candidate-derived pointer), **not** directly to owner O or necessarily C. No null or alias validation appears in this block.
- **`AND WORD PTR [candidate+0x28],0xFFDF`** at `0x0064F2FA` is a **16-bit read–modify–write** clearing bit 5 (0x20), preserving other bits of that word. It should not be described as an unconditional whole-byte reset.

The main path next **PUSH candidate; ECX=C; CALL 0x0064EF60** at `0x0064F303`, with one explicit pushed argument; no caller ESP fixup is present. This callee is out of scope. Then **CALL 0x006476C0** at `0x0064F308`, with no new pushed args or ECX reload after the preceding call. **Its ECX is therefore not statically fixed to C** — prior callee may have changed volatile ECX. Only the helper's returned **AL** is tested.

### 2.4 Conditional C+0x110 flag write

On `AL==0` from `0x006476C0`, branch `JE 0x0064F337` skips the final C field update. Otherwise:
1. **READ DWORD[C+0x110]** into EAX at `0x0064F311`.
2. If **EAX & 0x200 != 0**, `JNE 0x0064F337`, skip change.
3. Read **DWORD[C+0xD4]** into ECX and compare unsigned to **DWORD[C+0xE0]** at `0x0064F324`. If **C+0xD4 > C+0xE0 unsigned**, `JA 0x0064F337` skips update.
4. Otherwise set bit 8 **`EAX |= 0x100`** at `0x0064F32C` and **WRITE DWORD[C+0x110]=EAX** at `0x0064F331`. Other bits of that DWORD are preserved by the bitwise OR (assuming no concurrent mutation).
5. End with register restores and **RET 8** at `0x0064F33A`.

It is *not* an unconditional flag write, and the function does not establish the source-language name or meaning of C+0x110.

## 3. Exhaustive direct memory ledger

| Address base and offset | Exact instruction(s) | Width/access and conditions |
|---|---|---|
| **candidate+0x20** | `0x0064F27A` | READ DWORD; P compared with C |
| **candidate+0x0C** | `0x0064F281, 0x0064F2C8, 0x0064F2E7` | READ DWORD on mismatch/long-path/conditional fallback |
| **candidate+0x04** | `0x0064F2B1` | READ DWORD, forwarded as pushed argument |
| **candidate+0x28** | `0x0064F2DA` | READ BYTE, test bit 0x20 |
| **candidate+0x28** | `0x0064F2FA` | READ–MODIFY–WRITE WORD with 0xFFDF on bit-set path |
| **C+0x110** | `0x0064F311; 0x0064F331` | READ DWORD then conditional WRITE DWORD with bit 0x100 set |
| **C+0xD4, C+0xE0** | `0x0064F31E; 0x0064F324` | READ DWORD each, unsigned comparison |
| **EAX-result+0x60** | `0x0064F29D` | READ DWORD from return pointer of first `0x00586B40`; conditional second pair of calls |
| **T+0x04, T+0x00** | `0x0064F2ED; 0x0064F2F4` | WRITE DWORD 0 each, only candidate bit 0x20 set; T=second stack arg if nonzero, else `DWORD[candidate+0xC]-8` |
| **[EBP+0x08]**, **[EBP+0x0C]** | `0x0064F274; 0x0064F2E0` | READ DWORD incoming stack args |
| **machine stack** | PUSH/CALL/POP/RET | Implicit writes/reads return addresses and outgoing args, normal prologue/epilogue |

The candidate-derived T may coincide with other object regions, and an incoming record R could alias C or O; **those alias facts are not established**. The only direct **C-relative store** is `DWORD[C+0x110]`. The only direct candidate-relative **write** is the WORD bit-clear at `candidate+0x28`. The two T-relative DWORD stores are conditional and must not be silently relabeled as O-relative writes.

## 4. All immediate call boundaries, ABI where directly proven

No callee body is inspected, and semantic effects/return types are **unknown**. "No new stack args" means no immediately prepared PUSH for that method; previous pushes may still be on the stack.

| CALL address → target | Next/return EIP | Incoming register and stack facts |
|---|---|---|
| `0x0064F284 → 0x0064F250` | `0x0064F289` | **ECX=P=DWORD[candidate+0x20]**, **EDX=DWORD[candidate+0xC]**, no new pushed args; mismatch only |
| `0x0064F291 → 0x00656A20` | `0x0064F296` | ECX=`C&0xFFFFFF00`, CL=0, no new pushed args |
| `0x0064F298 → 0x00586B40` | `0x0064F29D` | ECX=EAX(`0x00656A20` return); no new pushed args |
| `0x0064F2A5 → 0x00656A20` | `0x0064F2AA` | CL=0, other ECX bits unknown after previous callees; no new pushed args; conditional on DWORD[prior EAX+0x60]!=0 |
| `0x0064F2AC → 0x00586B40` | `0x0064F2B1` | ECX=EAX(`0x00656A20` return), no new pushed args |
| `0x0064F2BC → 0x00656A20` | `0x0064F2C1` | CL=0, upper ECX bits unknown; two earlier pushed DWORDs remain on stack |
| `0x0064F2C3 → 0x00586B40` | `0x0064F2C8` | ECX=EAX(`0x00656A20` return); two earlier pushed DWORDs remain |
| `0x0064F2CD → 0x00457CC0` | `0x0064F2D2` | ECX=EAX(`0x00586B40`), EDX=DWORD[candidate+0xC]; pushed stack args first **0xFA**, second **DWORD[candidate+4]**; no local ADD ESP |
| `0x0064F2D5 → 0x00637A20` | `0x0064F2DA` | ECX=C, 1 pushed arg **candidate**; no local ADD ESP |
| `0x0064F303 → 0x0064EF60` | `0x0064F308` | ECX=C, 1 pushed arg **candidate**; no local ADD ESP |
| `0x0064F308 → 0x006476C0` | `0x0064F30D` | **ECX not freshly established** after `0x0064EF60`; no new pushed args; AL tested after return |

On ordinary well-balanced return from calls with pushed arguments and no caller correction, effective callee-side stack cleanup (or equivalent stack balancing) is required. **The exact callee RET instructions are not verified.** Although the calls to `0x00656A20` and `0x00586B40` between two PUSHes and `0x00457CC0` have no new explicit pushes of their own, they do execute while those already-pushed argument DWORDs are resident on the stack; the register/stack ABI should not be made more specific from these bytes alone.

## 5. Evidence boundaries and significance for readiness

**Original PE facts from supplied objdump:** both RET 8 exits; C/candidate/R distinction; comparisons and conditional branches; conditional zero writes via T; candidate word bit clear; conditional C+0x110 OR 0x100; eleven direct CALL instructions and their return addresses. No direct instruction addresses original owner O. No opcode directly reads or writes **DWORD[O+0x14]**, **BYTE[O+0x2D]**, or **DWORD[O]** (owner vptr). In particular, ***C+0x110 is not O+0x110*** without a proved alias; similarly, candidate+0x28 is not the owner readiness byte O+0x2D.

**Prior user-supplied finite P-code guest observation:** owner count 9 and direct readiness-byte clear in separate writer `0x005092F0`, not a run performed here. This material does not establish this candidate handler executed, altered owner state through an alias, set a positive readiness byte, or caused progress to stop. Any nested function may have unobserved effects; no claim that callees are pure, no claim they clear/set readiness, and no live-game rendering/menu/race assertion.

**Bounded conclusion:** for matching candidate and C, this function forwards a candidate to two other handlers, conditionally invalidates T-relative fields and clears candidate flag 0x20, then may set a separate bit in C+0x110. For mismatching candidate/C, it forwards two candidate-derived register values to `0x0064F250` and returns. These are well-founded local state-management operations but do **not themselves explain or repair O+0x14 or O+0x2D**.

## 6. Exactly one next evidence-backed target

**`0x0064EF60`**, the direct candidate-handling callee at **`0x0064F303`**, invoked on the long branch immediately after candidate flag/selected-pointer state updates, with **ECX=C** and **one pushed stack argument = candidate**, return EIP **`0x0064F308`**. It is the closest single call boundary for understanding what happens to candidate immediately before the final C+0x110 bit check. A separate bounded static audit can determine this callee's direct effects and cleanup, without global sweeps or replay. **This is the sole proposed next address; its body was not analyzed here.**

## Appendix A — complete supplied retail objdump, 205 bytes (original bytes unchanged)

~~~asm
0064f270: 55                    push   ebp
0064f271: 8b ec                 mov    ebp,esp
0064f273: 56                    push   esi
0064f274: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0064f277: 57                    push   edi
0064f278: 8b f9                 mov    edi,ecx
0064f27a: 8b 4e 20              mov    ecx,DWORD PTR [esi+0x20]
0064f27d: 3b cf                 cmp    ecx,edi
0064f27f: 74 0e                 je     0x64f28f
0064f281: 8b 56 0c              mov    edx,DWORD PTR [esi+0xc]
0064f284: e8 c7 ff ff ff        call   0x64f250
0064f289: 5f                    pop    edi
0064f28a: 5e                    pop    esi
0064f28b: 5d                    pop    ebp
0064f28c: c2 08 00              ret    0x8
0064f28f: 32 c9                 xor    cl,cl
0064f291: e8 8a 77 00 00        call   0x656a20
0064f296: 8b c8                 mov    ecx,eax
0064f298: e8 a3 78 f3 ff        call   0x586b40
0064f29d: 83 78 60 00          cmp    DWORD PTR [eax+0x60],0x0
0064f2a1: 74 0e                 je     0x64f2b1
0064f2a3: 32 c9                 xor    cl,cl
0064f2a5: e8 76 77 00 00        call   0x656a20
0064f2aa: 8b c8                 mov    ecx,eax
0064f2ac: e8 8f 78 f3 ff        call   0x586b40
0064f2b1: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
0064f2b4: 50                    push   eax
0064f2b5: 68 fa 00 00 00        push   0xfa
0064f2ba: 32 c9                 xor    cl,cl
0064f2bc: e8 5f 77 00 00        call   0x656a20
0064f2c1: 8b c8                 mov    ecx,eax
0064f2c3: e8 78 78 f3 ff        call   0x586b40
0064f2c8: 8b 56 0c              mov    edx,DWORD PTR [esi+0xc]
0064f2cb: 8b c8                 mov    ecx,eax
0064f2cd: e8 ee 89 e0 ff        call   0x457cc0
0064f2d2: 56                    push   esi
0064f2d3: 8b cf                 mov    ecx,edi
0064f2d5: e8 46 87 fe ff        call   0x637a20
0064f2da: f6 46 28 20           test   BYTE PTR [esi+0x28],0x20
0064f2de: 74 20                 je     0x64f300
0064f2e0: 8b 45 0c              mov    eax,DWORD PTR [ebp+0xc]
0064f2e3: 85 c0                 test   eax,eax
0064f2e5: 75 06                 jne    0x64f2ed
0064f2e7: 8b 46 0c              mov    eax,DWORD PTR [esi+0xc]
0064f2ea: 83 e8 08              sub    eax,0x8
0064f2ed: c7 40 04 00 00 00 00  mov    DWORD PTR [eax+0x4],0x0
0064f2f4: c7 00 00 00 00 00     mov    DWORD PTR [eax],0x0
0064f2fa: 66 81 66 28 df ff     and    WORD PTR [esi+0x28],0xffdf
0064f300: 56                    push   esi
0064f301: 8b cf                 mov    ecx,edi
0064f303: e8 58 fc ff ff        call   0x64ef60
0064f308: e8 b3 83 ff ff        call   0x6476c0
0064f30d: 84 c0                 test   al,al
0064f30f: 74 26                 je     0x64f337
0064f311: 8b 87 10 01 00 00     mov    eax,DWORD PTR [edi+0x110]
0064f317: a9 00 02 00 00        test   eax,0x200
0064f31c: 75 19                 jne    0x64f337
0064f31e: 8b 8f d4 00 00 00     mov    ecx,DWORD PTR [edi+0xd4]
0064f324: 3b 8f e0 00 00 00     cmp    ecx,DWORD PTR [edi+0xe0]
0064f32a: 77 0b                 ja     0x64f337
0064f32c: 0d 00 01 00 00        or     eax,0x100
0064f331: 89 87 10 01 00 00     mov    DWORD PTR [edi+0x110],eax
0064f337: 5f                    pop    edi
0064f338: 5e                    pop    esi
0064f339: 5d                    pop    ebp
0064f33a: c2 08 00              ret    0x8
~~~

**Report-only publication on `work/process-reports`. No source/runtime/P-code/renderer/guest-state changes or replay.**
