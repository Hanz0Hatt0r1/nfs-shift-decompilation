# Process 1b — bounded original-PE status result 0x0065FA60

**Date:** 2026-10-22. **Bounded audit time:** 2026-10-22, approximately 11:14–11:22 UTC. **Binary:** Need for Speed SHIFT PC retail 1.02, **original SHIFT.exe PE32 x86**, ImageBase `0x00400000`, SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**, independently **rechecked** by `sha256sum /mnt/data/SHIFT.exe` during this task. GNU `objdump -D -Mintel -w --start-address=0x0065FA60 --stop-address=0x0065FB50 /mnt/data/SHIFT.exe` matched the supplied complete original function. Full original instruction bytes are retained in Appendix A.

**Exact extent:** `0x0065FA60–0x0065FB4F` inclusive; end-exclusive `0x0065FB50`; **`0xF0 = 240 bytes`**. This report is a **new bounded, byte-level complete-body audit** of `0x0065FA60` on the established *status-chain call boundary*; it is **not** a rerun or claimed reproduction of older **v229–v239 request-path traces**, a caller/writer sweep, a callee-body decompilation or a native game execution. No source/runtime/P-code/renderer/guest-state changes or replay.

## 1. Entry from 0x0065EC50, precise ABI and return cleanup

The previously published static chain is `0x00508C70 → 0x00634F50 → 0x0065EC50 → 0x0065FA60`. The **direct incoming CALL** is `0x0065EC8A`, and its **CPU return EIP** is `0x0065EC8F`. Immediately before the CALL, the parent `0x0065EC50` has saved its ECX in EBX, passes **EDX=EBX=T**, sets **ECX=the EAX returned by `0x0065C0E0`**, and pushes **5 then S** (right-to-left argument order).

Use independent names:
- **I** = original item callback receiver. **O** = original owner, separately referenced elsewhere via an item field; O is **not** proven equal to any pointer here.
- **Q=DWORD[I+0x0C]** at the earlier callback. Its DWORD at `[Q]` was read by `0x00634F50` after `0x00636FB0`; **T=DWORD[Q]** at that earlier read (not Q itself). Parent `0x0065EC50` passes T through EBX.
- **S=I+0x120**, from the original status callback and through `0x0065EC50`.
- **P=EAX returned by `0x0065C0E0`**, the actual incoming ECX/ESI base of this function. **P, T, S, I and O are not interchangeable.** Even when a source may plausibly reference the same larger object, aliasing is unproved.

