# Process 1b — bounded retail status/query callback 0x00508C70

**Date and bounded audit window:** 2026-10-22, approximately 10:51–10:59 UTC. **Original executable:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`, SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**, independently verified from `/mnt/data/SHIFT.exe` with `sha256sum`. The provided *complete* original objdump block was cross-checked against this SHA-matched PE, using GNU `objdump -D -Mintel -w --start-address=0x508c70 --stop-address=0x508e08`. **Full extent: `0x00508C70–0x00508E07` inclusive, end-exclusive `0x00508E08`, size `0x198 = 408 bytes`, 131 decoded instructions, 16 direct CALL sites**. The source for every result is this *entire verified body* and the short original wrapper from the assignment. Selected original instruction runs and a full call ledger below make the findings independently checkable. No callee bodies have been analyzed.

**Scope limits:** one retail callback, its incoming ABI/wrapper and all immediate outgoing call boundaries; no global writer/caller/vtable scans, no source/runtime/P-code/renderer/guest-state changes and no new replay. User-supplied v790 and v791 **P-code guest** observations are prior finite traces, not native Windows/Wine or proof of menu/race rendering.

## 1. ABI, incoming receiver and the original wrapper

The directly supplied wrapper `0x005088A0` takes **`ECX=I`**, where **I** is an item, not the enclosing owner **O**:

~~~asm
005088a0: 56                    push   esi
005088a1: 8b f1                 mov    esi,ecx
005088a3: 8b 06                 mov    eax,DWORD PTR [esi]
005088a5: 8b 50 0c              mov    edx,DWORD PTR [eax+0xc]
005088a8: ff d2                 call   edx
005088aa: 89 86 e4 00 00 00     mov    DWORD PTR [esi+0xe4],eax
005088b0: 5e                    pop    esi
005088b1: c3                    ret
~~~

It loads a runtime vptr **`V=DWORD[I]`**, chooses slot **`F=DWORD[V+0x0C]`**, calls F with **ECX=I** and **no newly pushed stack arguments**; dynamic-call return EIP **`0x005088AA`**. At this address **the wrapper itself** writes **`DWORD[I+0xE4]=returned EAX`**, then plain RET. Bytes do **not** give a fixed slot target for all item instances.

At the observed **v790 invocation**, F was dynamically **`0x00508C70`**. The body starts:

~~~asm
00508c70: 55                    push   ebp
00508c71: 8b ec                 mov    ebp,esp
00508c73: 83 ec 0c              sub    esp,0xc
00508c76: 56                    push   esi
00508c77: 8b f1                 mov    esi,ecx
00508c79: e8 f2 2b f0 ff        call   0x40b870
~~~

Thus **`ESI=I`**. The callback receives **no explicit stack arguments** from this wrapper path. It preserves ESI, saves EDI only on the longer route, and saves EBX only if the owner-derived traversal executes. Its three normal exits all use **plain `RET`**, no callee argument cleanup: **`0x00508C91, 0x00508CCE, 0x00508E07`**. It allocates **0xC bytes of EBP-relative locals** for addresses subsequently passed to helpers, but does not directly write those locals. Its own original code has no direct owner-O operand; it reads **`DWORD[I+0xE8]`** and derives owner-relative substructure *addresses* from that loaded pointer on one branch.

## 2. Full branch/dataflow audit

### 2.1 Two early status=1 returns

**First gate**: direct `CALL 0x0040B870` with **ECX=I**, no pushed arg, return `0x00508C7E`; its **EAX return is a pointer** dereferenced as **`BYTE[EAX+0x104]`**. If that byte is nonzero (`TEST AL,AL` and `JNE`-equivalent through the original `JE` fallthrough), execute `MOV EAX,1` at `0x00508C88` and plain `RET` at `0x00508C91`. The dereferenced pointer is **callee-returned EAX**, not proven to be I or O.

When zero: prepare **one pushed stack DWORD `&[EBP−8]`**, **EDX=&[EBP−0xC]**, **ECX=I**, then `CALL 0x00508890` at `0x00508C9B`. Test returned **AL**; **AL==0** branches to the same `0x00508C88` status **1** exit. There is no caller `ADD ESP,4`, so a normally balanced call requires callee/equivalent cleanup; the callee's literal epilogue is not inspected. It is *possible* that the helper writes to the passed local pointers, but **no such write is direct in 0x00508C70**.

On nonzero AL: load **ECX=DWORD[I+0xC]**, **EDX=DWORD[I+0x348]**, save EDI, compute **EDI=I+8**, push the ECX field as **one stack DWORD**, set ECX=EDI, call **`0x00637890`** (`0x00508CB4`). Immediately call **`0x00637800`** (`0x00508CBB`) with **ECX=I+8**. Test returned AL: if **AL!=0**, restore EDI, assign **EAX=1**, exit via `0x00508CCE`. Thus **there are three independent conditions that can produce status 1 before any direct I-field write**: first byte nonzero; 0x00508890 returns AL=0; or 0x00637800 returns AL!=0.

### 2.2 Setup, early owner-traversal skip and two optional loops

If all early gates pass, the callback uses **ECX=I+0x120**, **EDX=I+8** to call **`0x00636E50`** at `0x00508CD7`, return `0x00508CDC`.

Immediately thereafter **`TEST BYTE[I+0x340],0x04`**. It reads **DWORD[I+4]** and performs three **direct item writes** before the branch:

~~~asm
00508cdc: f6 86 40 03 00 00 04  test   BYTE PTR [esi+0x340],0x4
00508ce3: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
00508ce6: 89 86 50 01 00 00     mov    DWORD PTR [esi+0x150],eax
00508cec: 8d 86 f0 00 00 00     lea    eax,[esi+0xf0]
00508cf2: 89 86 5c 01 00 00     mov    DWORD PTR [esi+0x15c],eax
00508cf8: c7 86 10 02 00 00 00 00 01 00  mov DWORD PTR [esi+0x210],0x10000
00508d02: 0f 85 ae 00 00 00     jne    0x508db6
~~~

**`JNE 0x00508DB6`** tests flags from original `TEST BYTE[I+0x340],4`, not from the intervening MOV/LEA stores, which do **not** modify EFLAGS. **If bit 0x04 is set, skip both owner-derived loops.** If clear: load **`O=DWORD[I+0xE8]`**, save EBX, and compute **`B1=O+0x64`** with LEA.

**First loop (B1=O+0x64):**
- `0x00508D17`: `CALL 0x0067DB80`, **ECX=B1**, **EDX=&[EBP−4]**. Read **EDI=DWORD[returned EAX]**.
- `0x00508D23`: `CALL 0x004F5EB0`, same ECX/EDX, compare **EDI with DWORD[returned EAX]**. If equal, exit this loop to `0x00508D5B`.
- Otherwise `0x00508D31` reads **EDX=DWORD[EDI+0xC]**, computes **ECX=I+0x120**, calls **`0x00637470`** at `0x00508D3A`. Next read **DWORD[EDI+4]**, update EDI to it only if nonzero. Call **0x004F5EB0** again at `0x00508D4D` with ECX=B1, EDX=&[EBP−4], repeat while EDI differs from DWORD[returned EAX]. **Loop bound is not in this body.**

**Second loop:** after exiting first loop, **`TEST BYTE[I+0x340],0x02`** at `0x00508D5B`. If bit 0x02 clear, jump to `0x00508DB5` and restore EBX. Otherwise **re-read O=DWORD[I+0xE8]** and form **`B2=O+0x88`**:
- `0x00508D75`: **0x0067DB80**, ECX=B2, EDX=&[EBP−4]; load EDI from returned pointer;
- `0x00508D81`: **0x004F5EB0**, same ECX/EDX, compare EDI to DWORD[returned pointer]; if equal, finish;
- loop at `0x00508D90`: **EDX=DWORD[EDI+0xC]**, **ECX=I+0x120**, call **0x006374A0** at `0x00508D99`; conditionally advance EDI via `DWORD[EDI+4]`, re-call **0x004F5EB0** at `0x00508DAC`, repeat if EDI differs from returned DWORD;
- exit through common **`0x00508DB5: POP EBX`**, then `0x00508DB6`.

These are **two independent flag-gated traversals of helper-provided iterator pointers**, not proof of a fixed iteration count or specific UI element source. **O+0x64 and O+0x88 are computed addresses, never directly dereferenced or written in this callback**. Any side effects of helpers operating on these substructures are **unknown**.

### 2.3 Final writes and the exact EAX=5 mechanism

All paths reaching `0x00508DB6` continue to the common tail:

~~~asm
00508db6: 8b 56 04              mov    edx,DWORD PTR [esi+0x4]
00508db9: 89 96 14 02 00 00     mov    DWORD PTR [esi+0x214],edx
00508dbf: 8d be 20 01 00 00     lea    edi,[esi+0x120]
00508dc5: 32 d2                 xor    dl,dl
00508dc7: 8b cf                 mov    ecx,edi
00508dc9: e8 12 e0 12 00        call   0x636de0
00508dce: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
00508dd1: 50                    push   eax
00508dd2: 6a 00                 push   0x0
00508dd4: 8d 56 08              lea    edx,[esi+0x8]
00508dd7: 8d 8e f0 00 00 00     lea    ecx,[esi+0xf0]
00508ddd: c7 86 60 01 00 00 00 00 10 00  mov DWORD PTR [esi+0x160],0x100000
00508de7: e8 34 11 00 00        call   0x509f20
00508dec: 8b 4e 0c              mov    ecx,DWORD PTR [esi+0xc]
00508def: 6a 05                 push   0x5
00508df1: 8b d7                 mov    edx,edi
00508df3: e8 58 c1 12 00        call   0x634f50
00508df8: f7 d8                 neg    eax
00508dfa: 1b c0                 sbb    eax,eax
00508dfc: 83 e0 fc              and    eax,0xfffffffc
00508dff: 5f                    pop    edi
00508e00: 83 c0 05              add    eax,0x5
00508e03: 5e                    pop    esi
00508e04: 8b e5                 mov    esp,ebp
00508e06: 5d                    pop    ebp
00508e07: c3                    ret
~~~

At `0x00508DC9`, **`XOR DL,DL` only clears the low byte** of EDX after the immediately preceding load `EDX=DWORD[I+4]`: outgoing **EDX=(DWORD[I+4] & 0xFFFFFF00)**, **not full EDX=0**. **ECX=I+0x120**, no pushed args. Then **`CALL 0x00509F20`** uses **ECX=I+0xF0**, **EDX=I+8** and **two explicit pushed DWORDs**: first=0, second=DWORD[I+4]. It follows the direct write **DWORD[I+0x160]=0x00100000**. No caller-side ADD ESP,8 appears after the call, so normally balanced execution requires callee/equivalent stack cleanup; the callee epilogue is not inspected.

Next `0x00508DF3: CALL 0x00634F50` gets **ECX=DWORD[I+0x0C]**, **EDX=I+0x120**, **one pushed DWORD=5**, and returns at `0x00508DF8`. This call too has no visible caller ADD ESP,4; assume only a compatible normally balanced return, not a verified RET 4 opcode.

**Exact return arithmetic:** let `r` denote the **full EAX** returned by `0x00634F50`. `NEG EAX` sets carry CF=0 if r==0, CF=1 if r!=0. `SBB EAX,EAX` yields 0 for CF=0 or `0xFFFFFFFF` for CF=1. `AND EAX,0xFFFFFFFC` yields 0 or `0xFFFFFFFC`, then `ADD EAX,5` yields **5** or **1**:

| r from `0x00634F50` | Final EAX from `0x00508C70` |
|---|---|
| **r=0** | **5** |
| **r!=0** | **1** |

All early branches also return exactly **1**. Thus **every normal exit is EAX∈{1,5}**. **The observed inner v790 EAX=5 implies this full tail was taken and 0x00634F50 returned zero in that observed invocation**. This says nothing about the meaning of that zero or why an unrelated owner readiness byte was later zero.

## 3. Exhaustive direct memory accesses and direct write-set

The **entire explicit item I-relative write-set** in this body consists of exactly **five 32-bit stores**, all on the long path after early status-1 branches:

| EIP | Direct memory WRITE | Exact value |
|---|---|---|
| `0x00508CE6` | **DWORD[I+0x150]** | previously read DWORD[I+4] |
| `0x00508CF2` | **DWORD[I+0x15C]** | address I+0xF0 (LEA) |
| `0x00508CF8` | **DWORD[I+0x210]** | constant `0x00010000` |
| `0x00508DB9` | **DWORD[I+0x214]** | previously read DWORD[I+4] |
| `0x00508DDD` | **DWORD[I+0x160]** | constant `0x00100000` |

**Explicit item-relative reads:** `DWORD[I+0x0C]` at `0x00508CA4` and `0x00508DEC`; `DWORD[I+0x348]` at `0x00508CA7`; `BYTE[I+0x340]` at `0x00508CDC` (mask 4) and `0x00508D5B` (mask 2); `DWORD[I+4]` at `0x00508CE3, 0x00508DB6, 0x00508DCE`; **`DWORD[I+0xE8]`** at `0x00508D08, 0x00508D64`. These are the only direct item-field reads through ESI in the full body. `LEA I+8, I+0x120, I+0xF0` are **address computations only**, not memory dereferences.

**Other explicit reads:** `BYTE[return EAX of 0x0040B870 +0x104]` (`0x00508C7E`); **DWORD[return EAX of 0x0067DB80]** (`0x00508D1C, 0x00508D7A`); **DWORD[return EAX of 0x004F5EB0]** (`0x00508D28, 0x00508D52, 0x00508D86, 0x00508DB1`); **DWORD[iterator EDI+0xC]** (`0x00508D31, 0x00508D90`); **DWORD[iterator EDI+4]** (`0x00508D3F, 0x00508D9E`). There are **no explicit stores** through these returned/iterator pointers in the original body.

**Stack effects:** EBP/ESI, conditional EDI and EBX saves, PUSHed outgoing arguments, CALL-pushed return addresses and subsequent POP/RET entail implicit machine-stack reads/writes. Stack-relative `LEA [EBP−8], [EBP−0xC], [EBP−4]` only form pointers; the function has no direct instruction writing those locals. Callees given those pointers could write them, but those are **unknown nested effects**, not direct writes of this body.

**Owner distinction:** `O=DWORD[I+0xE8]` is loaded only on the owner-traversal path. The function does **not directly read or write** `DWORD[O]` (owner vptr), `DWORD[O+0x14]` (observed insertion count) or `BYTE[O+0x2D]` (readiness). The address expressions **O+0x64** and **O+0x88** are *passed* to external iterator helpers, not dereferenced by the callback. **`DWORD[I+0xE4]` is also not directly stored by the callback**: it is written in the separate wrapper at `0x005088AA`. Unmeasured pointer aliases, nested helper side effects and asynchronous writes to owner memory remain unproved, not ruled out.

## 4. All 16 direct outgoing CALL boundaries (callee bodies not inspected)

Return EIP is the next original machine-code instruction. Where the callback has not just prepared a volatile register, its value is **unknown** rather than invented.

| Site → target | Return EIP | Proven immediate ABI, outgoing arguments |
|---|---|---|
| `0x508C79 → 0x40B870` | `0x508C7E` | ECX=I; 0 pushed |
| `0x508C9B → 0x508890` | `0x508CA0` | ECX=I, EDX=&[EBP−0xC]; **one PUSH & [EBP−8]** |
| `0x508CB4 → 0x637890` | `0x508CB9` | ECX=I+8, EDX=DWORD[I+0x348]; **one PUSH DWORD[I+0xC]** |
| `0x508CBB → 0x637800` | `0x508CC0` | ECX=I+8, EDX not freshly established; 0 new PUSH |
| `0x508CD7 → 0x636E50` | `0x508CDC` | ECX=I+0x120, EDX=I+8; 0 PUSH |
| `0x508D17 → 0x67DB80` | `0x508D1C` | ECX=O+0x64, EDX=&[EBP−4]; 0 PUSH |
| `0x508D23 → 0x4F5EB0` | `0x508D28` | ECX=O+0x64, EDX=&[EBP−4]; 0 PUSH |
| `0x508D3A → 0x637470` | `0x508D3F` | ECX=I+0x120, EDX=DWORD[iterator+0xC]; 0 PUSH |
| `0x508D4D → 0x4F5EB0` | `0x508D52` | ECX=O+0x64, EDX=&[EBP−4]; 0 PUSH |
| `0x508D75 → 0x67DB80` | `0x508D7A` | ECX=O+0x88, EDX=&[EBP−4]; 0 PUSH |
| `0x508D81 → 0x4F5EB0` | `0x508D86` | ECX=O+0x88, EDX=&[EBP−4]; 0 PUSH |
| `0x508D99 → 0x6374A0` | `0x508D9E` | ECX=I+0x120, EDX=DWORD[iterator+0xC]; 0 PUSH |
| `0x508DAC → 0x4F5EB0` | `0x508DB1` | ECX=O+0x88, EDX=&[EBP−4]; 0 PUSH |
| `0x508DC9 → 0x636DE0` | `0x508DCE` | ECX=I+0x120, EDX=DWORD[I+4]&0xFFFFFF00; 0 PUSH |
| `0x508DE7 → 0x509F20` | `0x508DEC` | ECX=I+0xF0, EDX=I+8; **two stack args: first 0, second DWORD[I+4]** |
| `0x508DF3 → 0x634F50` | `0x508DF8` | ECX=DWORD[I+0xC], EDX=I+0x120; **one pushed stack arg 5** |

For pushed outgoing arguments and no visible caller ESP correction, normal stack-balanced return requires callee-side or equivalent cleanup. **No callee RET opcode, internal memory write, return-type semantics or object-class name has been determined by this report.**

## 5. Supplied controlled replay fields; what status 5 does not establish

**v790 (already supplied, not rerun):** Writer `0x005092F0` invoked outer `0x005088A0` with item **`I=0x27DFAD78`**; wrapper's return to writer was **`0x00509370`**. **One observed inner virtual target was `0x00508C70` and returned EAX=5**. Outer `0x005088A0` returned **5** as well, consistent with its direct store `DWORD[I+0xE4]=5`. Static final-tail math means this particular observed inner status 5 required the final `0x00634F50` to return zero on that path; the external callee's reason for zero remains unknown.

**v791 (already supplied, not rerun):** **Five** outer `0x005088A0` invocations ended EAX=5. Their inner target EIPs were not supplied, so **it is not valid to assert all five executed `0x00508C70`** or that all five passed through `0x00634F50`. Separately, original owner **DWORD[O+0x14]=9** was observed, guard AL=0, and writer `0x005092F0` cleared **BYTE[O+0x2D]=0**. No direct causal link from **status 5** to these owner-field observations is proven. Guest draw translation and retail rendering have not been proven; neither observation is a native Windows/Wine run.

**Conclusion:** The PE proves three early gates that can return 1, five direct item initialization writes, two optional traversals of owner-derived substructures, and a tail that computes status **5 iff last callee EAX=0**, otherwise 1. The outer wrapper records the status in item+0xE4. **This callback directly neither changes owner O+0x14 nor sets/clears owner O+0x2D nor modifies owner vptr**. External helper or alias effects are unknown; no UI/menu/race cause or fix follows.

## 6. Exactly one next evidence-backed target

**`0x00634F50`**, the direct final status-determining callee called at **`0x00508DF3`**, return EIP **`0x00508DF8`**, with **ECX=DWORD[I+0xC]**, **EDX=I+0x120**, **one pushed DWORD 5**. This single next bounded target is directly justified because the **zero/nonzero return value** is transformed by adjacent original PE instructions into **5/1**. An independently assigned narrow PE audit of this callee's actual body, stack cleanup and direct writes would address the remaining most relevant status question. **No second next target**, global sweep or new replay is proposed.

## Appendix A — original PE excerpts fixing early exits, both loops and full-tail status

~~~asm
00508c79: e8 f2 2b f0 ff        call   0x40b870
00508c7e: 8a 80 04 01 00 00     mov    al,BYTE PTR [eax+0x104]
00508c84: 84 c0                 test   al,al
00508c86: 74 0a                 je     0x508c92
00508c88: b8 01 00 00 00        mov    eax,0x1
00508c91: c3                    ret
00508c9b: e8 f0 fb ff ff        call   0x508890
00508ca0: 84 c0                 test   al,al
00508ca2: 74 e4                 je     0x508c88
00508cbb: e8 40 eb 12 00        call   0x637800
00508cc0: 84 c0                 test   al,al
00508cc2: 74 0b                 je     0x508ccf
00508cc5: b8 01 00 00 00        mov    eax,0x1
00508cce: c3                    ret
00508cdc: f6 86 40 03 00 00 04  test   BYTE PTR [esi+0x340],0x4
00508ce6: 89 86 50 01 00 00     mov    DWORD PTR [esi+0x150],eax
00508cf2: 89 86 5c 01 00 00     mov    DWORD PTR [esi+0x15c],eax
00508cf8: c7 86 10 02 00 00 00 00 01 00  mov DWORD PTR [esi+0x210],0x10000
00508d02: 0f 85 ae 00 00 00     jne    0x508db6
00508d17: e8 64 4e 17 00        call   0x67db80
00508d23: e8 88 d1 fe ff        call   0x4f5eb0
00508d3a: e8 31 e7 12 00        call   0x637470
00508d4d: e8 5e d1 fe ff        call   0x4f5eb0
00508d59: 75 d6                 jne    0x508d31
00508d5b: f6 86 40 03 00 00 02  test   BYTE PTR [esi+0x340],0x2
00508d75: e8 06 4e 17 00        call   0x67db80
00508d81: e8 2a d1 fe ff        call   0x4f5eb0
00508d99: e8 02 e7 12 00        call   0x6374a0
00508dac: e8 ff d0 fe ff        call   0x4f5eb0
00508db3: 75 db                 jne    0x508d90
00508db9: 89 96 14 02 00 00     mov    DWORD PTR [esi+0x214],edx
00508dc5: 32 d2                 xor    dl,dl
00508dc9: e8 12 e0 12 00        call   0x636de0
00508ddd: c7 86 60 01 00 00 00 00 10 00  mov DWORD PTR [esi+0x160],0x100000
00508de7: e8 34 11 00 00        call   0x509f20
00508dec: 8b 4e 0c              mov    ecx,DWORD PTR [esi+0xc]
00508def: 6a 05                 push   0x5
00508df1: 8b d7                 mov    edx,edi
00508df3: e8 58 c1 12 00        call   0x634f50
00508df8: f7 d8                 neg    eax
00508dfa: 1b c0                 sbb    eax,eax
00508dfc: 83 e0 fc              and    eax,0xfffffffc
00508dff: 5f                    pop    edi
00508e00: 83 c0 05              add    eax,0x5
00508e07: c3                    ret
~~~

**Only report Markdown is added in `work/process-reports`. No other file, runtime state or replay is changed.**
