# Process 1b — bounded status producer 0x0065EC50 (original retail PE)

**Date / bounded analysis window:** 2026-10-22, 2026-10-22T11:08:00Z–2026-10-22T11:10:53.226Z UTC. **Executable:** Need for Speed SHIFT PC retail 1.02, original `SHIFT.exe` PE32 x86, ImageBase `0x00400000`; independently checked local SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**. The target was checked using original PE bytes and GNU `objdump -D -Mintel -w --start-address=0x0065ec50 --stop-address=0x0065ec96 /mnt/data/SHIFT.exe`. The full byte-for-byte function is provided in Appendix A. There were **no new guest replays**.

**Exact boundary correction:** the task's stated “68 bytes, end-exclusive `0x0065EC94`” is inconsistent with its own final `0x0065EC93: C2 04 00 / RET 4`, which occupies **three bytes**. Original PE confirms first instruction at `0x0065EC50`, last instruction starts at `0x0065EC93`, **last byte `0x0065EC95`**, **end-exclusive `0x0065EC96`**, total **`0x46 = 70 bytes`**, **33 instructions**. The supplied instruction bytes are otherwise identical to original retail disassembly. No padding or later function is counted.

**Strict scope:** entire `0x0065EC50` function and its three immediate CALL boundaries only. No global writer/caller search, no investigation of callee bodies, no source/runtime/P-code/renderer/guest-state modifications, no native launch or menu/race claims. Prior v790/v791 observations are kept separate from static PE.

## 1. Incoming ABI from known immediate caller 0x00634F50

Previously established original call path: item status callback `0x00508C70` → `0x00634F50` → **`0x00634F6A: CALL 0x0065EC50`**, with return EIP **`0x00634F6F`**. The prior body establishes:

- **I** = callback item receiver; original owner **O** is a different pointer, sometimes read earlier from `DWORD[I+0xE8]`.
- **Q=DWORD[I+0x0C]`**, first passed as ECX into `0x00634F50` and preserved in EDI there; this is the value later dereferenced by the parent into outgoing ECX for `0x0065EC50`. **For this actual call boundary, Q is the DWORD read at `[Q]` at `0x00634F65`**, not necessarily still the same numeric pointer originally passed as Q to the parent. To avoid ambiguity call **T=DWORD[Q]` at the parent** and distinguish it from the **parent's pointer Q**. 
- **S=I+0x120**, kept in ESI by `0x00634F50` and passed as EDX to this function.
- **`[EBP+8]=5`**, its sole explicit newly pushed DWORD, pushed at parent `0x00634F67` after the parent reads the memory field `T=DWORD[Q]`.

**Exact incoming register reality:** parent `0x00634F65: MOV ECX,DWORD[EDI]` (where EDI is previously saved Q) sets **ECX=T=DWORD[Q]**; `0x00634F68: MOV EDX,ESI` sets **EDX=S=I+0x120**; `0x00634F67: PUSH EAX` forwards the original stack arg 5. Thus the stated higher-level summary “ECX=Q=DWORD[I+0xC]” describes the parent input Q, **but not the exact ECX delivered to `0x0065EC50`**, which is **`T=DWORD[Q]`**. The present report uses **T** for the actual incoming ECX and **Q** for the parent pointer. This distinction is byte-proven and matters for the outgoing call register masks.

| Machine component at entry `0x0065EC50` | Value and provenance |
|---|---|
| **ECX** | **`T=DWORD[Q]`**, after prior `0x00636FB0` call has returned; `Q=DWORD[I+0x0C]` in parent |
| **EDX** | **`S=I+0x120`** |
| **[EBP+8]** | **DWORD value 5** |
| **[EBP+4]** | Return EIP **`0x00634F6F`**, pushed by CALL |
| EAX initially | Unspecified by this caller boundary; this function uses subsequent callee EAX, and the zero branch explicitly assigns 6 |

The target starts with `PUSH EBP; MOV EBP,ESP; PUSH EBX; PUSH ESI; MOV ESI,EDX; ...; PUSH EDI; ...; MOV EBX,ECX`. Hence **ESI=S**, **EBX=T**, **EDI=S+0x34** on both paths. The code saves/restores EBX/ESI/EDI and EBP. This is a register-plus-one-stack-DWORD calling pattern, not a verified source-level method signature.

**Two normal exits**, both **`RET 4`**:
- Early zero-field return at `0x0065EC6C`, **EAX=6**.
- Downstream result return at `0x0065EC93`, **EAX=last callee result**.
Both **callee-clean exactly one original incoming DWORD (4 bytes)**. The caller `0x00634F50` does not execute `ADD ESP,4` after the call. `RET 4` also removes the CPU return address normally.

