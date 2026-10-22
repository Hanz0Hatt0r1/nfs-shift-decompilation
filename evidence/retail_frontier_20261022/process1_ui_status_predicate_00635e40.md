# Process 1b — bounded UI status predicate 0x00635E40

**Report date:** 2026-10-22. **Audit completed at (UTC):** 2026-10-22T11:40:49.295Z. **Original binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`; local `/mnt/data/SHIFT.exe` SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**. Independently checked with `sha256sum /mnt/data/SHIFT.exe`; bounded `objdump -D -Mintel -w --start-address=0x00635e40 --stop-address=0x00635e60 /mnt/data/SHIFT.exe` independently reproduced the entire supplied function and immediately following INT3 padding.

**Exact function bounds:** `0x00635E40–0x00635E59` inclusive, end-exclusive `0x00635E5A`, **`0x1A = 26 bytes`, 12 original instructions**. `0x00635E5A` onward comprises `INT3` padding, not the function. **Scope:** only this entire original PE body, one previously established immediate *incoming* call boundary at `0x006534A2`, and return-edge implications in the immediate caller. **No outgoing CALLs inside this function** (zero direct, indirect or recursive call sites). No global writer/caller/vtable sweep, callee bodies, source/runtime/P-code/renderer/guest-state changes, replay or native game launch. Full unchanged objdump text is in Appendix A.

## 1. Incoming ABI, caller register source and exact return behavior

The previously published, separately verified caller `0x00653480` performs:

~~~asm
0065349f: 8d 4e 08              lea    ecx,[esi+0x8]
006534a2: e8 99 29 fe ff        call   0x635e40
006534a7: 84 c0                 test   al,al
006534a9: 74 0f                 je     0x6534ba
006534ab: 6a 0a                 push   0xa
006534ad: 8b ce                 mov    ecx,esi
006534af: e8 2c ea ff ff        call   0x651ee0
006534b4: 5f                    pop    edi
006534b5: 5e                    pop    esi
006534b6: 5d                    pop    ebp
006534b7: c2 10 00              ret    0x10
~~~

Here **V** is the receiver of `0x00653480`, which in one earlier bounded P-code probe entered as ECX=`0x36214784`. Its caller originally supplied `V=P+0x64` where **P** is an object returned by `0x0065C0E0` in the status chain. The target **`0x00635E40` receives ECX=X=V+8**, not V, callback item **I**, or original UI owner **O**. The earlier callback chain has **not** established pointer alias equalities `X==O`, `V==O` or `X==I`.

| Machine component at `0x00635E40` entry | Byte-proven value / origin |
|---|---|
| **ECX** | **`X=V+8`**, from caller `LEA ECX,[ESI+8]` with caller ESI=V |
| **EDX** | **0** for this immediate caller path: outer caller `0x0065FA60` set EDX=0 when calling `0x00653480`, and the prefix of `0x00653480` does not modify EDX before `CALL 0x00635E40`. This is **not** an input used by the predicate itself |
| EAX incoming | **Unspecified** from the caller by the relevant setup; partly preserved on one branch, overwritten on others |
| **`[ESP]`** at target entry | Return EIP **`0x006534A7`** (CPU-pushed by direct CALL) |
| Explicit stack arguments | **None**, zero newly pushed arguments at this CALL |

This target has **no prologue, local stack allocation, PUSH, POP, or register save/restore**. It has exactly **two plain `RET` opcodes (`C3`)** at `0x00635E56` (AL=0 path) and `0x00635E59` (AL=1 path); there is **no `RET imm16` and no callee-side explicit-argument cleanup**. On normal exit, the CPU pops the return address, transferring to `0x006534A7`. The target's instructions **do not change ECX, EDX, EBX, ESI or EDI**. They do change EFLAGS, and may change EAX or only its low byte, depending on branch.

The immediate caller tests **AL**, not full EAX: `0x006534A7: TEST AL,AL`, `0x006534A9: JE 0x006534BA`. If **AL=0**, it enters the main initialization path of `0x00653480`, which (upon normal return from its own outgoing helpers) explicitly executes `XOR EAX,EAX` and returns zero. If **AL!=0**, it calls **`0x00651EE0`** with a pushed literal `10` and forwards that callee's return EAX; the predicate's own full EAX is *not* used as a status there. Importantly this caller edge is only reached if its **earlier test of BYTE[V+0xCC] & 0x02 was zero**; otherwise `0x00653480` calls `0x00651EE0` with a *different* literal 3 and **does not invoke this predicate**.

## 2. Complete control flow and necessary-and-sufficient AL conditions

Let **`X=ECX=V+8`**. Define:
- **`D=DWORD[X+4]`**, always read first.
- **`A=DWORD[X]`**, read *only when D!=0*.
- **`W=unsigned WORD[A−4]`**, read *only when D!=0 and A!=0*. Since it is loaded via `MOVZX`, **`W∈[0,65535]`**, and full EAX immediately after this load is W.

The complete original function:

~~~asm
00635e40: 83 79 04 00           cmp    DWORD PTR [ecx+0x4],0x0
00635e44: 74 11                 je     0x635e57
00635e46: 8b 01                 mov    eax,DWORD PTR [ecx]
00635e48: 85 c0                 test   eax,eax
00635e4a: 74 0b                 je     0x635e57
00635e4c: 0f b7 40 fc           movzx  eax,WORD PTR [eax-0x4]
00635e50: 85 c0                 test   eax,eax
00635e52: 7e 03                 jle    0x635e57
00635e54: 32 c0                 xor    al,al
00635e56: c3                    ret
00635e57: b0 01                 mov    al,0x1
00635e59: c3                    ret
~~~

**Branches in original instruction order:**

1. **`CMP DWORD[X+4],0`** at `0x00635E40`, followed by **`JE 0x00635E57`** at `0x00635E44`. When **D==0**, return **AL=1** without dereferencing `DWORD[X]` or `WORD[A−4]`.
2. If D!=0, **`MOV EAX,DWORD[X]`** at `0x00635E46` and `TEST EAX,EAX` at `0x00635E48`; **`JE 0x00635E57`** at `0x00635E4A` if **A==0**, yielding **AL=1** without dereferencing the word.
3. If D!=0 and A!=0, **`MOVZX EAX,WORD[A−4]`** at `0x00635E4C` (zero-extending into EAX), followed by **`TEST EAX,EAX`** at `0x00635E50` and **`JLE 0x00635E57`** at `0x00635E52`. Here **JLE is a signed comparison of the flags from TEST**, but because MOVZX guarantees **0<=EAX<=65535**, its sign bit is always 0 and TEST clears OF: thus **`JLE` is taken if and only if W==0**. It is **not** evidence of a negative WORD or signed-length check.
4. Only with **D!=0, A!=0 and W!=0**, execute **`XOR AL,AL`** at `0x00635E54` and return at `0x00635E56`. This clears **only AL**, not the entire EAX.

**Necessary-and-sufficient normal return predicates** (assuming each performed memory dereference completes normally, no concurrent mutation changing the loaded values):

| Condition in observed read sequence | Returned AL | Control return EIP in this known call |
|---|---|---|
| **D==0** | **1** | `0x006534A7` via `RET at 0x00635E59` |
| **D!=0, A==0** | **1** | `0x006534A7` via `RET at 0x00635E59` |
| **D!=0, A!=0, W==0** | **1** | `0x006534A7` via `RET at 0x00635E59` |
| **D!=0, A!=0, W!=0** | **0** | `0x006534A7` via `RET at 0x00635E56` |

Equivalently, **`AL=0 iff (D!=0 && A!=0 && W!=0)`**; **`AL=1 iff (D==0 || (D!=0 && A==0) || (D!=0 && A!=0 && W==0))`**. No other AL outcomes exist on a normal return.

### Full EAX is not a normalized Boolean

The function's contract at this callsite is **AL**, not necessarily an exact 32-bit EAX=0 or 1:
- **D==0 branch:** `MOV AL,1` changes only the low 8 bits of whatever **incoming EAX** held. Full return **`EAX=(EAX_entry & 0xFFFFFF00)|1`**, so upper 24 bits are unspecified by this function.
- **D!=0, A==0:** EAX became 0 at the pointer read, so full return **EAX=1**.
- **D!=0, A!=0, W==0:** MOVZX made EAX=0; full return **EAX=1**.
- **D!=0, A!=0, W!=0:** MOVZX made EAX=W; **`XOR AL,AL`** gives **`EAX=W & 0x0000FF00`**, which **can be nonzero** (e.g., W=0x0100 gives EAX=0x0100) despite **AL=0**. The caller `TEST AL,AL` correctly uses the byte predicate.

No branch tests EDX, performs a CALL, modifies object state, or uses a returned callee value: **there are no outgoing calls at all**.

## 3. Exhaustive direct memory reads and write-set

**Explicit non-stack data reads**:

| EIP | Exact operand | Width, condition and interpretation limit |
|---|---|---|
| **`0x00635E40`** | **READ DWORD[X+4]** | Always; compare with immediate 0 |
| **`0x00635E46`** | **READ DWORD[X]** into EAX | Only if prior DWORD[X+4] != 0 |
| **`0x00635E4C`** | **READ WORD[A−4]** into zero-extended EAX | Only if prior D!=0 and A!=0; A was a pointer-sized DWORD loaded from X |

There are **no explicit memory writes** in the complete 26-byte body: no receiver-relative stores, no global stores, no stack PUSH or local-frame stores. **The two RETs implicitly READ a return-address DWORD from the machine stack** and advance ESP by 4, but they are not object stores or extra argument cleanup. Arithmetic/flag instructions and `MOV AL,1` affect registers only. No data memory value is modified directly.

In terms of the known caller, **X=V+8**, so the first two data reads are **`DWORD[V+0x0C]`** and conditionally **`DWORD[V+8]`**, followed by **`WORD[DWORD[V+8]−4]`** if those first two predicates pass. Even this reexpression is **V-relative, not original-owner O-relative**. The function does **not** directly read or write **DWORD[O]** (vptr), **DWORD[O+0x14]** (separately observed count), **BYTE[O+0x2D]** (separately observed readiness) or any field of original callback item I by a proven I pointer.

**Alias / asynchronous limits:** pointer X or dereferenced A may at runtime alias another object or global memory; object identity has not been verified. But because **the body contains no explicit data stores**, it does not itself directly update O, I, V, X, A or their fields even if an alias exists. External asynchronous writes could affect the values it reads, but none are evidenced by this static body. There are also **no nested callees**, so there are **no unknown immediate callee side effects to assign to this function**.

## 4. Outgoing CALL boundary count: zero

**There are exactly zero CALL instructions in `0x00635E40–0x00635E59`**, including **zero direct**, **zero indirect** and **zero recursive** calls. Hence there is **no list of outgoing CALL targets or return EIPs to enumerate**. The sole previously established **incoming** CALL is **`0x006534A2 → 0x00635E40`** with caller return **`0x006534A7`**, **ECX=V+8**, **EDX=0**, **no stack arguments**, and no callee argument cleanup. That established caller itself conditionally invokes **`0x00651EE0`** *after* receiving AL=1. The `0x00651EE0` call is **not** inside this 26-byte predicate and is not mislabeled an outgoing call of this function.

No vtable lookup, owner-vptr read, indirect dispatch, branch into padding, or write to original owner readiness appears in the target body.

## 5. Previous finite P-code evidence and limits

**Previously reported bounded P-code probe (not repeated):** one dynamic path through `0x00634F50 → 0x0065EC50 → 0x0065FA60 → 0x00653480` recorded entry to `0x00653480` with **ECX=0x36214784**, EDX=0, EAX=0x00010000, and exit EAX=0. The probe later timed out at 180 seconds / exit124 after 890 guest Present requests, without a host-frame checkpoint. **It did not record the byte gate `BYTE[V+0xCC]`, entry into this 0x00635E40 predicate, or its return AL**, so it cannot identify the selected branch in `0x00653480`. The predicate may not have been executed if the earlier gate was set.

**Older v229–v239 request-path probe** separately returned EAX=0 from `0x00653480` in a different context (`guest_draw_translation=false`). That is not this new static observation, not proof of this predicate's branch, and not a native game-run or UI render.

**Separate v790/v791 status traces** reported one selected inner `0x00508C70` status 5 in v790 and five outer status results of 5 in v791 without full selected inner targets. The observed owner count `DWORD[O+0x14]=9` and readiness writer `0x005092F0` clearing `BYTE[O+0x2D]` are independent evidence; **neither these values nor their cause is determined by this read-only predicate**. The original PE body provides no direct owner-readiness change or count decrement; do not infer menu, race or draw translation.

**Bounded conclusion:** `0x00635E40` implements a **read-only, three-gate AL predicate**. It returns **AL=0 iff all three tested nonzero requirements hold** (DWORD[X+4], DWORD[X], unsigned WORD[DWORD[X]−4]); otherwise **AL=1**. The full EAX may differ from zero/one because only AL is written on both exits. In its established caller, **AL=0 selects the main initialization path which later forces EAX=0**; **AL=1 selects a different callee-determined return path**. This static result does **not** show that either path executed in the supplied P-code probe, and does not directly explain readiness or owner count.

## 6. Exactly one evidence-backed next target, outside this callee-free body

**`0x00651EE0`** — the **only proposed next address**, *not* a callee of `0x00635E40`. It is a separately observed **direct callee of the immediately verified parent `0x00653480`** at **`0x006534AF`**, return EIP **`0x006534B4`**, when this predicate returns **AL=1**, with **ECX=V**, **EDX not guaranteed after the predicate's caller chain**, and **one pushed stack DWORD 10**. The parent also calls the same target at `0x00653494` with a different outgoing argument 3 when its preceding flag gate is set. Studying this *single separately bounded target* could resolve the **unknown EAX on the early paths** that may also be zero despite bypassing the forced-zero main path. No caller/writer sweep, replay or body study of `0x00651EE0` is undertaken here. **No other next target proposed.**

## Appendix A — complete original retail function and exact bytes (26 bytes, 12 instructions)

~~~asm
00635e40: 83 79 04 00           cmp    DWORD PTR [ecx+0x4],0x0
00635e44: 74 11                 je     0x635e57
00635e46: 8b 01                 mov    eax,DWORD PTR [ecx]
00635e48: 85 c0                 test   eax,eax
00635e4a: 74 0b                 je     0x635e57
00635e4c: 0f b7 40 fc           movzx  eax,WORD PTR [eax-0x4]
00635e50: 85 c0                 test   eax,eax
00635e52: 7e 03                 jle    0x635e57
00635e54: 32 c0                 xor    al,al
00635e56: c3                    ret
00635e57: b0 01                 mov    al,0x1
00635e59: c3                    ret
~~~

Original following bytes, **outside body**:

~~~asm
00635e5a: cc                    int3
00635e5b: cc                    int3
00635e5c: cc                    int3
00635e5d: cc                    int3
00635e5e: cc                    int3
00635e5f: cc                    int3
~~~

**Report-only publication on `work/process-reports`. No runtime, source, P-code, renderer, guest state or replay edits.**