| Target-entry location | Proven value |
|---|---|
| **ECX** | **P**, return EAX from `0x0065C0E0` |
| **EDX** | **T=DWORD[Q]`**, preserved by caller in EBX |
| **[EBP+8]** | **S=I+0x120**, first stack DWORD / second PUSH |
| **[EBP+0xC]** | **5**, second stack DWORD / first PUSH |
| **[EBP+4]** | Original CALL return address **`0x0065EC8F`** |
| Incoming EAX | Not separately established as a semantic input; overwritten on first field read or selected return |

Prologue `PUSH EBP; MOV EBP,ESP; PUSH ECX; PUSH ESI; MOV ESI,ECX` yields **ESI=P**; `PUSH ECX` reserves the 32-bit local at **`[EBP−4]`**, then `0x0065FA6E` overwrites it with **T=EDX**. The function saves EBX and EDI **only after passing early guards**, so the early epilogues restore only ESI/EBP; full-path epilogues restore EDI/EBX/ESI/EBP. On all four normal exits `0x0065FA88, 0x0065FA98, 0x0065FB42, 0x0065FB4D`, the original opcode is **`RET 8`** (`C2 08 00`), which **cleans both incoming DWORD stack arguments (8 bytes)**. Caller `0x0065EC50` correctly has no `ADD ESP,8` after its CALL.

The function has **no loops**; only four conditional branches and six direct CALL sites. Source-language signatures, names, asynchronous effects, and callee-side effects are not inferred.

## 2. Exact branch precedence and return-value conditions

### 2.1 Optional first call and early return cases

~~~asm
0065fa65: 8b f1                 mov    esi,ecx
0065fa67: f6 86 cc 02 00 00 02  test   BYTE PTR [esi+0x2cc],0x2
0065fa6e: 89 55 fc              mov    DWORD PTR [ebp-0x4],edx
0065fa71: 75 05                 jne    0x65fa78
0065fa73: e8 18 fb ff ff        call   0x65f590
0065fa78: 8b 86 cc 02 00 00     mov    eax,DWORD PTR [esi+0x2cc]
0065fa7e: a8 08                 test   al,0x8
0065fa80: 74 09                 je     0x65fa8b
0065fa82: 33 c0                 xor    eax,eax
0065fa88: c2 08 00              ret    0x8
0065fa8b: a8 04                 test   al,0x4
0065fa8d: 74 0c                 je     0x65fa9b
0065fa8f: b8 08 00 00 00        mov    eax,0x8
0065fa98: c2 08 00              ret    0x8
~~~

- Initial **READ BYTE[P+0x2CC], mask 0x02**. **If bit 1 is clear** (~0x65FA71 JNE~ not taken), execute **CALL `0x0065F590`**. **If bit 1 set**, skip that call. `MOV [EBP−4],EDX` between TEST and JNE does **not alter flags**.
- **Re-read full DWORD[P+0x2CC] at `0x0065FA78`** after the optional call. Therefore the next two branch conditions apply to the **post-`0x0065F590` field value**, not necessarily its earlier byte test; nested callee could change state, unknown.
- If **bit 3 (0x08) is set**, `XOR EAX,EAX` and **early `RET 8` returning 0**. This check **has priority** over the subsequent 0x04 test, even if both bits are set.
- If **bit 3 clear and bit 2 (0x04) set**, direct **`MOV EAX,8; RET 8`**.
- If **both bit 3 and bit 2 clear**, enter main path at `0x0065FA9B`. Neither early path contains any **direct non-stack writes** to P, S, I or O; possible prior call effects are unknown.

### 2.2 Main-path flag computation and first two explicit field writes

~~~asm
0065fa9b: 53                    push   ebx
0065fa9c: 8b 5d 0c              mov    ebx,DWORD PTR [ebp+0xc]
0065fa9f: 8b cb                 mov    ecx,ebx
0065faa1: d1 e9                 shr    ecx,1
0065faa3: 83 e1 01              and    ecx,0x1
0065faa6: 03 c9                 add    ecx,ecx
0065faa8: 0f b6 d3              movzx  edx,bl
0065faab: 83 e2 01              and    edx,0x1
0065faae: 0b ca                 or     ecx,edx
0065fab0: c1 e1 04              shl    ecx,0x4
0065fab3: 83 e0 cf              and    eax,0xffffffcf
0065fab6: 0b c8                 or     ecx,eax
0065fab8: 57                    push   edi
0065fab9: 83 c9 04              or     ecx,0x4
0065fabc: 89 8e cc 02 00 00     mov    DWORD PTR [esi+0x2cc],ecx
0065fac2: 8d 7e 64              lea    edi,[esi+0x64]
0065fac5: 6a 00                 push   0x0
0065fac7: 8d 56 08              lea    edx,[esi+0x8]
0065faca: 8b cf                 mov    ecx,edi
0065facc: c7 86 34 01 00 00 00 00 00 00  mov DWORD PTR [esi+0x134],0
0065fad6: e8 65 36 ff ff        call   0x653140
~~~

Let **F=DWORD[P+0x2CC]** from `0x0065FA78` after optional prior call, and **B=DWORD[EBP+0xC]**. From SHR/AND/ADD/MOVZX/OR/SHL, the extracted 2-bit value is **`(B & 3) << 4`**. `AND EAX,0xFFFFFFCF` clears bits represented by mask 0x30 (bit 4/5), then ORs in the extracted value and sets bit 2 (0x04). **Exact main-path store:**

`DWORD[P+0x2CC] = (F & 0xFFFFFFCF) | ((B & 3) << 4) | 0x04`.

For this **status-chain invocation B=5**: `B&3=1`, so the exact main-path result immediately after this store is **`(F & 0xFFFFFFCF) | 0x14`**. It **sets bits 0x10 and 0x04**, **clears bit 0x20**, and preserves other F bits at that moment. No source-language meaning is assigned to any bit.

Next **`LEA EDI,P+0x64`** computes a subobject pointer; **`LEA EDX,P+8`** computes another; neither dereferences memory. `PUSH 0` prepares one outgoing stack DWORD for `0x00653140`. The second unconditional direct store **`DWORD[P+0x134]=0`** at `0x0065FACC` occurs before that call.

### 2.3 Middle calls and precise stack order

- `0x0065FAD6 → 0x00653140` uses **ECX=P+0x64**, **EDX=P+8**, **one stack arg 0**; return EIP **`0x0065FADB`**. No subsequent local `ADD ESP,4`: stack balance on normal return implies effective callee cleanup or equivalent (literal callee RET opcode **not** inspected).
- `0x0065FAE3 → 0x00652190` uses **ECX=P+0x64**, **EDX=P+0x200**; **no new pushed args**; return EIP **`0x0065FAE8`**.
- `0x0065FAE8` reads incoming **S=DWORD[EBP+8]**, and `0x0065FAEB` reads saved **T=DWORD[EBP−4]**; `0x0065FAEE–0x0065FAF2` pushes values **1, B=5, S, P** in that order. **`CALL 0x0066CC00`** at `0x0065FAF9` gets **ECX=P+0x200**, **EDX=T**, and four stack arguments **in callee order first=P, second=S, third=5, fourth=1**. Return EIP **`0x0065FAFE`**. There is no local `ADD ESP,0x10`, so a normally balanced path requires effective 16-byte callee cleanup/equivalent; exact nested callee epilogue unknown. **This function does not TEST, CMP or use the returned EAX from `0x0066CC00`**: it proceeds to a new independent direct call.
- `0x0065FAFE–0x0065FB07` pushes **0x005B0D50, 0, 0, 0** in that order. It then sets **EDX=0**, **ECX=P+0x64**, and `CALL 0x00653480` at `0x0065FB0D`, return EIP **`0x0065FB12`**. Its four outgoing stack args **in callee order first=0, second=0, third=0, fourth=0x005B0D50**. Again **no caller ADD ESP,0x10**; normally returning balanced ABI requires effective callee/equivalent cleanup (actual epilogue not inspected).
- **`0x0065FB12: MOV EDI,EAX`** captures the **full 32-bit return from `0x00653480`**. `TEST EDI,EDI` at `0x0065FB14` is the only main-path decision about downstream results. **If EDI==0**, branch to `0x0065FB45`, return EAX=0. **If EDI!=0**, take the `0x0065FB18` side path. No inference about callee's return type/handle validity is warranted.

### 2.4 Nonzero returned EAX path and final status 3

~~~asm
0065fb12: 8b f8                 mov    edi,eax
0065fb14: 85 ff                 test   edi,edi
0065fb16: 74 2d                 je     0x65fb45
0065fb18: 8b 4e 70              mov    ecx,DWORD PTR [esi+0x70]
0065fb1b: 57                    push   edi
0065fb1c: 51                    push   ecx
0065fb1d: 68 50 01 af 00        push   0xaf0150
0065fb22: e8 c9 42 29 00        call   0x8f3df0
0065fb27: 83 c4 0c              add    esp,0xc
0065fb2a: 83 a6 cc 02 00 00 f3  and    DWORD PTR [esi+0x2cc],0xfffffff3
0065fb31: 89 be 34 01 00 00     mov    DWORD PTR [esi+0x134],edi
0065fb39: b8 03 00 00 00        mov    eax,0x3
0065fb42: c2 08 00              ret    0x8
0065fb45: 5f                    pop    edi
0065fb46: 5b                    pop    ebx
0065fb47: 33 c0                 xor    eax,eax
0065fb4d: c2 08 00              ret    0x8
~~~

For **nonzero EDI**, the code **READ DWORD[P+0x70]**, pushes **EDI, that field, 0x00AF0150**, then calls `0x008F3DF0` at `0x0065FB22` with **callee-order stack arguments first=0x00AF0150, second=DWORD[P+0x70], third=EDI**. Return EIP **`0x0065FB27`**. **`ADD ESP,0xC` is explicit 12-byte caller-side cleanup**, unlike other outgoing calls. ECX is the loaded `DWORD[P+0x70]` at this call boundary; EDX is not reinitialized since the `0x00653480` call and is unknown from local evidence.

After this call **the returned EAX is not tested**. It performs **READ-MODIFY-WRITE DWORD[P+0x2CC] &= 0xFFFFFFF3**, clearing bits 0x04 and 0x08 of whatever the field contains **at this later time**; it then **WRITE DWORD[P+0x134]=EDI** (the previously nonzero result of `0x00653480`), restores saved registers, forces **EAX=3**, and **RET 8**. Nested calls might have changed the field in between; do not assert its current full value equals the earlier formula without extra evidence.

For **zero EAX returned from `0x00653480`**, `0x0065FB16 JE` jumps straight to `0x0065FB45`; restore saved registers, **XOR EAX,EAX**, **RET 8**. This returns **0** after the **earlier** unconditional direct writes to P+0x2CC and P+0x134; it does **not** reach the late AND/store, and those effects must not be attributed to this zero branch.

**Complete normal EAX outcomes:**

| Branch at original PE | Direct EAX at return |
|---|---|
| Post-optional-call `DWORD[P+0x2CC] & 0x08 !=0` | **0**, early |
| bit 0x08 clear; `DWORD[P+0x2CC] & 0x04 !=0` | **8**, early |
| both tested bits clear; `EAX(0x00653480)==0` | **0**, full path |
| both bits clear; `EAX(0x00653480)!=0` | **3**, full path |

**Precisely two ways to return zero** on normal execution: early 0x08-bit branch, or the full path with zero from `0x00653480`. The main-path zero/nonzero decision is **not** based on `0x0066CC00`'s return. In the higher status callback `0x00508C70`, these **zero results** become **status 5**, whereas **3 or 8** become **status 1**. This is a **static implication only** for a specific dynamic call chain actually selecting that callback, not a claim that any earlier v229–v239 or v790 event took one of these paths.

## 3. Exhaustive direct memory reads and writes of this complete body

**All explicit P-relative object accesses:**

| EIP | Direct memory operand and width | Condition |
|---|---|---|
| `0x0065FA67` | **READ BYTE[P+0x2CC]**, TEST 0x02 | Always, before optional `0x0065F590` |
| `0x0065FA78` | **READ DWORD[P+0x2CC]** into EAX | Always on normal continuation after optional call |
| `0x0065FABC` | **WRITE DWORD[P+0x2CC]** = bit-combined F/B as above | Main path only |
| `0x0065FACC` | **WRITE DWORD[P+0x134]=0** | Main path only, before `0x00653140` |
| `0x0065FB18` | **READ DWORD[P+0x70]** | Main path only if `0x00653480` EAX!=0 |
| `0x0065FB2A` | **READ-MODIFY-WRITE DWORD[P+0x2CC] &=0xFFFFFFF3** | Main path only if captured EAX!=0 |
| `0x0065FB31` | **WRITE DWORD[P+0x134]=captured nonzero EAX of 0x00653480` | Main path only if captured EAX!=0 |

