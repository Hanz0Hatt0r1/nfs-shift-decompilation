# Process 1b — bounded pre-registration virtual slot +0x04 at retail callsite 0x0054B8DC

**Date:** 2026-10-22. **Original binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`, SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**. SHA was independently checked against the mounted `/mnt/data/SHIFT.exe`; exact opening/callsite bytes independently confirmed by GNU `objdump -D -Mintel -w`. Appendix A reproduces the complete **167-instruction** enclosing retail function from the prior independently verified original PE objdump, `0x0054B8B0–0x0054BB15`. No mutation of binary or project sources.

**Bounded scope:** one original **indirect CALL `0x0054B8DC`**, its immediate register/vtable source and return use, the enclosing function only to distinguish early/late vptr reads and listed intermediate call/write boundaries, and the user-supplied existing v751/v789/v791 and earlier v783 context. No global vtable/caller/writer sweep, no detailed callee analysis, new guest replay, native Windows/Wine launch, guest-state forcing, P-code/runtime/renderer change, or claims of rendered menus/races.

## 1. Exact CALL 0x0054B8DC: provenance, ABI and return EIP

The enclosing caller enters with **`ECX=S`**; `0x0054B8BE: MOV ESI,ECX` saves the containing-base pointer. `0x0054B8D2: LEA EDI,[ESI+4]` establishes **`O=EDI=S+4`**. At the early indirect call the original machine instructions, without any missing operation, are:

~~~asm
0054b8cc: 8b 46 04             mov    eax,DWORD PTR [esi+0x4]
0054b8cf: 8b 40 04             mov    eax,DWORD PTR [eax+0x4]
0054b8d2: 8d 7e 04             lea    edi,[esi+0x4]
0054b8d5: ba 0c 50 ac 00       mov    edx,0xac500c
0054b8da: 8b cf                mov    ecx,edi
0054b8dc: ff d0                call   eax
0054b8de: 8d 4d fc             lea    ecx,[ebp-0x4]
0054b8e1: 51                   push   ecx
~~~

Exact dataflow:
- `0x0054B8CC` reads **`V_early=DWORD[S+4]=DWORD[O]`** into EAX; `0x0054B8CF` reads **`F_early=DWORD[V_early+0x04]`** into EAX. This is the **runtime-loaded virtual-method pointer at byte offset +4**, vtable DWORD **index 1**.
- `0x0054B8D2` computes `O=S+4` in EDI **after** loading `F_early`, but from the **same S+4 address**. Thus the call's **ECX=O** at `0x0054B8DA`.
- `0x0054B8D5` overwrites EDX with literal **`0x00AC500C`**. The wrapper supplies an unchanged 32-bit register value; PE bytes alone do not specify that value's source-language type or dereference the pointed-to region here.
- **`CALL EAX` at `0x0054B8DC` has opcode `FF D0`, length two bytes.** The CPU pushes **return EIP `0x0054B8DE`**, *not `0x0054B8E1`*. The latter is a later `PUSH ECX` instruction reached only after the `LEA ECX,[EBP-4]` at `0x0054B8DE`.
- No `PUSH` instruction appears in this method's immediate argument preparation: **zero explicit newly pushed method arguments**. For this particular call, **outgoing register inputs are ECX=O and EDX=0x00AC500C**. EAX is the **target address**, not another method input. Any additional implicit, global, stack-frame or object fields required by the callee are unknown.
- The exact dynamically selected destination **`F_early` is not an immediate original PE target** and is not determined by these bytes. In particular, *nothing here establishes it is `0x005092F0` or the same target as later slot +0x0C*.

The enclosing function saves EBP, EBX, ESI and EDI and allocates `0x18` local stack bytes. Its eventual exit `0x0054BB15: RET` is a **plain `RET`**. At `0x0054B8DC`, because **the callsite pushes no method DWORD arguments**, there is **no visible outgoing method-argument cleanup** after return; `CALL` pushes one return address, which the callee's ordinary `RET` would pop under a compatible ABI. **The dynamic callee's prologue, own cleanup, semantic return type and effects are unknown.** There is no evidence from this site of a `RET imm16` requirement or a callee-cleaned positive number of callsite arguments. The earlier `PUSH 0x00ACC7E4` at `0x0054B8B9` is prepared for a **different** direct call `0x0054B8C0` and is **not** an argument to `0x0054B8DC`.

## 2. Does the caller use EAX returned from the early virtual call?

**No immediate consumer of that return value is present.** On normal return at **`0x0054B8DE`**, the caller executes:

~~~asm
0054b8de: 8d 4d fc             lea    ecx,[ebp-0x4]
0054b8e1: 51                   push   ecx
0054b8e2: 8d 55 f8             lea    edx,[ebp-0x8]
0054b8e5: 52                   push   edx
0054b8e6: e8 95 c6 fb ff       call   0x507f80
0054b8eb: 8b c8                mov    ecx,eax
0054b8ed: e8 ae 9a fb ff       call   0x5053a0
~~~

The `LEA/PUSH/LEA/PUSH` instructions leave EAX **unmodified** before `CALL 0x00507F80`, but **do not read or test it**. A direct call is then made with its own two pushed stack arguments `&[EBP-8]` and `&[EBP-4]` (right-to-left push order); `0x0054B8EB` uses *that later call's* EAX as ECX for `0x005053A0`, not a proved value from virtual slot +4. The dynamic slot +4 return is thus **not checked, compared or explicitly stored** in this caller. Since nested callee side effects are unknown, do not infer that its return represents a success flag, HRESULT, or a particular C++ method result.

## 3. Same vptr field as the later +0x0C call, but not proved same vptr value

The **static address of the loaded receiver vptr field** is identical at both sites:

| Property | Early `0x0054B8DC` | Later `0x0054BAC6` |
|---|---|---|
| Receiver | `ECX=EDI=O=S+4` | `ECX=EDI=O=S+4` |
| Pointer field read | `0x0054B8CC: DWORD[S+4]=DWORD[O]` | `0x0054BABF: DWORD[EDI]=DWORD[O]` |
| Slot lookup | `DWORD[V_early+0x04]` | `DWORD[V_late+0x0C]` |
| Outgoing register EDX | `0x00AC500C` | Holds the just-loaded `V_late` before CALL; no new EDX argument prepared |
| Explicit pushed method args | **0** | **0** |
| Return address | **`0x0054B8DE`** | `0x0054BAC8` |
| Known dynamic target from supplied trace | **unknown** | v783 observed **`0x005092F0`** for its particular invocation |

**PE-proven equality:** both *source addresses* are the same `DWORD[O]`. **Not PE-proven:** `V_early==V_late`. The early lookup happens **before** a virtual call that could itself modify O; then the enclosing function makes many additional calls with `ECX=O` including `0x00508F00`, `0x00509700` twice, `0x00509720` and `0x00509830`, numerous setup calls for S-relative member addresses, and nine insertion calls `0x005092E0`. At the end it **reloads** `DWORD[O]`. It does **not** reuse or cache V_early for the later lookup.

**Direct stores in this complete containing function:** explicit writes to `DWORD[S+0x1EE4]`, `DWORD[S+0x1EE8]`, later `FLOAT32[S+0x1EFC]` and `FLOAT32[S+0x1F00]`, `BYTE[S+0x1F04]` and on the relevant branch `DWORD[S+0x1EE0]`, plus local-stack/call argument effects. It contains **no direct instruction that writes `DWORD[S+4]=DWORD[O]`** or installs its vptr. Its calls, including the early dynamic slot +4 itself and helper/registering functions, **can have indirect effects that these PE instructions do not resolve**. Therefore no stronger nonmutation claim about the pointer field is justified. Two same-address reads separated by unknown callees **do not prove equality of the data read**.

**Source-level interface limit:** the calling convention is compatible with a receiver-oriented C++-style register virtual method, but this code does **not identify the class, COM interface, method name, vptr producer or exact target EIP**. It is **not** valid to assign the previously seen later writer `0x005092F0` to early +4 merely because both slots use O.

## 4. Existing v751/v789/v791 evidence: precise missing observation

The user asks whether an **already supplied, verified runtime event for `return_address=0x0054B8E1`** identifies the early call's target. **No such verified event is available in the supplied bounded facts for v751, v789 or v791. Its target is unknown.** The current assignment does **not** initiate a new trace or comb unprovided/full logs, and absence from the accessible summaries is **not** proof the function never executed.

Furthermore, **`0x0054B8E1` is not the correct return address of this CALL**. Its correct machine return EIP is **`0x0054B8DE`**. Even if another trace records `return_address=0x0054B8E1`, that field **would not by itself identify** this specific `FF D0` callsite; its trace schema and precise originating instruction would need independent correlation. Neither that address nor the later known `0x0054BAC8` should be substituted for `0x0054B8DE`.

**Relevant supplied controlled replay facts, kept separate:**
- **v783** reports a **different**, **postregistration slot +0x0C** dispatch with target/writer `0x005092F0` and return address **`0x0054BAC8`**. These paired target/return fields connect `0x0054BAC6` to writer in the observed run, **not the earlier `0x0054B8DC` call**.
- **v791**, original PE under Linux P-code guest runtime, reports 360 host frames, exit 0, **1,751,486 dispatches / 4,733 functions**, zero Vulkan validation errors, untruncated trace, and repetition of count=9, guard AL=0, readiness `BYTE[O+0x2D]=0`. Its `guest_draw_translation=false` and `retail_rendering_proven=false` are explicit limitations. The supplied v791 summary does **not** identify a slot +4 target or a return `0x0054B8DE`.
- No specific matching slot +4 target/return pair is supplied here for **v751** or **v789**. Saying **unknown** is warranted; saying those complete runs lacked the call is **not warranted**.

This report neither instruments the site nor upgrades indirect or absent evidence into runtime EIP. No native Windows/Wine, rendered menu, race or retail GPU reachability claim follows.

## 5. Bounded role before nine registrations, return and state effects

The early virtual call occurs **before** the successive owner-relative item registrations `0x0054BA56` through `0x0054BABA`. It receives **O and constant EDX=0x00AC500C**, supporting only a *possible initialization/configuration-like role by placement*. Such a semantic label remains inference: no complete dynamic callee implementation or return status is available. The earlier caller code `0x0054B8B9–0x0054B8C7` also calls direct setup-like functions before loading V_early, but these calls are not analyzed here.

What is byte-proven within the callsite itself: **two pointer reads, register setup, a single indirect CALL and no direct object store, argument validation, return-status check, queue manipulation, readiness write or Draw* call**. Any memory/state effects of the dynamically selected target are **out of scope and unresolved**. That it precedes list registration does not prove that it initialized `DWORD[O+0x14]`, installed `DWORD[O]`, constructed nine UI entries or set `BYTE[O+0x2D]`.

The previously supported *later* path is different: nine insertions increment `DWORD[O+0x14]`, a particular v783 later slot +0xC invocation chose `0x005092F0`, which tests count via guard `0x00554050` and can reset `BYTE[O+0x2D]`. There is **no byte-grounded path in this early CALL alone** establishing the same readiness reset or the cause of progress=30.

## 6. Exactly one next evidence-backed target

**`0x00508F00` — the first named direct **O-receiver** helper called at `0x0054B903` after this early vptr slot.** This is the single next proposed separate bounded PE audit, not a global search. It is evidenced by:

~~~asm
0054b8f9: 8b 55 f8              mov    edx,DWORD PTR [ebp-0x8]
0054b8fc: 50                    push   eax
0054b8fd: 8b 45 fc              mov    eax,DWORD PTR [ebp-0x4]
0054b900: 50                    push   eax
0054b901: 8b cf                 mov    ecx,edi
0054b903: e8 f8 d5 fb ff       call   0x508f00
~~~

It receives **`ECX=O`**, **`EDX=DWORD[EBP-8]`**, and two explicit stack DWORDs at that callsite. A later bounded study of the *single* direct callee could answer whether it writes `DWORD[O]` or other setup fields before item registration; **no such write is inferred in this report**. It is the **only** next target; the unknown early slot +4 method is **not** assigned a guessed static PE address.

## Appendix A — full original containing retail function 0x0054B8B0–0x0054BB15 (167 instructions, all machine bytes)

~~~asm
0054b8b0: 55                   push   ebp
0054b8b1: 8b ec                mov    ebp,esp
0054b8b3: 83 ec 18             sub    esp,0x18
0054b8b6: 53                   push   ebx
0054b8b7: 56                   push   esi
0054b8b8: 57                   push   edi
0054b8b9: 68 e4 c7 ac 00       push   0xacc7e4
0054b8be: 8b f1                mov    esi,ecx
0054b8c0: e8 bb c6 fb ff       call   0x507f80
0054b8c5: 8b c8                mov    ecx,eax
0054b8c7: e8 04 c6 fb ff       call   0x507ed0
0054b8cc: 8b 46 04             mov    eax,DWORD PTR [esi+0x4]
0054b8cf: 8b 40 04             mov    eax,DWORD PTR [eax+0x4]
0054b8d2: 8d 7e 04             lea    edi,[esi+0x4]
0054b8d5: ba 0c 50 ac 00       mov    edx,0xac500c
0054b8da: 8b cf                mov    ecx,edi
0054b8dc: ff d0                call   eax
0054b8de: 8d 4d fc             lea    ecx,[ebp-0x4]
0054b8e1: 51                   push   ecx
0054b8e2: 8d 55 f8             lea    edx,[ebp-0x8]
0054b8e5: 52                   push   edx
0054b8e6: e8 95 c6 fb ff       call   0x507f80
0054b8eb: 8b c8                mov    ecx,eax
0054b8ed: e8 ae 9a fb ff       call   0x5053a0
0054b8f2: 33 c9                xor    ecx,ecx
0054b8f4: e8 a7 28 0e 00       call   0x62e1a0
0054b8f9: 8b 55 f8             mov    edx,DWORD PTR [ebp-0x8]
0054b8fc: 50                   push   eax
0054b8fd: 8b 45 fc             mov    eax,DWORD PTR [ebp-0x4]
0054b900: 50                   push   eax
0054b901: 8b cf                mov    ecx,edi
0054b903: e8 f8 d5 fb ff       call   0x508f00
0054b908: ba 00 00 30 00       mov    edx,0x300000
0054b90d: 8b cf                mov    ecx,edi
0054b90f: e8 ec dd fb ff       call   0x509700
0054b914: ba 00 00 30 00       mov    edx,0x300000
0054b919: 8b cf                mov    ecx,edi
0054b91b: e8 e0 dd fb ff       call   0x509700
0054b920: 83 ca ff             or     edx,0xffffffff
0054b923: 8b cf                mov    ecx,edi
0054b925: e8 f6 dd fb ff       call   0x509720
0054b92a: 8b cf                mov    ecx,edi
0054b92c: e8 ff de fb ff       call   0x509830
0054b931: b9 28 a8 aa 00       mov    ecx,0xaaa828
0054b936: e8 65 28 0e 00       call   0x62e1a0
0054b93b: 33 c9                xor    ecx,ecx
0054b93d: 89 86 e4 1e 00 00    mov    DWORD PTR [esi+0x1ee4],eax
0054b943: e8 58 28 0e 00       call   0x62e1a0
0054b948: 89 86 e8 1e 00 00    mov    DWORD PTR [esi+0x1ee8],eax
0054b94e: e8 2d c6 fb ff       call   0x507f80
0054b953: 8b 8e e4 1e 00 00    mov    ecx,DWORD PTR [esi+0x1ee4]
0054b959: 6a 01                push   0x1
0054b95b: 51                   push   ecx
0054b95c: 05 74 17 00 00       add    eax,0x1774
0054b961: 50                   push   eax
0054b962: 8d 9e 80 11 00 00    lea    ebx,[esi+0x1180]
0054b968: 68 c4 c7 ac 00       push   0xacc7c4
0054b96d: ba b0 c7 ac 00       mov    edx,0xacc7b0
0054b972: 8b cb                mov    ecx,ebx
0054b974: e8 27 d1 fb ff       call   0x508aa0
0054b979: e8 02 c6 fb ff       call   0x507f80
0054b97e: 8b 96 e4 1e 00 00    mov    edx,DWORD PTR [esi+0x1ee4]
0054b984: 6a 00                push   0x0
0054b986: 52                   push   edx
0054b987: 05 74 17 00 00       add    eax,0x1774
0054b98c: 50                   push   eax
0054b98d: 8d 8e e0 0a 00 00    lea    ecx,[esi+0xae0]
0054b993: 68 90 c7 ac 00       push   0xacc790
0054b998: ba 84 c7 ac 00       mov    edx,0xacc784
0054b99d: e8 fe d0 fb ff       call   0x508aa0
0054b9a2: 8b 86 e4 1e 00 00    mov    eax,DWORD PTR [esi+0x1ee4]
0054b9a8: 6a 01                push   0x1
0054b9aa: 50                   push   eax
0054b9ab: e8 e0 cf 0f 00       call   0x648990
0054b9b0: 8b c8                mov    ecx,eax
0054b9b2: e8 89 cf 0f 00       call   0x648940
0054b9b7: 50                   push   eax
0054b9b8: 68 68 c7 ac 00       push   0xacc768
0054b9bd: ba 58 c7 ac 00       mov    edx,0xacc758
0054b9c2: 8d 8e 80 07 00 00    lea    ecx,[esi+0x780]
0054b9c8: e8 d3 d0 fb ff       call   0x508aa0
0054b9cd: 8b 8e e4 1e 00 00    mov    ecx,DWORD PTR [esi+0x1ee4]
0054b9d3: 6a 01                push   0x1
0054b9d5: 51                   push   ecx
0054b9d6: e8 b5 cf 0f 00       call   0x648990
0054b9db: 8b c8                mov    ecx,eax
0054b9dd: e8 5e cf 0f 00       call   0x648940
0054b9e2: 50                   push   eax
0054b9e3: 68 2c c7 ac 00       push   0xacc72c
0054b9e8: ba 30 be ab 00       mov    edx,0xabbe30
0054b9ed: 8d 8e c0 00 00 00    lea    ecx,[esi+0xc0]
0054b9f3: e8 a8 d0 fb ff       call   0x508aa0
0054b9f8: 8b 96 e4 1e 00 00    mov    edx,DWORD PTR [esi+0x1ee4]
0054b9fe: 6a 01                push   0x1
0054ba00: 52                   push   edx
0054ba01: e8 8a cf 0f 00       call   0x648990
0054ba06: 8b c8                mov    ecx,eax
0054ba08: e8 33 cf 0f 00       call   0x648940
0054ba0d: 50                   push   eax
0054ba0e: 68 80 50 ac 00       push   0xac5080
0054ba13: ba 1c c7 ac 00       mov    edx,0xacc71c
0054ba18: 8d 8e 20 04 00 00    lea    ecx,[esi+0x420]
0054ba1e: e8 7d d0 fb ff       call   0x508aa0
0054ba23: 8b 86 e4 1e 00 00    mov    eax,DWORD PTR [esi+0x1ee4]
0054ba29: 6a 01                push   0x1
0054ba2b: 50                   push   eax
0054ba2c: e8 5f cf 0f 00       call   0x648990
0054ba31: 8b c8                mov    ecx,eax
0054ba33: e8 08 cf 0f 00       call   0x648940
0054ba38: 50                   push   eax
0054ba39: 68 04 c7 ac 00       push   0xacc704
0054ba3e: ba fc c6 ac 00       mov    edx,0xacc6fc
0054ba43: 8d 8e 80 1b 00 00    lea    ecx,[esi+0x1b80]
0054ba49: e8 52 d0 fb ff       call   0x508aa0
0054ba4e: 8d 96 80 07 00 00    lea    edx,[esi+0x780]
0054ba54: 8b cf                mov    ecx,edi
0054ba56: e8 85 d8 fb ff       call   0x5092e0
0054ba5b: 8d 96 40 18 00 00    lea    edx,[esi+0x1840]
0054ba61: 8b cf                mov    ecx,edi
0054ba63: e8 78 d8 fb ff       call   0x5092e0
0054ba68: 8d 96 80 1b 00 00    lea    edx,[esi+0x1b80]
0054ba6e: 8b cf                mov    ecx,edi
0054ba70: e8 6b d8 fb ff       call   0x5092e0
0054ba75: 8b d3                mov    edx,ebx
0054ba77: 8b cf                mov    ecx,edi
0054ba79: e8 62 d8 fb ff       call   0x5092e0
0054ba7e: 8d 96 c0 00 00 00    lea    edx,[esi+0xc0]
0054ba84: 8b cf                mov    ecx,edi
0054ba86: e8 55 d8 fb ff       call   0x5092e0
0054ba8b: 8d 96 20 04 00 00    lea    edx,[esi+0x420]
0054ba91: 8b cf                mov    ecx,edi
0054ba93: e8 48 d8 fb ff       call   0x5092e0
0054ba98: 8d 96 e0 0a 00 00    lea    edx,[esi+0xae0]
0054ba9e: 8b cf                mov    ecx,edi
0054baa0: e8 3b d8 fb ff       call   0x5092e0
0054baa5: 8d 96 e0 14 00 00    lea    edx,[esi+0x14e0]
0054baab: 8b cf                mov    ecx,edi
0054baad: e8 2e d8 fb ff       call   0x5092e0
0054bab2: 8d 96 40 0e 00 00    lea    edx,[esi+0xe40]
0054bab8: 8b cf                mov    ecx,edi
0054baba: e8 21 d8 fb ff       call   0x5092e0
0054babf: 8b 17                mov    edx,DWORD PTR [edi]
0054bac1: 8b 42 0c             mov    eax,DWORD PTR [edx+0xc]
0054bac4: 8b cf                mov    ecx,edi
0054bac6: ff d0                call   eax
0054bac8: d9 ee                fldz
0054baca: 83 be e0 1e 00 00 00 cmp    DWORD PTR [esi+0x1ee0],0x0
0054bad1: d9 96 fc 1e 00 00    fst    DWORD PTR [esi+0x1efc]
0054bad7: d9 9e 00 1f 00 00    fstp   DWORD PTR [esi+0x1f00]
0054badd: c6 86 04 1f 00 00 00 mov    BYTE PTR [esi+0x1f04],0x0
0054bae4: 75 29                jne    0x54bb0f
0054bae6: 8d 4d e8             lea    ecx,[ebp-0x18]
0054bae9: e8 e2 af 2e 00       call   0x836ad0
0054baee: 8b 0d 58 60 c2 00    mov    ecx,DWORD PTR ds:0xc26058
0054baf4: 8b 01                mov    eax,DWORD PTR [ecx]
0054baf6: 8b 80 c4 01 00 00    mov    eax,DWORD PTR [eax+0x1c4]
0054bafc: 8d 55 e8             lea    edx,[ebp-0x18]
0054baff: ff d0                call   eax
0054bb01: 8d 4d e8             lea    ecx,[ebp-0x18]
0054bb04: 89 86 e0 1e 00 00    mov    DWORD PTR [esi+0x1ee0],eax
0054bb0a: e8 e1 82 3a 00       call   0x8f3df0
0054bb0f: 5f                   pop    edi
0054bb10: 5e                   pop    esi
0054bb11: 5b                   pop    ebx
0054bb12: 8b e5                mov    esp,ebp
0054bb14: 5d                   pop    ebp
0054bb15: c3                   ret
~~~

## Appendix B — exact focused callsite and postreturn instructions

~~~asm
0054b8cc: 8b 46 04              mov    eax,DWORD PTR [esi+0x4]
0054b8cf: 8b 40 04              mov    eax,DWORD PTR [eax+0x4]
0054b8d2: 8d 7e 04              lea    edi,[esi+0x4]
0054b8d5: ba 0c 50 ac 00        mov    edx,0xac500c
0054b8da: 8b cf                 mov    ecx,edi
0054b8dc: ff d0                 call   eax
0054b8de: 8d 4d fc              lea    ecx,[ebp-0x4]
0054b8e1: 51                    push   ecx
0054b8e2: 8d 55 f8              lea    edx,[ebp-0x8]
0054b8e5: 52                    push   edx
0054b8e6: e8 95 c6 fb ff        call   0x507f80
0054b8eb: 8b c8                 mov    ecx,eax
0054b8ed: e8 ae 9a fb ff        call   0x5053a0
~~~

**Single Markdown report only.** No source/runtime/P-code/renderer/guest-state edits, new replay, native launch or PR.
