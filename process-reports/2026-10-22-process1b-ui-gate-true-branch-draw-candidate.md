# Process 1 — retail UI gate true branch and candidate draw path at 0x0054BE00

**Report date:** 2026-10-22  
**PE:** Need for Speed Shift PC retail 1.02, PE32 x86, ImageBase `0x00400000`.  
**SHA-256 of supplied original `SHIFT.exe`, independently verified:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Primary sources:** Original `SHIFT.exe`; uploaded `SHIFT_objdump_full.txt`; exact user-provided v751 controlled P-code replay evidence and referenced v120 common-tail observation. Static vtable addresses were read from original PE `.rdata`. **No execution of retail binary in this analysis; no modifications to runtime, P-code, renderer, graphics, source or gates.** The separately stopped parent callback setter assignment was not resumed.

## Conclusion

**The conditional block `0x0054BE85–0x0054BEC6` is genuinely bypassed when `0x0050CEB0` returns zero.** The branch is `TEST EAX,EAX; JE 0x0054BEC8` at `0x0054BE81–0x0054BE83`. Zero is the *false-branch* of this gate; it is not an immediate return from the containing `0x0054BE00` function.

If the first gate is true, the function invokes `0x00545DC0(0)` on a singleton, then optionally obtains a nested device object via `vtable+0x10C`, checks that object's primary virtual slot 0, and calls the nested object's `vtable+0x58` with `EDX=0` and one pushed DWORD 0. These are **additional conditional state/render-related method calls**, not a directly proven guest D3D9 DrawPrimitive/DrawIndexedPrimitive/DrawUP submission.

In the normal constructor-generated class arrangement, we could actually resolve both levels of virtual dispatch beyond mere matching offsets: **`[0x00C26058]` stores an object with vptr `0x00B18D38`**, whose `+0x10C` slot points to `0x0082DB30`; that getter returns **`[wrapper+0x5F4]`**. Constructor `0x008323D0` creates that nested object via `0x00850190` and stores it at `[wrapper+0x5F4]`; its vptr is **`0x00B1BD88`**. The nested slot **0 points to `0x006A7300`** (reads `BYTE [child+5]`) and nested slot **+0x58 points to `0x00852760`**. These addresses are static class/construction evidence. **The v751 P-code trace did not independently capture current wrapper and child vptrs**, so treat them as the resolved *ordinary retail object* path, not forced runtime values.

The `0x00852760` body contains indirect graphics-interface operations and further call chains. This establishes a **plausible render-submission frontier** but not actual Draw* invocation. Independently provided v751 trace reports no observed guest Draw* calls or translation. The two are consistent; neither one establishes a global cause of missing rendering/UI.

## 1. ABI and pointer provenance

At `0x0054BE00`, `ECX=outer owner` (copied to **EDI**). ESI is **`DWORD [0x00C26058]`**, a separate global device/wrapper object; do not equate these. EBX saves EAX from `[ESI.vptr+0x11C]` and is later provided as EDX to wrapper calls `+0x138` and `+0x13C`. The function preserves EBX, ESI, EDI, takes no explicit stack parameters and ends `RET` at **0x0054BEF1**; EAX is not a normalized Boolean return here.

Before this function's gate, exact retail calls are:
- `ESI.vptr+0x11C` at `0x0054BE15`, whose result is saved in EBX;
- `ESI.vptr+0x12C` at `0x0054BE23`;
- `ESI.vptr+0x138` at `0x0054BE40`, with `EDX=EBX`, five explicit stack DWORD arguments, including owner field `[EDI+0x1EE0]`;
- `ESI.vptr+0x144` at `0x0054BE58`, with `EDX=[EDI+0x1EE0]`, one stack DWORD 0;
- direct `0x00427770(ECX=EDI+0x1EEC)` at `0x0054BE60`;
- direct `0x00894B60` then `0x00894AE0(ECX=returned EAX)` at `0x0054BE65` and `0x0054BE6C`;
- direct singleton `0x00545D90` at `0x0054BE71`, then `ECX=EAX+0x108` into `0x0050CEB0` at **0x0054BE7C**.

`0x00545D90` has a first-call initialization branch gated by `[0x00BE2560]&1`, invoking `0x00545CA0` and register/dtor helper `0x00900FB3` when needed; in all normal outcomes it returns constant **`EAX=0x00BE23F8`** at `0x00545DBA`. Thus `EAX+0x108 = 0x00BE2500`, matching the supplied v751 gate ECX. These are **not** accesses to the outer EDI or ESI device object.

