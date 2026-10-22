# Process 1b — bounded O-receiver setup helper 0x00508F00 → 0x00474D70

**Date:** 2026-10-22. **Retail binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`, original `/mnt/data/SHIFT.exe` SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`** (independently rechecked). Static disassembly from GNU `objdump -D -Mintel -w` reverified the thunk `0x00508F00`, full non-padding target `0x00474D70–0x00474DDA` and direct callsite `0x0054B8F2–0x0054B90D`. The intervening gaps in the target function contain **only original `CC` padding** at `0x00474D86–0x00474DA7` and `0x00474DB8–0x00474DC6`; not unexplored executable basic blocks.

**Scope:** exactly the call `0x0054B903` through its five-byte tail-jump thunk `0x00508F00` into the full target body `0x00474D70`. Only direct *outgoing* call boundaries `0x00508E40` and `0x0062E1A0` are established; neither callee's body is analyzed. No global caller/writer/vtable sweep, unrelated list-helper/renderer work, new replay, guest-state manipulation, code, P-code, runtime or renderer changes, native Windows/Wine execution or claim of rendered menu/race. Previously supplied v791 facts are kept separate from retail PE.

## 1. Exact caller-side register/stack ABI and tail thunk

Prior bounded caller `0x0054B8B0–0x0054BB15` receives `ECX=S` and saves it into ESI; computes `EDI=O=S+4` at `0x0054B8D2`. After the earlier vtable slot+4 call, it prepares two local DWORDs and, at the target callsite, issues:

~~~asm
0054b8f2: 33 c9                 xor    ecx,ecx
0054b8f4: e8 a7 28 0e 00       call   0x62e1a0
0054b8f9: 8b 55 f8              mov    edx,DWORD PTR [ebp-0x8]
0054b8fc: 50                    push   eax
0054b8fd: 8b 45 fc              mov    eax,DWORD PTR [ebp-0x4]
0054b900: 50                    push   eax
0054b901: 8b cf                 mov    ecx,edi
0054b903: e8 f8 d5 fb ff       call   0x508f00
0054b908: ba 00 00 30 00       mov    edx,0x300000
0054b90d: 8b cf                 mov    ecx,edi
~~~

The `0x0054B8F4` direct call was prepared with `ECX=0`; its returned EAX is placed on the stack **first** by `PUSH EAX`. At `0x0054B8F9`, `EDX=DWORD[caller EBP-8]`. The second `PUSH` uses the new `EAX=DWORD[caller EBP-4]`. The wrapper method's outgoing normal stack layout at target entry after CALL is:

| Location relative to target EBP | Proven value/source | Role in target |
|---|---|---|
| Register `ECX` | `O=EDI=S+4` | Object/receiver used by all field accesses |
| Register `EDX` | `DWORD[caller EBP-8]` | Saved in EDI, then stores `DWORD[O+0x30]` |
| `[EBP+0x08]` | `DWORD[caller EBP-4]`, **last PUSH / first stack arg** | Loads in EAX at `0x00474DCA`; stores `DWORD[O+0x34]`; returned as full EAX |
| `[EBP+0x0C]` | Earlier return EAX of `0x0062E1A0`, **first PUSH / second stack arg** | Fallback-zero check for `DWORD[O+0x38]` |
| `[EBP+0]` / `[EBP+4]` | Saved old EBP / return address | Standard stack frame |

The first/second stack *parameters* are not in original push order: x86 pushes right-to-left. The caller's explicit outgoing method arguments are exactly **two DWORDs**, plus ECX and EDX register inputs. There is no hidden extra PUSH for the initial virtual-call setup; earlier helper calls finish before this callsite.

The entire original thunk is:

~~~asm
00508f00: e9 6b be f6 ff       jmp    0x474d70
~~~

This is an **unconditional relative near JMP**, not CALL. It does **not** push a new return address, change incoming ECX/EDX or stack arguments, allocate a frame, restore registers, or return by itself. Therefore actual target `0x00474D70` sees precisely the register/stack inputs assembled for `0x00508F00`. The body ultimately returns **straight to the original caller at `0x0054B908`** with **`RET 0x8`**, cleaning both outgoing stack DWORDs. The caller performs **no subsequent `ADD ESP,8`**; adding one would double-clean the method inputs. This is a register-receiver / two-stack-argument convention *as observed*, not a verified source-level __thiscall or class-method signature.

