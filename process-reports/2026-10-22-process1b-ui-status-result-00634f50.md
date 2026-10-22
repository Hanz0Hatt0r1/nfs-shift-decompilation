# Process 1b — bounded retail status-result helper 0x00634F50

**Analysis:** 2026-10-22, UTC, in the assigned 12-minute bounded window following the published `0x00508C70` audit. **Original PE identity:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`, original local `/mnt/data/SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` (**independently verified by `sha256sum`**). The entire original code block was independently confirmed using GNU `objdump -D -Mintel -w --start-address=0x00634f50 --stop-address=0x00634f75 /mnt/data/SHIFT.exe`. This report performs no new replay and reads no direct callee bodies.

**Exact bounds:** first instruction `0x00634F50`, last instruction `0x00634F72: C2 04 00` occupies `0x00634F72–0x00634F74`, exclusive end `0x00634F75`; **0x25=37 bytes**, **18 instructions**, **two direct CALL instructions**, **no conditional/unconditional branches**, **one normal RET 4**. The complete original bytes, with no omitted instructions, are in Appendix A.

**Strict limits:** only `0x00634F50`, the previously established caller `0x00508DF3` and this body's two **immediate call boundaries**. No global writer/caller/vtable sweep, other callee body audit, source/runtime/P-code/renderer/guest-state modification, guest replay, native Windows/Wine run, or claims of displayed menu/race.

## 1. Exact entry ABI, register dataflow and stack cleanup

Prior bounded report on `0x00508C70` established its final invocation:

~~~asm
00508dec: 8b 4e 0c              mov    ecx,DWORD PTR [esi+0xc]
00508def: 6a 05                 push   0x5
00508df1: 8b d7                 mov    edx,edi
00508df3: e8 58 c1 12 00        call   0x634f50
00508df8: f7 d8                 neg    eax
~~~

In that caller **ESI=I** (item receiver), **EDI=I+0x120**, **Q=DWORD[I+0x0C]**. Item **I** is not original owner **O**; earlier item code reads the original owner pointer from `DWORD[I+0xE8]` on an optional traversal path. The **only explicitly supplied stack DWORD** for the present helper is **5**, pushed immediately before the CALL.

| Incoming machine component for `0x00634F50` | Proven value/source | Inside helper |
|---|---|---|
| **ECX** | **Q=DWORD[I+0x0C]** | Saved to **EDI=Q** at `0x00634F57` |
| **EDX** | **S=I+0x120** | Saved to **ESI=S** at `0x00634F55` |
| **[EBP+8]** | DWORD literal **5**, pushed by the caller at `0x00508DEF` | Loaded into EAX at `0x00634F62`, later forwarded as a pushed argument |
| **[EBP+4]** | CPU-pushed caller return address | **`0x00508DF8`** |
| **EAX initially** | No separately proven value | Overwritten at `0x00634F62`; previous callee EAX is not consumed |

The function prologue `PUSH EBP; MOV EBP,ESP; PUSH ESI; PUSH EDI` saves the frame pointer and two callee-saved registers but allocates **no explicit local buffer**. The register moves `ESI=EDX=S`, `EDI=ECX=Q` establish persistent values across both outgoing calls. There is **no write to EDI/ESI after these loads** within the original body; normally returning callees are expected to preserve them under the observed calling convention. No source-level class/type identity is derived from these register roles.

The **single epilogue** at `0x00634F6F–0x00634F74` pops EDI, ESI, EBP and executes **`RET 4`** (`C2 04 00`). This is **callee-side cleanup of precisely 4 bytes**, the **one original incoming stack argument**. There is **no caller `ADD ESP,4` after `0x00508DF3`**. `RET 4` also pops the return EIP normally; normal transfer resumes at `0x00508DF8`.

**EAX return value:** the body **does not manufacture a Boolean, compare returned EAX, branch, mask, store or normalize it**. The outgoing second call at `0x00634F6A` produces the final EAX and no subsequent instruction changes EAX. Consequently **`EAX(0x00634F50 return) = EAX(0x0065EC50 return)`** for normally returning execution. The first callee's returned EAX is **explicitly overwritten** by `MOV EAX,[EBP+8]` at `0x00634F62`, before the second call. Any callee side effects are outside this body's direct effect set.

## 2. Complete branch-free body and outgoing CALL boundaries

The original 18 instructions:

~~~asm
00634f50: 55                    push   ebp
00634f51: 8b ec                 mov    ebp,esp
00634f53: 56                    push   esi
00634f54: 57                    push   edi
00634f55: 8b f2                 mov    esi,edx
00634f57: 8b f9                 mov    edi,ecx
00634f59: 8b d7                 mov    edx,edi
00634f5b: 8b ce                 mov    ecx,esi
00634f5d: e8 4e 20 00 00        call   0x636fb0
00634f62: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00634f65: 8b 0f                 mov    ecx,DWORD PTR [edi]
00634f67: 50                    push   eax
00634f68: 8b d6                 mov    edx,esi
00634f6a: e8 e1 9c 02 00        call   0x65ec50
00634f6f: 5f                    pop    edi
00634f70: 5e                    pop    esi
00634f71: 5d                    pop    ebp
00634f72: c2 04 00              ret    0x4
~~~

**First direct CALL:** `0x00634F5D → 0x00636FB0`, return EIP **`0x00634F62`**. Immediate outgoing state:

- **ECX=S=I+0x120**, from `MOV ECX,ESI`;
- **EDX=Q=DWORD[I+0x0C]**, from `MOV EDX,EDI`;
- **zero newly pushed explicit stack arguments**. Saved EDI/ESI and upstream `[EBP+8]=5` are *not* specially pushed for this call.

The first callee may mutate memory reachable from these registers; none of its internal side effects or its cleanup/return semantics is claimed. The helper discards the **returned EAX** as a value by loading its original stack argument into EAX at `0x00634F62`.

**Inter-call instruction `0x00634F65: MOV ECX,DWORD[EDI]`** dereferences **Q** and reads its **first DWORD**. Crucially, this read takes place **after `0x00636FB0` has returned**. The code does not prove that it sees the same contents Q had at entry, since first-call side effects are not resolved. The address `DWORD[Q]` is **not automatically an original owner vptr**; no such type/equality evidence is present.

**Second direct CALL:** `0x00634F6A → 0x0065EC50`, return EIP **`0x00634F6F`**. Immediate outgoing state:

- **ECX=DWORD[Q]**, re-read at `0x00634F65` after the first call;
- **EDX=S=I+0x120**, reloaded at `0x00634F68`;
- **one explicit stack DWORD = original `[EBP+8]` = 5**, pushed at `0x00634F67`. Thus at second-callee entry `[ESP]` is return EIP `0x00634F6F`, `[ESP+4]` is 5.

There is **no `ADD ESP,4` or POP of the outgoing argument** in `0x00634F50` between this CALL and its epilogue. Under a normally returning, stack-balanced ABI, `0x0065EC50` must effectively remove/consume its pushed DWORD before returning (or otherwise provide equivalent balance). This is a **callsite inference**, **not** an independently verified `RET 4` instruction in `0x0065EC50`. Note this outgoing callee's stack cleanup is **separate** from the verified **RET 4** of `0x00634F50` that cleans its *own* inbound 5.

**Flow is unconditional:** there are no tests, comparisons, conditional jumps, loops, alternate exits or local return-value branches. Execution of the second call follows a normally returning first call, provided reads/stack accesses are valid. Externally induced faults/nonreturn do not justify inventing additional original branches.

## 3. Exhaustive direct memory reads and writes

**Explicit non-stack memory reads:** only **`0x00634F65: READ DWORD[Q]`**. Q was originally derived from **`DWORD[I+0x0C]` in the *caller***, not dereferenced from item I in the current function. This single load uses stable EDI=Q and is performed **after** the first callee. No other explicit original memory operand addresses C, item I, owner O, owner O+0x14, O+0x2D, or either vptr field.

**Explicit stack memory read:** **`0x00634F62: MOV EAX,DWORD[EBP+8]`**, one 32-bit read of the incoming value 5. The saved-register POPs, RET, CALL and PUSH instructions also access the **machine stack implicitly**, including saved EBP/ESI/EDI, return EIPs and outgoing call argument 5.

**Direct non-stack write-set: EMPTY.** The body contains **no `MOV [reg+offset],...` store**, no direct store to Q, S, I, O, any substructure, global variable or readiness field. Its stack writes are the explicit pushes of EBP/ESI/EDI, the second call's pushed DWORD 5, and the implicit return-address pushes of CALL; these are **not object-field writes**. It does not directly write item status **`DWORD[I+0xE4]`**: wrapper `0x005088AA` writes that *after* the virtual callback returns.

**No direct original-owner access:** the current function does **not even load original O**. At its caller, I+0xE8 may identify O; at this function boundary only **Q=DWORD[I+0xC]** and **S=I+0x120** are passed. Q may alias O, some other object, or be an interior pointer; **the PE does not establish such aliases**. Indirect writes by `0x00636FB0` or `0x0065EC50` through Q/S/reachable objects, and asynchronous writes elsewhere, are **unknown**. Therefore no affirmative or categorical-negative claim about all possible runtime owner mutations can be made, but the **direct** code has **no path** writing **`DWORD[O]` vptr, `DWORD[O+0x14]` count, or `BYTE[O+0x2D]` readiness byte**.

## 4. Status handoff to 0x00508C70 and finite replay evidence limits

The observed caller `0x00508C70` immediately converts this helper's EAX through:

~~~asm
00508df8: f7 d8                 neg    eax
00508dfa: 1b c0                 sbb    eax,eax
00508dfc: 83 e0 fc              and    eax,0xfffffffc
00508dff: 5f                    pop    edi
00508e00: 83 c0 05              add    eax,0x5
~~~

For **return r=0** from `0x00634F50` (hence from its second callee `0x0065EC50`), this yields **status 5**. For **r!=0**, it yields **status 1**. The status transformation is performed in **the parent callback `0x00508C70`**, **not** here. The outer wrapper `0x005088A0` stores that final status to item **`I+0xE4`**.

**v790 prior controlled P-code replay (not repeated):** one observed inner dispatch to `0x00508C70` returned EAX=5; outer helper `0x005088A0` also returned 5 for item `I=0x27DFAD78`. Given the static path to 5, this supports that `0x00634F50`, and ultimately its second callee `0x0065EC50`, returned EAX=0 in that particular normally returning inner invocation. **This is a derived implication** of the byte-proven return math plus the reported v790 inner target/result, not an independently recorded `0x0065EC50` runtime target/result event. No semantics for the zero value have been established.

**v791 prior finite guest replay (not repeated):** five outer `0x005088A0` calls yielded EAX=5, but no selected inner target EIPs were supplied for all five. Therefore do **not** attribute all five to `0x00508C70`, `0x00634F50` or `0x0065EC50`. Separately observed `DWORD[O+0x14]=9` and writer `0x005092F0` clearing `BYTE[O+0x2D]` are **not explained directly by the present branch-free helper**. Nothing here proves that a status value itself causes list-count decrement, readiness set/reset, UI appearance or a race.

**Inference boundary:** "status-result forwarding helper" describes observable return propagation, not a source method name. Q's first DWORD, the two callees' interfaces and any data they modify are not assigned speculative ownership, allocator, rendering, game state or vtable semantics. Only the caller's visible arithmetic determines the 1/5 status.

## 5. Exactly one next evidence-backed target

**`0x0065EC50` — direct second callee at `0x00634F6A`, return EIP `0x00634F6F`**, receives **ECX=DWORD[Q]**, **EDX=I+0x120**, **one pushed DWORD 5**. It is the **sole** evidence-backed next target because **its returned full EAX passes directly through `0x00634F50`**, then directly controls the parent's **status 5 versus 1** conversion. A distinct later bounded PE audit could determine only this callee's stack epilogue, direct memory effects and zero/nonzero return conditions. Its body has **not been inspected** here. There is no second next target or invitation to sweep callers/writers.

## Appendix A — complete original retail PE function, all 18 instructions and 37 bytes

~~~asm
00634f50: 55                    push   ebp
00634f51: 8b ec                 mov    ebp,esp
00634f53: 56                    push   esi
00634f54: 57                    push   edi
00634f55: 8b f2                 mov    esi,edx
00634f57: 8b f9                 mov    edi,ecx
00634f59: 8b d7                 mov    edx,edi
00634f5b: 8b ce                 mov    ecx,esi
00634f5d: e8 4e 20 00 00        call   0x636fb0
00634f62: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00634f65: 8b 0f                 mov    ecx,DWORD PTR [edi]
00634f67: 50                    push   eax
00634f68: 8b d6                 mov    edx,esi
00634f6a: e8 e1 9c 02 00        call   0x65ec50
00634f6f: 5f                    pop    edi
00634f70: 5e                    pop    esi
00634f71: 5d                    pop    ebp
00634f72: c2 04 00              ret    0x4
~~~

**Only this report is published in `work/process-reports`. No original-game files, code, runtime, P-code, renderer, guest-state or replay altered.**
