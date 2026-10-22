# Process 1b — bounded list detach body 0x0064EEF0 (original retail PE)

**Analysis date:** 2026-10-22; **report authored:** 2026-10-22T10:48:58.691Z. **Binary identity:** Need for Speed SHIFT PC retail 1.02, original SHIFT.exe PE32 x86, ImageBase `0x00400000`; SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` (locally verified retail hash **as supplied**). **Evidence basis:** the complete original 106-byte objdump block supplied in this assignment, reprinted verbatim in Appendix A, together with *previously established* callsites from the bounded 0x0064EF60 report. This report does not claim a new dynamic execution or a new original PE hash calculation.

**Exact bounds:** first instruction at `0x0064EEF0`; last instruction `0x0064EF57: C2 04 00 / RET 4` occupies `0x0064EF57–0x0064EF59`; end-exclusive `0x0064EF5A`; byte length `0x6A = 106`. Strict scope is **this entire function** and its two already-proven immediate callsites. There are **no CALL instructions of any kind** inside the body. No unrelated caller/writer/vtable survey or deep callee analysis, no replay, source/runtime/P-code/renderer/guest-state edits, native Windows/Wine run, or menu/race claims.

## 1. Exact known entry ABI, register/stack flow and return

Prior complete function `0x0064EF60` calls this helper from **two separate sites**:

| Source call | Prior caller input pointer P | Receiver and explicit stack argument | CPU return address |
|---|---|---|---|
| `0x0064EFB1: CALL 0x0064EEF0` | `P=DWORD[N+0x18]`, previously tested nonzero with `BYTE[P+0x28]&2 !=0` | `ECX=C`, one pushed DWORD `P` at `0x0064EFAE` | **`0x0064EFB6`** |
| `0x0064EFFF: CALL 0x0064EEF0` | `P=DWORD[N+0x1C]`, previously tested nonzero with `BYTE[P+0x28]&2 !=0` | `ECX=C`, one pushed DWORD `P` at `0x0064EFFC` | **`0x0064F004`** |

**C** is the previous body’s receiver/root, whose upstream observed source is **old `DWORD[O+0x38]`**. **O** is the older original owner; **N** is the previous caller's mutable current candidate/list element; **P** is this callee's *selected neighbor argument*; **L** and **R** below are P's link field values. Neither C, O, N, P, L nor R may be silently treated as the same pointer. A runtime alias is possible but **not established**.

The original function:

~~~asm
0064eef0: 55                    push   ebp
0064eef1: 8b ec                 mov    ebp,esp
0064eef3: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
~~~

Receives **`ECX=C`**, **`[EBP+8]=P`** as its **only explicit incoming stack DWORD**. On entry EAX is overwritten by this load, and incoming EDX has no proved use as an argument (it is overwritten by `MOV EDX,[EAX+0x10]`). It saves EBP and EDI; EDI is restored at exit. ECX remains C throughout this function: **no instruction changes ECX**, and there are no nested calls to clobber it.

**Normal return:** the only exit is `0x0064EF57: RET 0x4`, following `POP EDI; POP EBP`. The opcode **`C2 04 00`** proves callee-side cleanup of exactly **one 32-bit stack argument**; the known callers make no subsequent `ADD ESP,4` after these sites. **`0x0064EF4D: MOV EAX,DWORD[EAX]`** reads **`DWORD[P]`**; `0x0064EF4F` subtracts that value from a C-relative field but does not modify EAX. Therefore normal returned **EAX=DWORD[P]** as read at `0x0064EF4D`, not a Boolean or proven success indicator. The callers do not consume this EAX as a visible branch predicate immediately after these calls. No error branch, exception handling or recursive CALL appears inside the body.

## 2. Branch/dataflow, exact pointer identity and direct mutations

Define at entry:
- **`C=ECX`**, stable receiver pointer, separate from owner O.
- **`P=DWORD[EBP+8]`**, loaded into EAX at `0x0064EEF3` and retained as EAX until `0x0064EF4D`.
- **`L=DWORD[P+0x10]`** and **`R=DWORD[P+0x14]`**: two pointer-sized link fields. They are names for **values from original PE bytes**, not C++ field names.

### 2.1 First branch — update one neighbor or first C endpoint

~~~asm
0064eef6: 8b 50 10              mov    edx,DWORD PTR [eax+0x10]
0064eef9: 85 d2                 test   edx,edx
0064eefb: 57                    push   edi
0064eefc: 74 08                 je     0x64ef06
0064eefe: 8b 78 14              mov    edi,DWORD PTR [eax+0x14]
0064ef01: 89 7a 14              mov    DWORD PTR [edx+0x14],edi
0064ef04: eb 09                 jmp    0x64ef0f
0064ef06: 8b 50 14              mov    edx,DWORD PTR [eax+0x14]
0064ef09: 89 91 00 01 00 00     mov    DWORD PTR [ecx+0x100],edx
~~~

- Always **read L=DWORD[P+0x10]** and TEST it.
- If **L!=0**, read **R=DWORD[P+0x14]**, then **write DWORD[L+0x14]=R**. This branch does **not** update `DWORD[C+0x100]` directly.
- If **L==0**, load **R=DWORD[P+0x14]**, then **write DWORD[C+0x100]=R**. This is the *first* conditional C endpoint store. No evidence equates this slot with O+0x14 or an owner vptr.
- The `PUSH EDI` at `0x0064EEFB` occurs on both branches, **after** the TEST but before JE. It saves the callee-saved register; it is **not a new explicit argument** and does not alter flags.

### 2.2 Second branch — opposite neighbor or second C endpoint

~~~asm
0064ef0f: 8b 50 14              mov    edx,DWORD PTR [eax+0x14]
0064ef12: 85 d2                 test   edx,edx
0064ef14: 74 08                 je     0x64ef1e
0064ef16: 8b 78 10              mov    edi,DWORD PTR [eax+0x10]
0064ef19: 89 7a 10              mov    DWORD PTR [edx+0x10],edi
0064ef1c: eb 09                 jmp    0x64ef27
0064ef1e: 8b 50 10              mov    edx,DWORD PTR [eax+0x10]
0064ef21: 89 91 04 01 00 00     mov    DWORD PTR [ecx+0x104],edx
~~~

- Always re-read **R=DWORD[P+0x14]**; the original PE does **not** reuse EDI from the first branch or assume unchanged P links.
- If **R!=0**, read L anew and **write DWORD[R+0x10]=L**.
- If **R==0**, re-read L and **write DWORD[C+0x104]=L**. This is the *second* conditional C endpoint store.
- These four predecessor/successor cases are formed by **two independent zero tests**, not a test of list size or ownership.

**Pointer/field diagram, descriptive only:**

~~~text
Before:  L <--[+0x10]-- P --[+0x14]--> R

If L!=0: DWORD[L+0x14] = R
Else:    DWORD[C+0x100] = R

If R!=0: DWORD[R+0x10] = L
Else:    DWORD[C+0x104] = L

After:   DWORD[P+0x10] = 0; DWORD[P+0x14] = 0
~~~

This precisely implements *link detachment from a doubly connected structure at these field offsets*, conditional on valid pointers/links. It is not a proven source-level linked-list class or heap free.

### 2.3 Flag update, counter/sum adjustment, exit

~~~asm
0064ef27: 66 8b 50 28           mov    dx,WORD PTR [eax+0x28]
0064ef2b: 66 81 e2 fd ff        and    dx,0xfffd
0064ef30: 66 83 ca 04           or     dx,0x4
0064ef34: c7 40 14 00 00 00 00  mov    DWORD PTR [eax+0x14],0x0
0064ef3b: c7 40 10 00 00 00 00  mov    DWORD PTR [eax+0x10],0x0
0064ef42: 66 89 50 28           mov    WORD PTR [eax+0x28],dx
0064ef46: 83 81 e8 00 00 00 ff  add    DWORD PTR [ecx+0xe8],0xffffffff
0064ef4d: 8b 00                 mov    eax,DWORD PTR [eax]
0064ef4f: 29 81 ec 00 00 00     sub    DWORD PTR [ecx+0xec],eax
0064ef55: 5f                    pop    edi
0064ef56: 5d                    pop    ebp
0064ef57: c2 04 00              ret    0x4
~~~

- **READ WORD[P+0x28]** into the low half DX; **`DX = (old WORD & 0xFFFD) | 0x0004`**. This specifically **clears bit 1 (0x02)** and **sets bit 2 (0x04)**; all other word bits are preserved. The 16-bit DX operation does not guarantee a new value for full EDX, but full EDX is not used subsequently.
- **WRITE DWORD[P+0x14]=0** and **WRITE DWORD[P+0x10]=0**. Then **WRITE WORD[P+0x28]=DX**.
- **READ-MODIFY-WRITE DWORD[C+0xE8] += 0xFFFFFFFF**, i.e. decrement by one modulo 2^32; **no zero/saturation check**.
- **READ DWORD[P]** into EAX, then **READ-MODIFY-WRITE DWORD[C+0xEC] -= EAX**; no checked-underflow guard. This value is **not** proven to be a byte count, allocation size or total cost, although an accumulator interpretation is structurally plausible.
- **Return EAX=DWORD[P]**, saved EDI and EBP restored, **RET 4**. Neither C+0xE8 nor C+0xEC is read as an incoming semantic parameter; the processor reads them implicitly for read-modify-write.

## 3. Exhaustive direct memory access ledger

| Source instruction | Direct access | Branch condition |
|---|---|---|
| `0x0064EEF3` | READ DWORD[EBP+8] (=P) | Always |
| `0x0064EEF6` | READ DWORD[P+0x10] (=L) | Always |
| `0x0064EEFE` | READ DWORD[P+0x14] (=R) | If L!=0 |
| `0x0064EF01` | **WRITE DWORD[L+0x14]=R** | If L!=0 |
| `0x0064EF06` | READ DWORD[P+0x14] (=R) | If L==0 |
| `0x0064EF09` | **WRITE DWORD[C+0x100]=R** | If L==0 |
| `0x0064EF0F` | READ DWORD[P+0x14] (=R) | Always |
| `0x0064EF16` | READ DWORD[P+0x10] (=L) | If R!=0 |
| `0x0064EF19` | **WRITE DWORD[R+0x10]=L** | If R!=0 |
| `0x0064EF1E` | READ DWORD[P+0x10] (=L) | If R==0 |
| `0x0064EF21` | **WRITE DWORD[C+0x104]=L** | If R==0 |
| `0x0064EF27` | READ WORD[P+0x28] | Always |
| `0x0064EF34` | **WRITE DWORD[P+0x14]=0** | Always |
| `0x0064EF3B` | **WRITE DWORD[P+0x10]=0** | Always |
| `0x0064EF42` | **WRITE WORD[P+0x28]=(old & 0xFFFD) \| 0x0004** | Always |
| `0x0064EF46` | **READ-MODIFY-WRITE DWORD[C+0xE8] -=1** | Always |
| `0x0064EF4D` | READ DWORD[P+0] | Always |
| `0x0064EF4F` | **READ-MODIFY-WRITE DWORD[C+0xEC] -= DWORD[P]** | Always |

Other memory behavior is limited to implicit machine-stack accesses from **PUSH EBP, PUSH EDI, POP EDI, POP EBP and RET 4** (including callee popping the return address and advancing ESP past the one incoming arg). There are **zero CALL instructions**, **zero dynamically dispatched targets**, **no global memory operand** and **no direct copy between original O and C**. The table covers all explicit memory operands of the original function.

## 4. Direct call-boundary count and limits of upstream evidence

**Inside `0x0064EEF0–0x0064EF59`: zero outgoing calls**; there are no callee effects to ascribe directly to it, and no recursive call in the body. The two incoming callsites `0x0064EFB1` and `0x0064EFFF` are *different static sites with the same exact ABI*. The previous enclosing function `0x0064EF60` **may write other link/size fields after either return**, but those later instructions are **not** effects of this callee. In particular:
- following `0x0064EFB6`, the caller then adds `DWORD[N]` to `DWORD[P]` and adjusts neighbor links;
- following `0x0064F004`, the caller instead adds `DWORD[P]` to `DWORD[N]` and adjusts different links.

The current helper's **own** writes end at `0x0064EF4F` before its return; conflating those subsequent caller changes with it would overstate provenance.

**Owner separation and alias uncertainty:** The original owner **O** provided old `DWORD[O+0x38]` from which **C** originated in the established upstream path. This callee **never has O as a proved operand**. It directly manipulates C, P, L and R; it does **not** contain an original-PE instruction directly addressing **DWORD[O]** (vptr), **DWORD[O+0x14]** (the separate UI insertion count), or **BYTE[O+0x2D]** (readiness). The fact that this function **writes `DWORD[P+0x14]`** does **not** mean it writes `DWORD[O+0x14]`; the bases are different and no alias has been shown. Likewise C+0xE8 decrement is **not** O+0x14 decrement. As with any pointer-based code, unusual/undocumented aliasing of C/P/L/R with O could yield indirect overlap, but this is **unknown**; neither guaranteed absence nor a positive alias is supported.

**Observed runtime (separate):** user-supplied finite v791 original PE P-code guest replay observed `DWORD[O+0x14]=9` and later `0x005092F0` zeroing `BYTE[O+0x2D]`. No supplied replay event proves `0x0064EEF0` executed. There is no direct instruction-level explanation in this helper for the readiness write, and no basis for a readiness repair or actual UI draw/menu/race claim. This report performs no replay.

**Bounded conclusion:** the helper directly unlinks one P node from C-relative endpoints/neighbor links, clears the node's two connection slots, changes two defined bits in its 16-bit flags field, decrements C+0xE8 and subtracts a P-derived DWORD from C+0xEC, returning that P-derived value with one stack argument cleaned. Calling it a *detachment operation* is grounded in pointer assignments, whereas type/ownership/class/resource semantics and any effect on O's readiness remain **unproved**.

## 5. Exactly one next evidence-backed target

**`0x00657440`** — the immediate **one-stack-argument downstream handler** invoked by the previously bounded parent `0x0064EF60` after merge/detach, at two concrete callsites **`0x0064EFE6`** (argument current N, return `0x0064EFEB`) and **`0x0064F07D`** (argument selected P, ECX=C, return `0x0064F082`). It is the *single* next bounded address justified by the relationship between this helper's unlink operations and the parent's subsequent handling of discarded/merged element pointers. The callee's effects are **unknown**, and its body is **not analyzed here**. A separate assignment should study only that callee's original PE block and immediate ABI, with no global sweep or replay.

## Appendix A — complete supplied original retail objdump 0x0064EEF0–0x0064EF59 (106 bytes)

~~~asm
0064eef0: 55                    push   ebp
0064eef1: 8b ec                 mov    ebp,esp
0064eef3: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0064eef6: 8b 50 10              mov    edx,DWORD PTR [eax+0x10]
0064eef9: 85 d2                 test   edx,edx
0064eefb: 57                    push   edi
0064eefc: 74 08                 je     0x64ef06
0064eefe: 8b 78 14              mov    edi,DWORD PTR [eax+0x14]
0064ef01: 89 7a 14              mov    DWORD PTR [edx+0x14],edi
0064ef04: eb 09                 jmp    0x64ef0f
0064ef06: 8b 50 14              mov    edx,DWORD PTR [eax+0x14]
0064ef09: 89 91 00 01 00 00     mov    DWORD PTR [ecx+0x100],edx
0064ef0f: 8b 50 14              mov    edx,DWORD PTR [eax+0x14]
0064ef12: 85 d2                 test   edx,edx
0064ef14: 74 08                 je     0x64ef1e
0064ef16: 8b 78 10              mov    edi,DWORD PTR [eax+0x10]
0064ef19: 89 7a 10              mov    DWORD PTR [edx+0x10],edi
0064ef1c: eb 09                 jmp    0x64ef27
0064ef1e: 8b 50 10              mov    edx,DWORD PTR [eax+0x10]
0064ef21: 89 91 04 01 00 00     mov    DWORD PTR [ecx+0x104],edx
0064ef27: 66 8b 50 28           mov    dx,WORD PTR [eax+0x28]
0064ef2b: 66 81 e2 fd ff        and    dx,0xfffd
0064ef30: 66 83 ca 04           or     dx,0x4
0064ef34: c7 40 14 00 00 00 00  mov    DWORD PTR [eax+0x14],0x0
0064ef3b: c7 40 10 00 00 00 00  mov    DWORD PTR [eax+0x10],0x0
0064ef42: 66 89 50 28           mov    WORD PTR [eax+0x28],dx
0064ef46: 83 81 e8 00 00 00 ff  add    DWORD PTR [ecx+0xe8],0xffffffff
0064ef4d: 8b 00                 mov    eax,DWORD PTR [eax]
0064ef4f: 29 81 ec 00 00 00     sub    DWORD PTR [ecx+0xec],eax
0064ef55: 5f                    pop    edi
0064ef56: 5d                    pop    ebp
0064ef57: c2 04 00              ret    0x4
~~~

**Report only, branch `work/process-reports`; no modification of executable, source, runtime, P-code, renderer, guest state, or replay.**