## 2. Complete original body: branch conditions and precise memory operations

Full original *non-padding* instruction block is reproduced byte-for-byte in Appendix A, including both tests, unconditional jumps, conditional helper calls and final `RET 8`. On entry:

~~~asm
00474d70: 55                    push   ebp
00474d71: 8b ec                 mov    ebp,esp
00474d73: 56                    push   esi
00474d74: 8b f1                 mov    esi,ecx
00474d76: 83 7e 30 00           cmp    DWORD PTR [esi+0x30],0x0
00474d7a: 57                    push   edi
00474d7b: 8b fa                 mov    edi,edx
00474d7d: 74 29                 je     0x474da8
00474d7f: e8 bc 40 09 00        call   0x508e40
00474d84: eb 22                 jmp    0x474da8
~~~

Let `O=ESI=entry ECX` and `A=entry EDX=EDI`.

**First branch** at `0x00474D76`: **compare `DWORD[O+0x30]` to zero**.
- If **zero**: `0x00474D7D: JE 0x00474DA8` skips `CALL 0x00508E40` entirely.
- If **nonzero**: control falls through to **`0x00474D7F: CALL 0x00508E40`**, followed by unconditional `JMP 0x00474DA8` (no return/status check).
- **Exactly at this immediate call boundary**, `ECX=O`: the prologue saved it to ESI but did not change ECX. **EDX is still A**, copied to EDI by `MOV EDI,EDX`, not changed before this CALL. No explicit stack arguments are newly pushed for `0x00508E40`. Its ABI/receiver are **inferred strictly from the actual register values**; what it does, returns, mutates or frees is **not** determined here. The local store into `O+0x30` has not yet executed.
- The branch is on **existing `DWORD[O+0x30]`**, which might plausibly mean "old resource exists", but there is no proof of object/handle semantics or target-side clearing without the callee implementation. It is not a read of `O+0x14` (the replayed insertion-maintained counter).

**Second branch** at `0x00474DA8` (reached on normal execution from either first branch):

~~~asm
00474da8: 8b 45 0c              mov    eax,DWORD PTR [ebp+0xc]
00474dab: 85 c0                 test   eax,eax
00474dad: 75 18                 jne    0x474dc7
00474daf: 33 c9                 xor    ecx,ecx
00474db1: e8 ea 93 1b 00       call   0x62e1a0
00474db6: eb 0f                 jmp    0x474dc7
~~~

- First load **`B=DWORD[EBP+0x0C]`**. If `B!=0`, `JNE 0x00474DC7` selects **EAX=B** unchanged for the following store and **skips** the fallback.
- If `B==0`, **`XOR ECX,ECX`** sets **ECX=0** and `CALL 0x0062E1A0` with **no new pushed stack arguments**. Its returned full EAX replaces the zero B. There is **no null/failure check** on this result in the caller body.
- This helper also appears earlier at `0x0054B8F4` to supply B in the first place. Its *external implementation and semantic name* are unverified. From this local body, it is only a "zero-fallback provider", not necessarily a heap allocator/resource object factory.

**Join and stores** at `0x00474DC7`:

~~~asm
00474dc7: 89 46 38              mov    DWORD PTR [esi+0x38],eax
00474dca: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00474dcd: 89 7e 30              mov    DWORD PTR [esi+0x30],edi
00474dd0: 5f                    pop    edi
00474dd1: 89 46 34              mov    DWORD PTR [esi+0x34],eax
00474dd4: c6 46 3c 01           mov    BYTE PTR [esi+0x3c],0x1
00474dd8: 5e                    pop    esi
00474dd9: 5d                    pop    ebp
00474dda: c2 08 00              ret    0x8
~~~

**All direct PE-level memory accesses to the receiver (and only these) are:**

| EIP | Width, receiver-relative address | Value/condition |
|---|---|---|
| `0x00474D76` | **READ DWORD[O+0x30]** | Compare with zero; gate `0x00508E40` |
| `0x00474DC7` | **WRITE DWORD[O+0x38]** | B if nonzero; otherwise EAX returned by `0x0062E1A0` |
| `0x00474DCD` | **WRITE DWORD[O+0x30]** | Original incoming EDX, saved in EDI |
| `0x00474DD1` | **WRITE DWORD[O+0x34]** | Original first pushed DWORD (`[EBP+8]`) |
| `0x00474DD4` | **WRITE BYTE[O+0x3C]** | Literal byte **1**, unconditional on normal return |