## 2. Exact branches, register dataflow and EAX result

The entire instruction body, including all three direct calls, is reproduced without omissions in Appendix A. There is **one conditional branch**, **no loop** and **no object-field writes**.

### 2.1 First guard — direct return EAX=6

~~~asm
0065ec55: 8b f2                 mov    esi,edx
0065ec57: 83 7e 34 00           cmp    DWORD PTR [esi+0x34],0x0
0065ec5b: 57                    push   edi
0065ec5c: 8d 7e 34              lea    edi,[esi+0x34]
0065ec5f: 8b d9                 mov    ebx,ecx
0065ec61: 75 0c                 jne    0x65ec6f
0065ec63: 5f                    pop    edi
0065ec64: 5e                    pop    esi
0065ec65: b8 06 00 00 00        mov    eax,0x6
0065ec6a: 5b                    pop    ebx
0065ec6b: 5d                    pop    ebp
0065ec6c: c2 04 00              ret    0x4
~~~

**Only condition: `DWORD[S+0x34] != 0`**, read from **`DWORD[I+0x154]`** for the proven S=I+0x120. The PUSH, LEA and MOV between CMP and JNE **do not modify EFLAGS**, so JNE is based solely on this direct memory comparison.

If **`DWORD[S+0x34]==0`**, the helper **does not issue any CALL**, pops its saved registers, sets full **EAX=6** and `RET 4`. Consequently, when the outer callback `0x00508C70` subsequently converts nonzero EAX to status 1, **this zero-field path yields status 1**, never status 5. This is not a store of 6 into item state; the eventual item status field `I+0xE4` is written only by the separate outer wrapper `0x005088A0`.

The **`LEA EDI,[ESI+0x34]`** computes a pointer **`P=S+0x34=I+0x154`** without reading or writing the corresponding DWORD. No direct read from `DWORD[T]` or `DWORD[Q]` occurs in this body.

### 2.2 Nonzero-field path — 3-call straight-line chain

If `DWORD[S+0x34]!=0`, the function:

~~~asm
0065ec6f: 32 d2                 xor    dl,dl
0065ec71: 32 c9                 xor    cl,cl
0065ec73: e8 b8 e0 ff ff        call   0x65cd30
0065ec78: 8b d7                 mov    edx,edi
0065ec7a: 8b c8                 mov    ecx,eax
0065ec7c: e8 5f d4 ff ff        call   0x65c0e0
0065ec81: 8b 4d 08              mov    ecx,DWORD PTR [ebp+0x8]
0065ec84: 51                    push   ecx
0065ec85: 56                    push   esi
0065ec86: 8b d3                 mov    edx,ebx
0065ec88: 8b c8                 mov    ecx,eax
0065ec8a: e8 d1 0d 00 00        call   0x65fa60
0065ec8f: 5f                    pop    edi
0065ec90: 5e                    pop    esi
0065ec91: 5b                    pop    ebx
0065ec92: 5d                    pop    ebp
0065ec93: c2 04 00              ret    0x4
~~~

- `XOR DL,DL` clears **only low byte of EDX**, not entire EDX. Since **EDX=S**, the first call receives **`EDX=S & 0xFFFFFF00`**.
- `XOR CL,CL` clears **only low byte of ECX**, not entire ECX. Since **ECX=T=DWORD[Q]**, first call receives **`ECX=T & 0xFFFFFF00`**. Neither register is proven 0; no meaning is assigned to this masking.
- The full **EAX returned by `0x0065CD30`** is copied into **ECX** for `0x0065C0E0`; this function does not read the EAX as a pointer or status directly.
- **EDX=P=S+0x34** is supplied to `0x0065C0E0`; `LEA` derived P from the field address. The **EAX returned by `0x0065C0E0`** is copied into **ECX** for `0x0065FA60`.
- Read incoming stack DWORD **`[EBP+8]=5`**, **PUSH 5**, **PUSH S** (in that order), **EDX=T** (restored from EBX), **ECX=EAX from `0x0065C0E0`**, then direct `CALL 0x0065FA60`.
- There is **no TEST/CMP/branch based on returned EAX** from any of these three calls inside this helper. `0x0065FA60`'s returned EAX passes through POP EDI, POP ESI, POP EBX, POP EBP and `RET 4` **unchanged**.

Thus **the complete EAX return relationship** is:

~~~text
if DWORD[S+0x34] == 0:
    result = 6
else:
    A = call 0x0065CD30(ECX=T & 0xFFFFFF00,
                       EDX=S & 0xFFFFFF00)
    B = call 0x0065C0E0(ECX=A, EDX=S+0x34)
    result = call 0x0065FA60(ECX=B, EDX=T,
                             stack first=S, stack second=5)