## 2. Exact two-branch control flow: 0x0054BE7C–0x0054BEC8

| Retail site | Exact condition / operation | Next control-flow edge |
|---|---|---|
| **0x0054BE7C** | `0x0050CEB0(ECX=0x00BE2500)` in ordinary singleton path | EAX examined at `0x0054BE81` |
| **0x0054BE81–0x0054BE83** | `TEST EAX,EAX; JE` | **EAX==0 → 0x0054BEC8** directly, skipping 0x0054BE85–0x0054BEC6 |
| **0x0054BE85–0x0054BE8E** | push 0, `0x00545D90()`, ECX=singleton, `0x00545DC0(singleton, 0)` | test EAX |
| **0x0054BE93–0x0054BE95** | `TEST EAX,EAX; JNE` | **0x00545DC0 returned nonzero → 0x0054BEC8** |
| **0x0054BE97–0x0054BEA1** | `ESI.vptr+0x10C` called once with ECX=ESI | EAX becomes *nested object pointer* |
| **0x0054BEA3–0x0054BEA9** | `nested.vptr+0` with ECX=nested | its **AL** is tested |
| **0x0054BEAB–0x0054BEAD** | `TEST AL,AL; JE` | AL==0 → `0x0054BEC8` |
| **0x0054BEAF–0x0054BEC6** | `ESI.vptr+0x10C` invoked **again**, then `nested.vptr+0x58` with ECX=nested, EDX=0, stack [0] | fallthrough `0x0054BEC8` regardless of result |
| **0x0054BEC8** | common tail, called from *every* path | `ESI.vptr+0x13C` at `0x0054BEDA`; `ESI.vptr+0x130` at `0x0054BEEC` |

The second `+0x10C` getter call is real and cannot be optimized away when describing retail side effects; no local caching of its first result occurs. A callback could in principle change the nested object between these calls, although no such mutation was proved for v751.

**Condition to reach the final nested `+0x58` call**:

```text
return(0x0050CEB0(singleton+0x108)) != 0
AND return(0x00545DC0(singleton, 0)) == 0
AND lowbyte(return(nested.vptr[0](nested))) != 0
=> second nested getter, then nested.vptr[0x58/4](nested, EDX=0, stackDWORD=0)
```

The code contains **no null check** on the pointer returned by wrapper `+0x10C` before dereferencing `[EAX]`; this is a static requirement for safe execution of that branch, **not evidence that a non-null pointer existed in v751**.

**`0x00545DC0` is a larger procedure, not a direct Draw import.** Its exact entry `0x00545DDD–0x00545DEA` checks `0x0050CEB0(ECX=singleton+0x108)` again. If that gate fails, it returns zero via `0x00545F56`. For a nonzero gate it follows additional conditional wrapper/nested calls, `0x0050CD80` and `0x0050CDB0`; ordinary successful paths return AL=1 at `0x00545F46`. Its return-zero path is necessary (but not sufficient) to continue through the caller's second set of virtual calls. There is no evidence that `0x00545DC0` was even entered during v751 because the *outer* gate was always zero.

## 3. Two-level retail vtable resolution: no offset-only guess

### Wrapper from 0x00C26058

`0x00823CF0` allocates `0x3970` bytes, calls `0x008323D0` at `0x00823D0A`, then at `0x00823D15–0x00823D1A` stores returned EAX to **both** `[0x00C26054]` and `[0x00C26058]` (zero if allocation failed). Constructor at `0x008323EB`: `DWORD [wrapper] = 0x00B18D38` (and `[wrapper+4]=0x00B18D14` — a separate secondary vptr, *not* primary `+4` slot).

The original .rdata DWORDs are:

| Memory address (0x00B18D38 + offset) | DWORD value | Relevance |
|---|---|---|
| **0x00B18E44** (primary **+0x10C**) | **0x0082DB30** | `0x0082DB30: mov eax,[ecx+0x5f4]; ret` |
| 0x00B18E54 (+0x11C) | 0x0082DB70 | wrapper pre-gate virtual getter |
| 0x00B18E64 (+0x12C) | 0x0082F710 | pre-gate virtual method |
| 0x00B18E68 (+0x130) | 0x00835D80 | one common-tail method |
| 0x00B18E70 (+0x138) | 0x0082F780 | pre-gate method |
| 0x00B18E74 (+0x13C) | 0x00833670 | one common-tail method |
| 0x00B18E7C (+0x144) | 0x0082DBC0 | pre-gate method |

