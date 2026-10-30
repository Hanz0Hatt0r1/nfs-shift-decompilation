# Process 1 — bounded original-retail forwarder 0x00651EE0

**Analysis date:** 2026-10-22. **Report authored (UTC):** 2026-10-22T11:49:10.064Z. **Original binary:** Need for Speed SHIFT PC retail 1.02 `SHIFT.exe`, PE32 x86, ImageBase `0x00400000`. **Independently reverified local SHA-256:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` (`sha256sum /mnt/data/SHIFT.exe`). The supplied complete original disassembly was checked with bounded GNU `objdump -D -M intel -w --start-address=0x00651ee0 --stop-address=0x00651ef8 /mnt/data/SHIFT.exe`. It matches the original PE byte for byte, subject only to the **corrected length/padding boundary** below. Full text of the nine body instructions is included in Appendix A.

**Exact verified PE extent:** `0x00651EE0–0x00651EF3` inclusive, exclusive end `0x00651EF4`, **`0x14=20 bytes`** and **nine instructions**. The supplied assignment's “19 bytes, INT3 begins at `0x00651EF3`” is an **off-by-one error**: the final **`0x00651EF1: C2 04 00`** occupies addresses **`0x00651EF1–0x00651EF3`**, so INT3 padding starts at **`0x00651EF4`**, verified in original PE. The padding does not belong to the function.

**Scope:** strictly this entire body and **only the two already established direct incoming callsites in its immediate parent `0x00653480`**. No additional caller/writer lookup, no outgoing callee bodies (there are none), no guest replay, source/runtime/P-code/renderer/guest-state changes, native game run, host-frame/render/menu/race claim. Finite previous probe observations are kept separate from the current static byte-derived proof.

## 1. Known callsites and exact incoming ABI

The previously bounded `0x00653480` caller receives **`ECX=V`**, where `V=P+0x64` for the previously audited status chain. **V is not a proved alias of callback item I or original owner O**. Its ESI holds V, and EDI stores the original incoming EDX (zero in the established `0x0065FA60` call). For the two *direct incoming callsites*:

| Caller site | Condition before call | Explicit call preparation | Callee machine entry | Return EIP |
|---|---|---|---|---|
| **`0x00653494: CALL 0x00651EE0`** | `BYTE[V+0xCC] & 0x02 != 0` | `0x00653492: PUSH 3`; prior `ECX=V` unchanged | **ECX=V, EDX=0** on established chain; **`[EBP+8]=3`** | **`0x00653499`** |
| **`0x006534AF: CALL 0x00651EE0`** | initial `BYTE[V+0xCC] & 0x02 == 0`; predicate `0x00635E40` returned **AL!=0** | `0x006534AB: PUSH 10`, `0x006534AD: MOV ECX,ESI` | **ECX=V, EDX=0** on established chain; **`[EBP+8]=10`** | **`0x006534B4`** |

**EDX at the second callsite:** unlike a merely hypothetical opaque callee, the immediately preceding predicate `0x00635E40` has already been **separately audited in the preceding bounded report** and its entire 26-byte body **never changes EDX**. Since `0x00653480` entered this branch with EDX=0 and does not rewrite EDX, the second callsite also has **EDX=0** in the *established* chain. This relies only on previously established bounded bytes, **not** on a new callee-body audit or a broad search. This helper **does not consume or change EDX**, so EDX is not a meaningful input here.

The only explicit stack input is **`[EBP+8]=A`**, a 32-bit DWORD pushed by the parent. The function has **no additional arguments** in this established calling convention, **no ECX dereference until its direct store**, no ESI/EDI/EBX save, no local allocation and no indirect register dispatch. On entry `[EBP+4]` holds one of the two listed return addresses. **Full incoming EAX is overwritten** by `MOV EAX,[EBP+8]`.

The prologue is **`PUSH EBP; MOV EBP,ESP`**. The only exit is **`POP EBP; RET 4`** (`C2 04 00` at `0x00651EF1`), which pops the return address and **callee-cleans exactly one 4-byte explicit caller argument**. Both caller sites immediately restore saved registers, without `ADD ESP,4`. This stack balance is **proven by the actual callee opcode**, not inferred solely from the parent.

## 2. Complete control flow, return EAX and necessary/sufficient predicates

The whole body has one conditional jump (`JNE 0x00651EF0`), no loop and no CALL:

~~~asm
00651ee0: 55                    push   ebp
00651ee1: 8b ec                 mov    ebp,esp
00651ee3: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00651ee6: 85 c0                 test   eax,eax
00651ee8: 89 41 24              mov    DWORD PTR [ecx+0x24],eax
00651eeb: 75 03                 jne    0x651ef0
00651eed: 89 41 28              mov    DWORD PTR [ecx+0x28],eax
00651ef0: 5d                    pop    ebp
00651ef1: c2 04 00              ret    0x4
~~~

Define **`A=DWORD[EBP+8]`** (the original stack argument), and **`V=ECX`** (receiver). `TEST EAX,EAX` sets ZF when A==0; **the intervening store `MOV DWORD[V+0x24],EAX` does not modify EFLAGS**. Therefore:

- **For A!=0:** always **WRITE DWORD[V+0x24]=A**, then `JNE` skips the second store, restores EBP and **returns EAX=A**. Necessary/sufficient zero-test fact: second store does not run iff A!=0, assuming normal execution without a fault at the first store.
- **For A==0:** always **WRITE DWORD[V+0x24]=0**, `JNE` not taken, additionally **WRITE DWORD[V+0x28]=0**, then restores EBP and **returns EAX=0**.
- **For all normal executions:** the **full 32-bit EAX equals incoming A**; not merely AL, not 0/1 normalization, and not a status manufactured from callee results. `ECX` and `EDX` are unchanged by body instructions. No memory contents are read from V before writing those fields.

**Exhaustive return table:**

| Actual caller | A passed | `DWORD[V+0x24]` | `DWORD[V+0x28]` | Returned full EAX |
|---|---:|---:|---|---:|
| Parent `0x00653494` | **3** | **3** | **Not written** | **3** |
| Parent `0x006534AF` | **10** | **10** | **Not written** | **10** |
| General hypothetical A==0 (not these known parent callsites) | **0** | **0** | **0** | **0** |
| General hypothetical A!=0 | **A** | **A** | **Not written** | **A** |

This is **not** a claim that `V+0x24` holds an error code, readiness state or any other source-language named field. Its actual semantics are unknown.

## 3. Exhaustive direct memory read/write ledger

| Instruction | Direct memory operand | Proven width, condition, effect |
|---|---|---|
| `0x00651EE3` | **READ DWORD[EBP+8]** | Unconditional stack read; EAX=A |
| `0x00651EE8` | **WRITE DWORD[ECX+0x24]** | Unconditional 32-bit store of A into **V+0x24** |
| `0x00651EED` | **WRITE DWORD[ECX+0x28]** | Conditional 32-bit store **of 0**, iff **A==0** |

This is the **entire explicit memory operand set**. `PUSH EBP` and `CALL` (performed by caller) implicitly write saved frame/return address to the machine stack; `POP EBP` and `RET 4` read those values. There are **no direct receiver-memory reads**. There are **no other explicit object-field writes**, no global access, no vptr dereference/write, no other item- or owner-relative address forms, and **zero outgoing CALLs** (direct or indirect). On the known arg=3 or arg=10 paths the *entire object-field write-set* is only **`DWORD[V+0x24]`**.

**Owner/item separation:** V is a receiver derived upstream from `P+0x64`. Item I came from a status callback; original owner O was represented via an item field in that upstream chain but is **not this helper's proven ECX receiver**. Thus direct **V+0x24** and **V+0x28** stores cannot be relabeled as **I+offset**, **O+0x14**, **O+0x2D**, or **DWORD[O]** (original owner vptr), absent an explicit address-equality/alias proof. Possible address aliasing remains **unknown**, as do external asynchronous effects. The body itself has **no outgoing callees**, so there are no unknown *nested callee* effects of `0x00651EE0`.

## 4. What this proves about the parent's observed EAX=0

In **`0x00653480`**, both early paths call this helper and **immediately forward its returned EAX unchanged** through the parent's `RET 0x10`:

- Early **BYTE[V+0xCC]&0x02 set** case **must return EAX=3**, provided the call returns normally. It **cannot** return zero.
- Early `0x00635E40` **AL!=0** case **must return EAX=10**, provided the call returns normally. It **cannot** return zero.
- The parent **main initialization** case (initial gate clear and predicate AL==0) **executes `XOR EAX,EAX` near its exit** and locally returns **EAX=0** after its outgoing calls return normally.

Therefore, for an observed **normal `0x00653480` return EAX=0**, the **necessary and sufficient parent path selection** from these fully audited PE bodies is: **first BYTE[V+0xCC] mask-2 gate clear and `0x00635E40` AL=0**, and the parent’s main path must complete normally. This strengthens the previous static report which had not yet audited `0x00651EE0` and therefore had treated its early returned EAX as unknown.

**Already supplied bounded P-code trace, not rerun here:** latest trace observed **first gate clear and `0x00635E40` AL=0**, so **neither** early helper call ran on that observed main path. An earlier probe also recorded `0x00653480` returning EAX=0 in the existing status chain, but it had not independently recorded every nested callee return. The newly proven body is fully consistent with these **separately supplied** observations; **no fresh replay event or new dynamic execution is claimed**. Historical request-path v229–v239 observations are also separate. The earlier trace's timeout/host-frame/guest draw limitations remain in force, and the present helper proves nothing about menu, race or GPU draw translation.

**Readiness/count limits:** this helper has direct **V-relative** stores, and no byte-proven direct original-owner store **DWORD[O+0x14]**, **BYTE[O+0x2D]** or **DWORD[O]**. The callback outer status value 5 is still generated only higher up by a zero/nonzero mapping; this helper’s early arg=3/10 results yield a **nonzero** value and do not themselves explain readiness, count or original owner vptr. Neither a source-language field role nor any cross-object alias is established by this bounded audit.

## 5. Bounded conclusion and next-target decision

**Bounded conclusion:** `0x00651EE0` is a **two-store, one-branch, callee-cleaning register/stack forwarder**. It unconditionally writes its first stack DWORD to **DWORD[ECX+0x24]**, writes zero to **DWORD[ECX+0x28]** only when that argument is zero, and returns the **same full EAX argument** via `RET 4`. For the **only two documented immediate parent callsites**, its outputs are **exactly 3 and 10**, respectively. Hence **neither early parent path can account for a zero result**, and a normally returned `0x00653480` EAX=0 uniquely selects the already audited main path.

**Next-target decision: none proposed.** This 20-byte body contains **zero direct/indirect CALL targets**, and its two known immediate caller sites plus the `0x00635E40` predicate have already been bounded-audited. Naming an unrelated or previously analyzed address as a "next target" would not be grounded in **this function's body**. This explicitly follows the assignment's **“one next target only if justified”** restriction; no global search, new replay or second task is authorized.

## Appendix A — complete original retail assembly (20 bytes; 9 instructions)

~~~asm
00651ee0: 55                    push   ebp
00651ee1: 8b ec                 mov    ebp,esp
00651ee3: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00651ee6: 85 c0                 test   eax,eax
00651ee8: 89 41 24              mov    DWORD PTR [ecx+0x24],eax
00651eeb: 75 03                 jne    0x651ef0
00651eed: 89 41 28              mov    DWORD PTR [ecx+0x28],eax
00651ef0: 5d                    pop    ebp
00651ef1: c2 04 00              ret    0x4
~~~

Original PE bytes immediately after the function, **not part of it**:

~~~asm
00651ef4: cc                    int3
00651ef5: cc                    int3
00651ef6: cc                    int3
00651ef7: cc                    int3
~~~

**Publication only:** `work/process-reports` report Markdown. No code, runtime, P-code, renderer, original executable, guest-state changes or replay.