return result   // RET 4 consumes this function's one incoming stack DWORD
~~~

This is a **machine-register flow sketch**, not reconstructed game source or a claim about the direct callees' typed parameters and internal memory effects.

## 3. Every immediate outgoing CALL boundary (no callee bodies inspected)

| Site → direct target | Return EIP | Exact provable outgoing state |
|---|---|---|
| **`0x0065EC73 → 0x0065CD30`** | **`0x0065EC78`** | **ECX=`T&0xFFFFFF00`**, **EDX=`S&0xFFFFFF00`**; **zero newly pushed stack arguments** |
| **`0x0065EC7C → 0x0065C0E0`** | **`0x0065EC81`** | **ECX=EAX returned from `0x0065CD30`**, **EDX=S+0x34**, **zero newly pushed stack arguments** |
| **`0x0065EC8A → 0x0065FA60`** | **`0x0065EC8F`** | **ECX=EAX returned from `0x0065C0E0`**, **EDX=T=DWORD[Q]**, **two explicit outgoing stack args, first=S=I+0x120, second=5**; the 5 was pushed first, then S |

**Outgoing stack detail:** the two `PUSH` instructions for `0x0065FA60` are `PUSH 5` at `0x0065EC84` and `PUSH S` at `0x0065EC85`. At second-callee entry, the CPU-pushed return address `0x0065EC8F` sits at `[ESP]`, the **first** explicit argument S at `[ESP+4]`, and the **second** explicit argument 5 at `[ESP+8]`. There is **no local `ADD ESP,8` or pair of POPs for these two arguments** after the call. Thus normal stack-balanced return requires `0x0065FA60` to consume those two DWORDs (or equivalent balancing); **the actual RET opcode and semantics of `0x0065FA60` are unknown**. This differs from the verified **RET 4** in the present function, which cleans its *own caller's* single DWORD.

The first two callees have no newly pushed args; no cleanup opcode or return-type inference is made from this alone. Any callee may access arbitrary memory reachable from its register/stack inputs, but **none has been decompiled, followed or run** here.

## 4. Exhaustive direct memory reads/writes in complete body

**Explicit non-stack memory access: one READ, zero WRITEs.**

| EIP | Direct access | Meaning actually proven |
|---|---|---|
| **`0x0065EC57`** | **READ DWORD[ESI+0x34]** for CMP with immediate zero | Guard **`DWORD[S+0x34]=DWORD[I+0x154]`**; **no load/store of this DWORD otherwise** |

**Explicit stack memory access:** `0x0065EC81: MOV ECX,DWORD[EBP+8]` reads the one incoming DWORD **5**, only in the nonzero-field path. `PUSH EBP, EBX, ESI, EDI` and POP restore the saved registers from the machine stack; `PUSH 5` and `PUSH S` write two outgoing args to stack; each CALL pushes a return EIP; the two `RET 4` instructions read their return address and advance ESP. These are stack effects, **not direct writes to Q/S/item/owner fields**.

**LEA `0x0065EC5C: EDI=S+0x34`** only derives a pointer; it **does not dereference, set or clear** memory at `S+0x34`. MOVs among ESI/EDI/EBX/ECX/EDX/EAX and the two 8-bit XORs likewise make **no object-field writes**. **There are no explicit direct object/global stores anywhere in the function.**