These specific DWORDs come from the PE image, not from guesses based on the offsets. In particular, user-supplied independent v120/v751 runtime analysis resolves the common-tail calls through `+0x13C / +0x130` to D3D9 EndScene/Present respectively; this report retains that **runtime-observed** classification rather than treating vtable-slot order alone as sufficient.

### Nested object from wrapper+0x5F4

In `0x008323D0`, the code at **0x00832802–0x00832823** allocates `0xDC` bytes, calls `0x00850190` at `0x00832815`, then `0x00832823: mov [esi+0x5f4],eax`. `0x00850190` writes **`DWORD [nested]=0x00B1BD88`** at `0x00850244`; it also initializes `BYTE [nested+5]=0` at `0x008501AF`. Therefore for the standard constructed nested object:

| Memory address | DWORD | Proven implementation |
|---|---|---|
| 0x00B1BD88 (+0) | 0x006A7300 | `mov al,BYTE [ecx+5]; ret` |
| **0x00B1BDE0 (+0x58)** | **0x00852760** | state/render-oriented routine, `ret 4` |

The boolean slot test at 0x0054BEA9 is therefore (for this concrete vptr) **the byte field `nested+5`**; it is not by itself a GPU command. The final virtual call at 0x0054BEC6 resolves, under this ordinary vptr assumption, to `0x00852760(nested, EDX=0, [ESP+4]=0)`.

## 4. Does the bypassed block issue a proven Draw* command?

**No direct guest Draw/DrawUP import call or resolved Draw* COM method is present among the executable instructions at 0x0054BE85–0x0054BEC6.** Its *direct* executable call targets are exactly **0x00545D90**, **0x00545DC0**; all other calls within that interval use virtual method pointers loaded at wrapper/nested offsets listed above. It is **not** valid to extrapolate "the block performs DrawPrimitive" from any one vtable offset.

The nested implementation `0x00852760` makes this path a **credible deferred graphics setup/submission candidate**, not a proven draw: its retail code sets `BYTE [nested+9]=1` at 0x00852774, tests `DWORD [nested+0x98]` and `BYTE [nested+6]` at 0x0085277D/0x00852795, can return before deeper work, and on an enabled path calls `0x0082C050`, `0x0082A660`, `0x0082C0B0`, `0x0082E110`, `0x0082E510`, `0x00850F10`, `0x00851730`, `0x008521F0`, `0x00852FF0` plus indirect device/interface methods. The *complete transitive draw-import provenance* through these nested methods has **not** been proven by this bounded analysis; do not assert the absence of any Draw* in all their descendants. This assignment specifically excludes renderer implementation changes.

Even if `0x00852760` is entered, reaching a particular inner graphics call additionally depends on `[nested+0x98]`, `[nested+6]` and further return values. Thus **"the optional block was entered"**, **"the nested +0x58 call occurred"**, **"graphics-state routines ran"**, and **"D3D9 Draw* import was called"** are four distinct propositions.

## 5. What v751 and v120 actually establish

**User-supplied controlled v751**: original retail PE executed under Linux recompilation/P-code guest runtime (not Windows/Wine); bounded 120 host frames; 594 calls to `0x0050CEB0`, all returned **EAX=0**, every caller `0x0054BE00`; no observed guest Draw* calls/translation; no runtime blocker. Evidence path `evidence/retail_frontier_20261022/process1_ui_callback_pointer_provenance_v751.json`. Therefore on these **observed calls**, the branch at 0x0054BE83 jumps directly to 0x0054BEC8. Do not infer from this a global inability to render or any cause not present in the trace.

**User-supplied independent v120**: `evidence/retail_frontier_20261019/ui_gate_common_tail_dispatch.json` identifies the two post-gate virtual calls as D3D9 EndScene/Present in the measured path. The original bytes show **both** calls remain on the false-gate path. Their presence does **not** prove a drawing submission occurred in the same frame; EndScene/Present can be reached after no observed guest Draw*.

**Inference bounded to this frame path:** v751 did not take the 0x0054BE85–0x0054BEC6 optional branch in the 594 measured gate checks. The absent Draw* observation is *consistent with* an absent optional branch, but a **causal claim** that its bypass is *why* no Draw* occurred requires additional transitive/render evidence and is not made here.

## 6. Confidence ledger and exactly one next target

**PE-byte proven:** identity hash; complete call/Jcc structure of 0x0054BE00; double gating; exact local ECX/EDX/stack argument flows; pre-gate/common-tail execution on both branches; standard wrapper+child constructor chain, both vptr constants and corresponding .rdata slots; `0x0082DB30` returns `[wrapper+0x5F4]`; `0x006A7300` reads `nested+5`; `0x00852760` is the standard nested `+0x58` implementation and itself conditionally invokes further routines.