The function separately **reads `[EBP+0x0C]` and `[EBP+0x08]`**. There are no explicit direct stores to either stack parameter or to local offsets aside from prologue/restore. It preserves ESI and EDI and EBP per observed prologue/epilogue. Outgoing calls are exactly **`0x00508E40`** on old-field-nonzero and **`0x0062E1A0`** on second-argument-zero; no loop, further return branches or other call sites in this body.

**Return EAX:** `MOV EAX,[EBP+8]` at `0x00474DCA` occurs **after** whichever helper branches and after storing `O+0x38`; no later instruction changes EAX. Thus **full 32-bit EAX equals the original first stack argument** on both normal paths, **not** the second arg/fallback result, a fixed boolean, the old O+0x30 or an observed HRESULT. `RET 8` is callee cleanup of exactly two method stack DWORDs.

### Pseudocode — bounded semantics only, not reconstructed source

~~~c
// Register/stack ABI only: O=ECX, A=EDX, p1=[EBP+8], p2=[EBP+0xC]
if (*(uint32_t *)(O+0x30) != 0) {
    helper_00508E40(/*ECX=O, EDX=A; no local stack args*/);
}
uint32_t value38 = p2;
if (value38 == 0) {
    value38 = helper_0062E1A0(/*ECX=0; no local stack args*/);
}
*(uint32_t *)(O+0x38) = value38;
*(uint32_t *)(O+0x30) = A;
*(uint32_t *)(O+0x34) = p1;
*(uint8_t *)(O+0x3C) = 1;
return p1;  // EAX; method RET 8
~~~

This description does **not** assert the return type/callee cleanup rules or side effects of the two nested helpers. A registered/cached state slot, ownership/release, resource allocation, callback, valid flag etc. are all possible *interpretations*, not typed PE observations.

## 3. Does this setup write the vptr, list count or readiness byte?

**No direct original machine-code writes in the complete target body** to any of:

- **`DWORD[O]`**, the object's vptr storage loaded by the earlier `0x0054B8DC` and later `0x0054BAC6` dispatch sites;
- **`DWORD[O+0x14]`**, the exact insertion-maintained count field that the v788/v791 guard sees as 9;
- **`BYTE[O+0x2D]`**, the readiness-associated byte that later writer `0x005092F0` explicitly writes to zero.

The only direct field writes are **+0x38, +0x30, +0x34 (each DWORD) and +0x3C (BYTE=1)** in that order. In particular, **`BYTE[O+0x3C]=1` is *not* `BYTE[O+0x2D]=1`**; it is a different offset. The first branch's **`DWORD[O+0x30]`** is a *read* used to decide whether to call the outside helper; the eventual write to the same offset occurs after that call.

**Important alias/side-effect qualification:** this is a strict statement about the body’s **direct addressing**, not a guarantee that `0x00508E40` or `0x0062E1A0` cannot indirectly touch O, its vptr, list count, or readiness state. The helper `0x00508E40` is entered with **ECX=O** and unknown implementation effects, so it could modify arbitrary O fields, including those not directly written by `0x00474D70`. The `0x0062E1A0` helper is an external call with ECX=0 whose writes are also not established; no blanket purity claim is made. Likewise a malformed/aliased pointer could make unrelated memory overlap, but no such alias is evidenced by the original code or supplied runtime facts.

## 4. Role of the helper before nine registrations: PE vs Ghidra inference vs finite replay

**PE facts:** `0x0054B903` is a direct call with register receiver **O**, a second register value **EDX**, two stack DWORDs, and return to **`0x0054B908`**. The thunk simply tail-jumps to a target that:
(1) conditionally invokes `0x00508E40` when old **`DWORD[O+0x30] != 0`**;
(2) takes/replaces a second incoming DWORD via zero fallback;
(3) writes a **four-field setup tuple** at O offsets +0x30/+0x34/+0x38/+0x3C; and
(4) returns first incoming stack DWORD in EAX while cleaning 8 bytes. The call occurs before the nine direct list insertions in the caller, so those fields are set by this body before registrations **on a normal return**, unless another unknown callee changes them.

**Grounded but unproven inference:** the routine resembles a state-binding or configuration setup/replacement for O with an optional release/reset of a preexisting field. That matches a Ghidra description but **does not prove a constructor, identity of an interface, object reference ownership, allocator, callback, or semantics of byte +0x3C**. Only offsets, tests, instructions, outgoing calling convention and stores are validated here.