**This is the *entire* direct non-stack write-set:** P+0x2CC and P+0x134 only. No explicit store to P+0x70, P+0x200, P+0x64 or P+8. `LEA EDI,[P+0x64]`, `LEA EDX,[P+8]` and `LEA EDX,[P+0x200]` and `LEA ECX,[P+0x200]` derive pointers **without directly reading or writing** memory at those addresses.

**Stack memory:** `0x0065FA6E: WRITE DWORD[EBP−4]=incoming T`; `0x0065FA9C: READ DWORD[EBP+0xC]=B=5`; `0x0065FAE8: READ DWORD[EBP+8]=S`; `0x0065FAEB: READ DWORD[EBP−4]=T`. Prologue `PUSH ECX` initializes the same local slot before its overwrite. Register save/restore, PUSH arguments, CALL return-address writes, POP and RET read/write the **machine stack implicitly**, not the item/owner object fields.

**No direct access to original O or item I by their pointer bases:** in this function **P** is the result of `0x0065C0E0`, **S=I+0x120** and **T=DWORD[Q]`. Neither P=S nor P=I nor P=O is proven; do **not** equate `DWORD[P+0x2CC]` or `DWORD[P+0x134]` with any original item `DWORD[I+offset]` or owner `DWORD[O+offset]`. No instruction directly dereferences **`DWORD[O]` vptr, `DWORD[O+0x14]` insertion count, or `BYTE[O+0x2D]` readiness**. Nor does this body directly access item I vptr or `DWORD[I+0xE4]`. Alias/reachable graph writes by callees, including optional `0x0065F590` and the five other calls, are **unknown**; the bounded body-level audit is not proof that full execution has no side effects.

## 4. Every direct outgoing CALL boundary — exactly six

These are **all** outgoing CALL instructions in the original 240-byte function. Return EIP is the next original instruction. Explicit PUSH argument order is shown as **callee sees them**, not assembly push order.

| CALL site → target | Return EIP | Proven ECX, EDX and freshly pushed stack arguments |
|---|---|---|
| `0x0065FA73 → 0x0065F590` | `0x0065FA78` | Only if BYTE[P+0x2CC] bit 0x02 **clear**; **ECX=P**, **EDX=T** (prior local store did not change EDX), **0 pushed** |
| `0x0065FAD6 → 0x00653140` | `0x0065FADB` | **ECX=P+0x64**, **EDX=P+8**, **1 stack arg=0**; main path |
| `0x0065FAE3 → 0x00652190` | `0x0065FAE8` | **ECX=P+0x64**, **EDX=P+0x200**, **0 newly pushed** |
| `0x0065FAF9 → 0x0066CC00` | `0x0065FAFE` | **ECX=P+0x200**, **EDX=T**, **4 args: P, S, 5, 1** in callee order; B=5 from [EBP+0xC] |
| `0x0065FB0D → 0x00653480` | `0x0065FB12` | **ECX=P+0x64**, **EDX=0** (full XOR), **4 args: 0, 0, 0, 0x005B0D50** |
| `0x0065FB22 → 0x008F3DF0` | `0x0065FB27` | **ECX=DWORD[P+0x70]**, **EDX unknown** since preceding callee, **3 args: 0x00AF0150, DWORD[P+0x70], EDI (nonzero EAX of 0x00653480)**; **ADD ESP,0xC** does *caller* cleanup |

The outgoing calls with one or four explicit pushed DWORDs and **no local `ADD ESP`** require callee/equivalent stack balancing on normal return (**4 or 16 bytes**, respectively); the actual nested callee RET opcode is **not inspected**. By contrast, `0x008F3DF0` has **explicit caller-side cleanup of 12 bytes**. `0x0065FA60` itself verifies **RET 8** to clean its own two original incoming arguments. The status flags and candidate receiver P are byte-derived, but no callee implementation is given a source-level semantic name.

## 5. New static findings vs older request-path traces; limits

**Newly established by this full-body status-chain analysis:** exact receiver P/T/S/B provenance from `0x0065EC50`, exact bit precedence and **all normal result classes {0,3,8}**, exact flag formula when B=5, two precisely different zero-return paths, both direct P-relative field writes and conditional late RMW/write, six complete immediate call/return/stack boundaries, and the observation that **`0x0066CC00`'s EAX is not directly inspected before the `0x00653480` call**. None of these findings requires a new replay or a global search.

**Existing earlier finite v229–v239 *request-path* probes (not reproduced here):** already reported a direct call sequence involving `0x00653140, 0x00652190, 0x0066CC00, 0x00653480`; selected captured `0x0066CC00` returned `0x00010000` and selected `0x00653480` returned zero. Those are **different probe contexts at the guest host-frame loop**, `guest_draw_translation=false`. They do not independently prove **the `0x0065EC50 → 0x0065FA60` callback route was reached**, or that `0x0065FA60` produced the observed v790 status 5. For *a hypothetical matching straight-line invocation* in which `0x00653480` returns zero and early flags allow continuation, this body would return zero, but that is **conditional static reasoning**, not a verified status-5 event.

**Earlier v790/v791 status observations (separate):** v790 one documented internal virtual call to `0x00508C70` returned 5; v791 five outer `0x005088A0` calls returned 5 without recording all nested targets. The direct EAX chain makes a zero return from some nested path necessary for the **specific verified `0x00508C70` invocation**, but it does **not establish whether that one took the early 0x08 guard or this full path, nor that all five v791 queries selected the same callback**. The separate O+0x14=9 and O+0x2D=0 observations do not acquire a causal explanation from this function's stores.

**Uncertainty:** pointers P/S/T/Q/I/O may alias, and direct callees might change reachable memory or terminate abnormally. No write to original owner vptr, count or readiness can be attributed **directly** to this body, and no absence of indirect effects is proven. No claim of active Windows/Wine game state, displayed UI, menu/race, or native GPU draw translation is made.

**Bounded conclusion:** the body optionally invokes an initial helper, branches on two bits of P+0x2CC, and either immediately returns **0** or **8**, or initializes P-relative state, calls several helpers, and returns **0 iff `0x00653480` returned zero** on the full path, otherwise **3** after a diagnostic call and final P-field stores. On this status chain, **only return zero could become status 5** upstream. The original owner O+0x14/O+0x2D changes remain **unproven** by the direct memory instructions and this finite evidence.

## 6. Exactly one evidence-backed next target

**`0x00653480`**, the immediate direct callee at **`0x0065FB0D`**, return EIP **`0x0065FB12`**, with **ECX=P+0x64**, **EDX=0**, **four stack DWORDs (first 0, second 0, third 0, fourth 0x005B0D50)**. It is the **single** bounded next target most directly supported because its **EAX==0 versus !=0** determines the full-path **0 versus 3**, and its zero result was **previously observed only in a separate request-path probe**, not in the documented status-query event. A **new, separately assigned** narrow original-PE body audit could investigate its stack cleanup, direct write-set and zero/nonzero return conditions; its implementation is deliberately **not** studied in this report. No other target is proposed.

## Appendix A — full original PE objdump, 0x0065FA60–0x0065FB4F inclusive (240 bytes)

~~~asm
0065fa60: 55                    push   ebp
0065fa61: 8b ec                 mov    ebp,esp
0065fa63: 51                    push   ecx
0065fa64: 56                    push   esi
0065fa65: 8b f1                 mov    esi,ecx
0065fa67: f6 86 cc 02 00 00 02  test   BYTE PTR [esi+0x2cc],0x2
0065fa6e: 89 55 fc              mov    DWORD PTR [ebp-0x4],edx
0065fa71: 75 05                 jne    0x65fa78
0065fa73: e8 18 fb ff ff        call   0x65f590
0065fa78: 8b 86 cc 02 00 00     mov    eax,DWORD PTR [esi+0x2cc]
0065fa7e: a8 08                 test   al,0x8
0065fa80: 74 09                 je     0x65fa8b
0065fa82: 33 c0                 xor    eax,eax
0065fa84: 5e                    pop    esi
0065fa85: 8b e5                 mov    esp,ebp
0065fa87: 5d                    pop    ebp
0065fa88: c2 08 00              ret    0x8
0065fa8b: a8 04                 test   al,0x4
0065fa8d: 74 0c                 je     0x65fa9b
0065fa8f: b8 08 00 00 00        mov    eax,0x8
0065fa94: 5e                    pop    esi
0065fa95: 8b e5                 mov    esp,ebp
0065fa97: 5d                    pop    ebp
0065fa98: c2 08 00              ret    0x8
0065fa9b: 53                    push   ebx
0065fa9c: 8b 5d 0c              mov    ebx,DWORD PTR [ebp+0xc]
0065fa9f: 8b cb                 mov    ecx,ebx
0065faa1: d1 e9                 shr    ecx,1
0065faa3: 83 e1 01              and    ecx,0x1
0065faa6: 03 c9                 add    ecx,ecx
0065faa8: 0f b6 d3              movzx  edx,bl
0065faab: 83 e2 01              and    edx,0x1
0065faae: 0b ca                 or     ecx,edx
0065fab0: c1 e1 04              shl    ecx,0x4
0065fab3: 83 e0 cf              and    eax,0xffffffcf
0065fab6: 0b c8                 or     ecx,eax
0065fab8: 57                    push   edi
0065fab9: 83 c9 04              or     ecx,0x4
0065fabc: 89 8e cc 02 00 00     mov    DWORD PTR [esi+0x2cc],ecx
0065fac2: 8d 7e 64              lea    edi,[esi+0x64]
0065fac5: 6a 00                 push   0x0
0065fac7: 8d 56 08              lea    edx,[esi+0x8]
0065faca: 8b cf                 mov    ecx,edi
0065facc: c7 86 34 01 00 00 00 00 00 00  mov DWORD PTR [esi+0x134],0x0
0065fad6: e8 65 36 ff ff        call   0x653140
0065fadb: 8d 96 00 02 00 00     lea    edx,[esi+0x200]
0065fae1: 8b cf                 mov    ecx,edi
0065fae3: e8 a8 26 ff ff        call   0x652190
0065fae8: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0065faeb: 8b 55 fc              mov    edx,DWORD PTR [ebp-0x4]
0065faee: 6a 01                 push   0x1
0065faf0: 53                    push   ebx
0065faf1: 50                    push   eax
0065faf2: 56                    push   esi
0065faf3: 8d 8e 00 02 00 00     lea    ecx,[esi+0x200]
0065faf9: e8 02 d1 00 00        call   0x66cc00
0065fafe: 68 50 0d 5b 00        push   0x5b0d50
0065fb03: 6a 00                 push   0x0
0065fb05: 6a 00                 push   0x0
0065fb07: 6a 00                 push   0x0
0065fb09: 33 d2                 xor    edx,edx
0065fb0b: 8b cf                 mov    ecx,edi
0065fb0d: e8 6e 39 ff ff        call   0x653480
0065fb12: 8b f8                 mov    edi,eax
0065fb14: 85 ff                 test   edi,edi
0065fb16: 74 2d                 je     0x65fb45
0065fb18: 8b 4e 70              mov    ecx,DWORD PTR [esi+0x70]
0065fb1b: 57                    push   edi
0065fb1c: 51                    push   ecx
0065fb1d: 68 50 01 af 00        push   0xaf0150
0065fb22: e8 c9 42 29 00        call   0x8f3df0
0065fb27: 83 c4 0c              add    esp,0xc
0065fb2a: 83 a6 cc 02 00 00 f3  and    DWORD PTR [esi+0x2cc],0xfffffff3
0065fb31: 89 be 34 01 00 00     mov    DWORD PTR [esi+0x134],edi
0065fb37: 5f                    pop    edi
0065fb38: 5b                    pop    ebx
0065fb39: b8 03 00 00 00        mov    eax,0x3
0065fb3e: 5e                    pop    esi
0065fb3f: 8b e5                 mov    esp,ebp
0065fb41: 5d                    pop    ebp
0065fb42: c2 08 00              ret    0x8
0065fb45: 5f                    pop    edi
0065fb46: 5b                    pop    ebx
0065fb47: 33 c0                 xor    eax,eax
0065fb49: 5e                    pop    esi
0065fb4a: 8b e5                 mov    esp,ebp
0065fb4c: 5d                    pop    ebp
0065fb4d: c2 08 00              ret    0x8
~~~

Report-only, branch `work/process-reports`; no code, P-code, runtime, renderer, guest-state changes, or replay.