Specifically, the audited body **does not directly read or write**:
- **`DWORD[Q]`** or **`DWORD[T]`**. Parent `0x00634F50` performed `T=DWORD[Q]` *before this function started*;
- **`DWORD[S]`**, or any direct store into **S=I+0x120**;
- **`DWORD[I]`** (item vptr), **`DWORD[I+0xE4]`** (outer wrapper's stored status), or original owner **`DWORD[O]`** (owner vptr);
- **`DWORD[O+0x14]`** (list registration count) or **`BYTE[O+0x2D]`** (readiness associated byte).

**Unknown alias/callee effects are not ruled out.** The first callee receives register-masked values derived from T/S; the second receives S+0x34; the third receives S, T and a scalar 5. Their *implementations may read/write those pointers or any reachable state*, and the exact identity/alias relationship of Q/T/I/O is unknown. This report's **empty direct object-field write-set** must not be expanded into a claim that execution has no side effects or can never affect original owner O.

## 5. Status-5 provenance and existing finite replay evidence

The caller `0x00508C70` immediately maps this function's EAX to:

~~~asm
00508df8: f7 d8                 neg    eax
00508dfa: 1b c0                 sbb    eax,eax
00508dfc: 83 e0 fc              and    eax,0xfffffffc
00508e00: 83 c0 05              add    eax,0x5
~~~

So **returned EAX=0 yields callback status 5; returned EAX!=0 yields status 1**. Now this body provides a further strict condition:

- If **`DWORD[S+0x34]==0`**, this helper returns **6**, so the parent callback returns **status 1**, not 5.
- If **`DWORD[S+0x34]!=0`**, this helper returns **the unmodified EAX from `0x0065FA60`**. **Only if that final callee returns zero** does the parent callback return status 5.

Thus **a status 5 observed from this specific inner target `0x00508C70` on its normal long path logically entails both `DWORD[S+0x34]!=0` at the guard and `0x0065FA60` returning zero**. This is a **static-flow implication**, not an independently observed runtime value for the guard or final callee.

**User-supplied earlier v790 trace:** one instance of `0x005088A0` chose inner virtual callback `0x00508C70` and that inner callback returned **EAX=5** for item `I=0x27DFAD78`; wrapper returned 5 as well. The known PE flow supports the above conditional implications for **that single normal invocation**. It does **not** establish why the final callee returned zero or what 5 means in game logic.

**User-supplied earlier v791 trace:** five outer `0x005088A0` calls yielded **EAX=5**, but their actual nested target EIPs were not all supplied. **Do not generalize `0x00508C70` or `0x0065EC50` execution to all five**. Separately observed owner `DWORD[O+0x14]=9` and writer `0x005092F0` clearing `BYTE[O+0x2D]=0` have **no direct causal link** to this function's return path. No replay was run during this task, and guest graphics/rendering or native Windows/Wine game behavior is not established.

**Bounded conclusion:** `0x0065EC50` is a **branching status-forwarder**: if S+0x34 is zero it returns fixed EAX=6; otherwise it calls two register-only helpers and a third helper with one more receiver-like pointer plus two stack values, forwarding that final EAX. It contains **no direct write to Q, S, I or O** and no direct instruction explaining changes to owner count, readiness byte, or vptr. The semantic types of these pointers/fields and all callee effects remain unknown.

## 6. Exactly one next evidence-backed target

**`0x0065FA60` — final direct CALL at `0x0065EC8A`**, return EIP `0x0065EC8F`, with **ECX=EAX from `0x0065C0E0`**, **EDX=T=DWORD[Q]`**, **first stack arg S=I+0x120**, **second stack arg 5**. This is the **sole next bounded address justified by the body**: its **zero/nonzero EAX** directly determines the status 5 versus 1 seen at the higher callback, on the nonzero-guard path. A distinct later bounded task can inspect only its complete original PE block for stack cleanup, direct effects and return conditions; **its body has not been inspected here**, no caller/writer sweep or replay is proposed.

## Appendix A — full original PE function 0x0065EC50–0x0065EC95, 33 instructions / 70 bytes

~~~asm
0065ec50: 55                    push   ebp
0065ec51: 8b ec                 mov    ebp,esp
0065ec53: 53                    push   ebx
0065ec54: 56                    push   esi
0065ec55: 8b f2                 mov    esi,edx
0065ec57: 83 7e 34 00           cmp    DWORD PTR [esi+0x34],0x0
0065ec5b: 57                    push   edi
0065ec5c: 8d 7e 34              lea    edi,[esi+0x34]
0065ec5f: 8b d9                 mov    ebx,ecx
0065ec61: 75 0c                 jne    0x65ec6f
0065ec63: 5f                    pop    edi
0065ec64: 5e                    pop    esi
0065ec65: b8 06 00 00 00        mov    eax,0x6
0065ec6a: 5b                    pop    ebx
0065ec6b: 5d                    pop    ebp
0065ec6c: c2 04 00              ret    0x4
0065ec6f: 32 d2                 xor    dl,dl
0065ec71: 32 c9                 xor    cl,cl
0065ec73: e8 b8 e0 ff ff        call   0x65cd30
0065ec78: 8b d7                 mov    edx,edi
0065ec7a: 8b c8                 mov    ecx,eax
0065ec7c: e8 5f d4 ff ff        call   0x65c0e0
0065ec81: 8b 4d 08              mov    ecx,DWORD PTR [ebp+0x8]
0065ec84: 51                    push   ecx
0065ec85: 56                    push   esi
0065ec86: 8b d3                 mov    edx,ebx
0065ec88: 8b c8                 mov    ecx,eax
0065ec8a: e8 d1 0d 00 00        call   0x65fa60
0065ec8f: 5f                    pop    edi
0065ec90: 5e                    pop    esi
0065ec91: 5b                    pop    ebx
0065ec92: 5d                    pop    ebp
0065ec93: c2 04 00              ret    0x4
~~~

**Publication: one report-only Markdown file on `work/process-reports`. No original PE, code, runtime, P-code, renderer, guest state or replay changes.**