**Directly supplied runtime observations (not rerun):** v751: 594 false gate checks, common-tail method observations, no guest Draw* / translation; v120: independent EndScene/Present common-tail verification. Runtime vptr values of nested objects and transitive GPU import mapping were not provided.

**Unknown/hypothesis:** whether state bytes/pointers can later enable the true branch; whether/when 0x00545DC0 returns zero following a true outer gate; exact rendering semantics of each transitive nested call; evidence of a guest Draw* import in this optional subtree; connection to any global UI menu failure. No field forcing, patches or renderer edits proposed.

**One next bounded trace/retail target: `0x00852760`.** This is the actually resolved nested `+0x58` implementation for the ordinary retail object. When observed, record callsite, ECX, vptr, entry values `[ECX+0x5]`, `[ECX+0x6]`, `[ECX+0x98]`, return AL and which device/interface calls execute, together with separately captured Draw* import events. If the target is never reached within a bounded run, report only that negative observation. This is a read-only observation, *not* an instruction to force gate/state.

## 7. Full original retail executable objdump: 0x0054BE00–0x0054BEF1

The complete function below is kept unabridged, with machine bytes, exactly one executable block `0x0054BE00–0x0054BEF1`. No jump-table data is implied.

```asm
0054be00: 53                    push   ebx
0054be01: 56                    push   esi
0054be02: 8b 35 58 60 c2 00     mov    esi,DWORD PTR ds:0xc26058
0054be08: 8b 06                 mov    eax,DWORD PTR [esi]
0054be0a: 8b 90 1c 01 00 00     mov    edx,DWORD PTR [eax+0x11c]
0054be10: 57                    push   edi
0054be11: 8b f9                 mov    edi,ecx
0054be13: 8b ce                 mov    ecx,esi
0054be15: ff d2                 call   edx
0054be17: 8b d8                 mov    ebx,eax
0054be19: 8b 06                 mov    eax,DWORD PTR [esi]
0054be1b: 8b 90 2c 01 00 00     mov    edx,DWORD PTR [eax+0x12c]
0054be21: 8b ce                 mov    ecx,esi
0054be23: ff d2                 call   edx
0054be25: 8b 8f e0 1e 00 00     mov    ecx,DWORD PTR [edi+0x1ee0]
0054be2b: 8b 06                 mov    eax,DWORD PTR [esi]
0054be2d: 8b 80 38 01 00 00     mov    eax,DWORD PTR [eax+0x138]
0054be33: 6a 00                 push   0x0
0054be35: 6a 00                 push   0x0
0054be37: 51                    push   ecx
0054be38: 6a 00                 push   0x0
0054be3a: 6a 01                 push   0x1
0054be3c: 8b d3                 mov    edx,ebx
0054be3e: 8b ce                 mov    ecx,esi
0054be40: ff d0                 call   eax
0054be42: 8b 0d 58 60 c2 00     mov    ecx,DWORD PTR ds:0xc26058
0054be48: 8b 01                 mov    eax,DWORD PTR [ecx]
0054be4a: 8b 97 e0 1e 00 00     mov    edx,DWORD PTR [edi+0x1ee0]
0054be50: 8b 80 44 01 00 00     mov    eax,DWORD PTR [eax+0x144]
0054be56: 6a 00                 push   0x0
0054be58: ff d0                 call   eax
0054be5a: 8d 8f ec 1e 00 00     lea    ecx,[edi+0x1eec]
0054be60: e8 0b b9 ed ff        call   0x427770
0054be65: e8 f6 8c 34 00        call   0x894b60
0054be6a: 8b c8                 mov    ecx,eax
0054be6c: e8 6f 8c 34 00        call   0x894ae0
0054be71: e8 1a 9f ff ff        call   0x545d90
0054be76: 8d 88 08 01 00 00     lea    ecx,[eax+0x108]
0054be7c: e8 2f 10 fc ff        call   0x50ceb0
0054be81: 85 c0                 test   eax,eax
0054be83: 74 43                 je     0x54bec8
0054be85: 6a 00                 push   0x0
0054be87: e8 04 9f ff ff        call   0x545d90
0054be8c: 8b c8                 mov    ecx,eax
0054be8e: e8 2d 9f ff ff        call   0x545dc0
0054be93: 85 c0                 test   eax,eax
0054be95: 75 31                 jne    0x54bec8
0054be97: 8b 16                 mov    edx,DWORD PTR [esi]
0054be99: 8b 82 0c 01 00 00     mov    eax,DWORD PTR [edx+0x10c]
0054be9f: 8b ce                 mov    ecx,esi
0054bea1: ff d0                 call   eax
0054bea3: 8b 10                 mov    edx,DWORD PTR [eax]
0054bea5: 8b c8                 mov    ecx,eax
0054bea7: 8b 02                 mov    eax,DWORD PTR [edx]
0054bea9: ff d0                 call   eax
0054beab: 84 c0                 test   al,al
0054bead: 74 19                 je     0x54bec8
0054beaf: 8b 16                 mov    edx,DWORD PTR [esi]
0054beb1: 8b 82 0c 01 00 00     mov    eax,DWORD PTR [edx+0x10c]
0054beb7: 8b ce                 mov    ecx,esi
0054beb9: ff d0                 call   eax
0054bebb: 8b 38                 mov    edi,DWORD PTR [eax]
0054bebd: 8b c8                 mov    ecx,eax
0054bebf: 8b 47 58              mov    eax,DWORD PTR [edi+0x58]
0054bec2: 6a 00                 push   0x0
0054bec4: 33 d2                 xor    edx,edx
0054bec6: ff d0                 call   eax
0054bec8: 8b 06                 mov    eax,DWORD PTR [esi]
0054beca: 8b 80 3c 01 00 00     mov    eax,DWORD PTR [eax+0x13c]
0054bed0: 6a 00                 push   0x0
0054bed2: 6a 00                 push   0x0
0054bed4: 6a ff                 push   0xffffffff
0054bed6: 8b d3                 mov    edx,ebx
0054bed8: 8b ce                 mov    ecx,esi
0054beda: ff d0                 call   eax
0054bedc: 8b 06                 mov    eax,DWORD PTR [esi]
0054bede: 8b 80 30 01 00 00     mov    eax,DWORD PTR [eax+0x130]
0054bee4: 6a 00                 push   0x0
0054bee6: 6a 00                 push   0x0
0054bee8: 33 d2                 xor    edx,edx
0054beea: 8b ce                 mov    ecx,esi
0054beec: ff d0                 call   eax
0054beee: 5f                    pop    edi
0054beef: 5e                    pop    esi
0054bef0: 5b                    pop    ebx
0054bef1: c3                    ret
```