**Previously reported controlled replay (not newly executed):** v791 observed O+0x14=9, a later guard with AL=0, and byte-zero store to O+0x2D in writer 0x005092F0. This is original retail PE running inside P-code guest runtime; guest draw translation / rendered menu/race are **not proven**. Those observations do **not demonstrate** this setup function's actual invocation/old-field value, whether its outgoing helper ran, or that it caused or should repair readiness. The static code offers **no direct causality from these four setup writes to count=9 or byte +0x2D=0**.

**Unresolved:** initial value of O+0x30; dynamic effects/return of `0x00508E40`, side effects and type of `0x0062E1A0`, true typed meaning of O+0x30/34/38/3C, whether call touched vptr indirectly, positive readiness-byte writers and global list lifecycle. No inference is made about race/menu presence or native Windows/Wine launch.

## 5. Exactly one next evidence-backed target

**`0x00508E40` — the single direct conditional callee of `0x00474D70` at `0x00474D7F`.** It receives **`ECX=O`**, still-current **`EDX=incoming register A`**, with **no newly pushed stack parameters**, *only when `DWORD[O+0x30]!=0`*. This is the **only evidence-backed next target** because its potential prior-state effects are the explicit remaining uncertainty about the same O receiver before list registrations. In a **separate bounded task**, examine its full original PE block, writes, return and immediate ABI to determine whether old setup state can affect O fields, without global caller/writer scans or guest-state forcing. Its body is **not analyzed in the present task**.

## Appendix A — full original thunk 0x00508F00

~~~asm
00508f00: e9 6b be f6 ff        jmp    0x474d70
~~~

## Appendix B — complete original nonpadding target 0x00474D70–0x00474DDA

~~~asm
00474d70: 55                    push   ebp
00474d71: 8b ec                 mov    ebp,esp
00474d73: 56                    push   esi
00474d74: 8b f1                 mov    esi,ecx
00474d76: 83 7e 30 00           cmp    DWORD PTR [esi+0x30],0x0
00474d7a: 57                    push   edi
00474d7b: 8b fa                 mov    edi,edx
00474d7d: 74 29                 je     0x474da8
00474d7f: e8 bc 40 09 00        call   0x508e40
00474d84: eb 22                 jmp    0x474da8
00474da8: 8b 45 0c              mov    eax,DWORD PTR [ebp+0xc]
00474dab: 85 c0                 test   eax,eax
00474dad: 75 18                 jne    0x474dc7
00474daf: 33 c9                 xor    ecx,ecx
00474db1: e8 ea 93 1b 00        call   0x62e1a0
00474db6: eb 0f                 jmp    0x474dc7
00474dc7: 89 46 38              mov    DWORD PTR [esi+0x38],eax
00474dca: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00474dcd: 89 7e 30              mov    DWORD PTR [esi+0x30],edi
00474dd0: 5f                    pop    edi
00474dd1: 89 46 34              mov    DWORD PTR [esi+0x34],eax
00474dd4: c6 46 3c 01           mov    BYTE PTR [esi+0x3c],0x1
00474dd8: 5e                    pop    esi
00474dd9: 5d                    pop    ebp
00474dda: c2 08 00              ret    0x8
~~~

**Padding:** original PE bytes **`0x00474D86–0x00474DA7` (34 bytes)** and **`0x00474DB8–0x00474DC6` (15 bytes)** are all `0xCC`, not unexamined function logic. **No function-pointer entry from the body jumps to them.**

## Appendix C — original caller-side arguments and return anchor

~~~asm
0054b8f2: 33 c9                 xor    ecx,ecx
0054b8f4: e8 a7 28 0e 00       call   0x62e1a0
0054b8f9: 8b 55 f8              mov    edx,DWORD PTR [ebp-0x8]
0054b8fc: 50                    push   eax
0054b8fd: 8b 45 fc              mov    eax,DWORD PTR [ebp-0x4]
0054b900: 50                    push   eax
0054b901: 8b cf                 mov    ecx,edi
0054b903: e8 f8 d5 fb ff       call   0x508f00
0054b908: ba 00 00 30 00       mov    edx,0x300000
0054b90d: 8b cf                 mov    ecx,edi
~~~

**Report-only publication:** no code, runtime, P-code, guest state, renderer, replay or PR changes. No actual game-run inference.