## 8. Compact supporting raw bytes (exact callable functions)

```asm
00545d90: b8 01 00 00 00        mov eax,1
00545d95: 84 05 60 25 be 00     test BYTE PTR ds:0xbe2560,al
00545d9b: 75 1d                 jne 0x545dba
...
00545dba: b8 f8 23 be 00        mov eax,0xbe23f8
00545dbf: c3                    ret

0082db30: 8b 81 f4 05 00 00     mov eax,DWORD PTR [ecx+0x5f4]
0082db36: c3                    ret

006a7300: 8a 41 05              mov al,BYTE PTR [ecx+0x5]
006a7303: c3                    ret

00832813: 8b c8                 mov ecx,eax
00832815: e8 76 d9 01 00        call 0x850190
0083281a: eb 02                 jmp 0x83281e
0083281e: 68 c0 08 00 00        push 0x8c0
00832823: 89 86 f4 05 00 00     mov DWORD PTR [esi+0x5f4],eax

008501af: 88 46 05              mov BYTE PTR [esi+0x5],al
00850244: c7 06 88 bd b1 00     mov DWORD PTR [esi],0xb1bd88

00852760: 55                    push ebp
00852761: 8b ec                 mov ebp,esp
00852763: 51                    push ecx
00852764: 53                    push ebx
00852765: 56                    push esi
...
00852774: c6 46 09 01           mov BYTE PTR [esi+0x9],0x1
0085277d: 83 be 98 00 00 00 00  cmp DWORD PTR [esi+0x98],0
00852795: 80 7e 06 00           cmp BYTE PTR [esi+0x6],0
...
008528ea: 5f                    pop edi
008528eb: 5e                    pop esi
008528ec: b0 01                 mov al,1
008528ee: 5b                    pop ebx
008528ef: 8b e5                 mov esp,ebp
008528f1: 5d                    pop ebp
008528f2: c2 04 00              ret 4
```

**Scope limit:** These abbreviated auxiliary excerpts are provided to anchor named side-callees; the complete *assigned* function 0x0054BE00–0x0054BEF1 is supplied unabridged above. `0x00852760` and downstream device methods are the separate next investigation, not claimed analyzed exhaustively here.
