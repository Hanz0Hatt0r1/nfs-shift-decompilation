# Process 1b — UI item insertion payload at 0x0054BABA / complete caller 0x0054B8B0 (v788 context)

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86; ImageBase `0x00400000`, SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**. Original PE hash was independently verified locally; full caller's PE disassembly matches the supplied verified objdump and was independently spot-checked against local GNU objdump, including the entire nine-call registration sequence and exit. This is a strictly bounded static inspection combined only with **previously supplied** controlled P-code guest replay v788; no new runtime execution, replay, native Windows/Wine launch or guest-state forcing.

**Scope:** exactly the original retail function `0x0054B8B0–0x0054BB15`, especially `0x0054BABA` and its source payload register, with only the accepted `0x005092E0` tail thunk / `0x004F5E60` producer ABI used as prior proof. No global caller/writer/class/vtable sweep, no deep investigation of the other direct calls, no modifications to source, P-code, runtime, renderer or guest state. The prior published producer report remains the bounded authoritative reference.

## 1. ABI and exact source/payload/counter join

The full caller is entered with a receiver/base pointer **`ECX=S`**, captured by `0x0054B8BE: MOV ESI,ECX`. It has a standard EBP frame with `SUB ESP,0x18` (24 bytes of local storage), and saves EBX, ESI, EDI. It does **not** read explicit incoming stack parameters: there are no `[EBP+8]` (or higher) parameter loads. Initial EDX is not a demonstrated input to the caller; it is overwritten for downstream calls. At `0x0054B8D2: LEA EDI,[ESI+4]`, **`O=EDI=S+4`** remains the common receiver for the nine insertion sites.

At the **ninth exact site**, the original bytes are:

~~~asm
0054bab2: 8d 96 40 0e 00 00   lea    edx,[esi+0xe40]
0054bab8: 8b cf               mov    ecx,edi
0054baba: e8 21 d8 fb ff      call   0x5092e0
0054babf: 8b 17               mov    edx,DWORD PTR [edi]
~~~

There is **no PUSH for explicit arguments** to this call. The register values are `ECX=O=S+4` and **`EDX=P=S+0xE40=O+0xE3C`**. The 5-byte CALL at `0x0054BABA` gives the exact return address **`0x0054BABF`**, independently matching the user-supplied v788 last-writer record.

The proven tail thunk `0x005092E0: ADD ECX,8; JMP 0x004F5E60` (not CALL) forwards **`ECX=C=O+8=S+0xC`** with **EDX=P unchanged**. It neither creates a second return address nor adds caller arguments. The insertion producer `0x004F5E60` saves `EDX` as the incoming payload, obtains a node pointer `N`, writes **`DWORD[N+0xC]=P`** at `0x004F5EA3`, then executes **`0x004F5EA5: ADD DWORD[C+0xC],1`**. This is precisely `DWORD[O+0x14] = DWORD[S+0x18]`. The producer's normal `RET` returns directly to `0x0054BABF` with **EAX=N+0xC** (address of payload slot, *not* HRESULT/count). The caller does not inspect the producer's returned EAX at this site; it next reads `DWORD[O]`.

~~~text
S = incoming ECX of caller 0x0054B8B0
O = EDI = S+0x04
P = EDX = S+0xE40 = O+0xE3C
C = O+0x08 = S+0x0C         (container receiver of producer)
count address = C+0x0C = O+0x14 = S+0x18
node payload store = DWORD[N+0x0C] = P
tail JMP preserves source CALL return address 0x0054BABF
~~~

For the **supplied v788 object `O=0x27DFA5FC`**, arithmetic gives **`S=0x27DFA5F8`**, **`C=0x27DFA604`**, **`P=0x27DFB438`**, and **count address `0x27DFA610`**. This calculated `P` was not independently captured as a runtime register in this task.

**Normal cleanup:** full caller restores EDI/ESI/EBX, `MOV ESP,EBP; POP EBP; RET` at `0x0054BB0F–0x0054BB15` (plain `RET`, no immediate); thunk is a JMP; producer ends in plain `RET`. The separate nested calls are expected to respect their individual ABIs. The full caller does not set a final fixed EAX value: it may carry a downstream call's result; do not label its EAX as bool/HRESULT based on this body.

## 2. Exactly nine direct tail-thunk calls in the complete original caller

After earlier setup, the original caller performs **nine straight-line calls** to `0x005092E0`, all with `ECX=EDI=O` and these nine *distinct* derived `EDX` pointer values. They are consecutive registrations with **no branch or loop within this group**:

| Ordinal | Retail CALL EIP | Outgoing EDX payload | Preparation |
|---:|---|---|---|
| 1 | `0x0054BA56` | `S+0x780` | `0x0054BA4E LEA EDX,[ESI+0x780]` |
| 2 | `0x0054BA63` | `S+0x1840` | `0x0054BA5B LEA EDX,[ESI+0x1840]` |
| 3 | `0x0054BA70` | `S+0x1B80` | `0x0054BA68 LEA EDX,[ESI+0x1B80]` |
| 4 | `0x0054BA79` | `S+0x1180` | `0x0054BA75 MOV EDX,EBX`; `EBX=S+0x1180` from `0x0054B962` |
| 5 | `0x0054BA86` | `S+0xC0` | `0x0054BA7E LEA EDX,[ESI+0xC0]` |
| 6 | `0x0054BA93` | `S+0x420` | `0x0054BA8B LEA EDX,[ESI+0x420]` |
| 7 | `0x0054BAA0` | `S+0xAE0` | `0x0054BA98 LEA EDX,[ESI+0xAE0]` |
| 8 | `0x0054BAAD` | `S+0x14E0` | `0x0054BAA5 LEA EDX,[ESI+0x14E0]` |
| 9 | **`0x0054BABA`** | **`S+0xE40`** | **`0x0054BAB2 LEA EDX,[ESI+0xE40]`** |

The proven insertion producer increments the **same** `DWORD[C+0xC]=DWORD[O+0x14]` upon normal completion of each registration. Thus **nine calls provide a direct, parsimonious explanation for the observed count 9**, *conditional* on suitable initial count and no other modifications. The original caller and this trace **do not prove** initial count 0, absence of side effects in downstream helpers, nine currently valid elements, or universal correctness of the list structure.

## 3. Preparation and use of ESI-relative regions in this one caller

**Bytes prove a receiver pointer, not a C++ declaration:** at `0x0054B8CC` the caller loads `DWORD[S+4]`, reads a function pointer at `[DWORD[S+4]+4]`, and calls it with `ECX=O=S+4` and `EDX=0xAC500C` (`0x0054B8DC`). Then `0x0054B903` calls `0x00508F00` with `ECX=O` and two pushed values. There are subsequent direct calls `0x00509700` (twice, `EDX=0x300000`), `0x00509720` (`EDX=0xFFFFFFFF`) and `0x00509830` with `ECX=O`. These are **call boundaries**, not proof of particular UI lifecycle or effects; their bodies are intentionally not analyzed.

**Direct stores proven in this caller:** `0x0054B93D` writes EAX to `DWORD[S+0x1EE4]` and `0x0054B948` writes EAX to `DWORD[S+0x1EE8]`. At later tail `0x0054BAD1–0x0054BADD` it writes floating zero to `FLOAT32[S+0x1EFC]` and `FLOAT32[S+0x1F00]` and byte zero to `BYTE[S+0x1F04]`; conditional body `0x0054BB04` writes `DWORD[S+0x1EE0]`. **None is a direct write to `[S+0xE40]` or `BYTE[O+0x2D]=BYTE[S+0x31]`**.

**Original preparation-like calls with ECX equal to individual owner-relative addresses:**

| Original `CALL 0x00508AA0` site | Proven ECX receiver address | Further outgoing values (not type proof) |
|---|---|---|
| `0x0054B974` | `S+0x1180` (saved in EBX) | EDX=`0xACC7B0`, 4 pushed DWORDs |
| `0x0054B99D` | `S+0xAE0` | EDX=`0xACC784`, 4 pushed DWORDs |
| `0x0054B9C8` | `S+0x780` | EDX=`0xACC758`, 2 pushed DWORDs |
| `0x0054B9F3` | `S+0xC0` | EDX=`0xABBE30`, 2 pushed DWORDs |
| `0x0054BA1E` | `S+0x420` | EDX=`0xACC71C`, 2 pushed DWORDs |
| `0x0054BA49` | `S+0x1B80` | EDX=`0xACC6FC`, 2 pushed DWORDs |

These are exactly **six** such calls in the bounded function. Their receivers are *candidate embedded members* by pointer arithmetic; whether `0x00508AA0` constructs, binds, registers or writes vptrs cannot be settled without its body, intentionally excluded here.

**Crucial `S+0xE40` negative finding:** the full caller contains just **one literal use of displacement `0xE40`**, the `LEA EDX,[ESI+0xE40]` at `0x0054BAB2`. It has **no direct initialization/store to `DWORD[S+0xE40]`, no read from that address, no vptr load through `S+0xE40`, and no `CALL 0x00508AA0` with ECX=`S+0xE40`**. Likewise the offsets `+0x14E0` and `+0x1840` are registered here without corresponding visible `0x00508AA0` calls. It is **not justified** to claim they were never initialized elsewhere or that indirect calls here could not mutate them via other pointers.

**Type and allocation conclusion:**
- **Byte-proven:** P is an address **computed by LEA within S-relative storage**, *not* a pointer fetched from `DWORD[S+0xE40]` and *not* a returned heap allocation pointer on this callsite. The producer writes the address as the node payload.
- **Inference:** it is a plausible inline member/subobject address in a larger owner-shaped object because numerous different S-relative offsets are passed into the same registration thunk.
- **Not proven:** `S` allocation origin (heap/stack/global), extent/validity of the containing storage, a constructed C++ subobject at P, its class/vptr, interface type, UI callback/entry identity, ownership/lifetime, initialization completion or effects of indirect helpers. The full caller has no direct vptr write to `P` and makes no virtual call using `P` itself.

## 4. Postregistration dispatch and bounded link to v788 readiness reset

Directly **after the ninth insertion**, the caller does:

~~~asm
0054babf: 8b 17                mov    edx,DWORD PTR [edi]
0054bac1: 8b 42 0c             mov    eax,DWORD PTR [edx+0xc]
0054bac4: 8b cf                mov    ecx,edi
0054bac6: ff d0                call   eax
0054bac8: d9 ee                fldz
~~~

So `0x0054BAC6` uses **`ECX=O`** and dynamic **`F=DWORD[DWORD[O]+0xC]`**; exact `F` cannot be determined from this static PE fragment. Previously supplied v783 writer provenance reported writer `0x005092F0` with caller `0x0054B8B0` and return `0x0054BAC8`, consistent with this virtual dispatch in that replay. **Do not promote that observation to a universal static vtable identity.**

**PE plus accepted v788 facts:** the supplied v788 P-code guest trace (120 frames, exit 0, zero Vulkan validation errors, 815451 dispatches, 3934 unique functions, 23 untruncated events, full v659 manifest) attributes an exact 4-byte write of **9** to `0x004F5E60` at `0x27DFA610`, dispatch `461055`, reported thunk `0x005092E0`, call return `0x0054BABF`, thread `0x00177D80`. For `O=0x27DFA5FC` this count address is precisely `O+0x14`. The previously accepted guard on dispatch `461057` read **9**, returned `EAX=0x00509200` with **AL=0**; the writer `0x005092F0` tests AL and when zero executes **`BYTE[O+0x2D]=0`**. Prior v787 independently observed count 9 and AL=0. This correlates source pointer, list-counter increment, guard and reset **for the reported bounded replay**, not for native Windows/Wine or all frames.

**What remains unproved:** whether exactly nine *live* UI elements exist, whether item number nine is required for readiness reset (the guard simply tests *nonzero count*), whether the owner subobjects are valid UI callbacks, why progress reached 30, whether `BYTE[O+0x2D]` is later set positive by another function, or any retail renderer reachability. Both replay configurations reported `guest_draw_translation=false` and `retail_rendering_proven=false`; **no menu/race, draw or native game-execution claim is made**.

## 5. Evidence ledger and boundary

**Original PE facts:** exact SHA-256, full function in Appendix A, nine direct `CALL 0x5092E0` sites, `ESI=S` and `EDI=S+4`, ninth `EDX=S+0xE40` with `ECX=O`, return `0x0054BABF`; thunk `ECX+=8`, producer stores `EDX` into `[N+0xC]` and increments `DWORD[O+0x14]`. Immediate postregistration virtual dispatch `O.vptr+0xC` followed by distinct state-field zero writes. No direct S+E40 initialization within the complete caller.

**User-provided observed evidence:** values/dispatch/thread/return address from v788 and v787, not reproduced here. The numerical P address is a deduction from the recorded O and PE arithmetic, not separately observed.

**Inference only:** candidate inline-subobject/registration, count as list-size approximation, unspecified initialization paths. No global semantics, successful native game activity, complete object lifetime or Draw* claims.

## 6. Exactly one next evidence-backed target

**`0x0054BAC6` — the immediate virtual dispatch `DWORD[DWORD[O]+0x0C]` after all nine insertions.** Exactly this one target is warranted by (a) the retail PE's EIP and `ECX=O` receiver, (b) exact `0x0054BAC8` return address matching the prior writer-provenance observation, and (c) its position directly after the ninth count increment. In a *separate bounded task*, resolve the specific receiver-vptr/slot provenance and whether v783 observed this call to writer `0x005092F0`, without a global vtable/caller sweep. Do **not** make any guest-state changes or broaden this present task to callee internals.

## Appendix A — complete original retail function 0x0054B8B0–0x0054BB15

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

## Appendix B — original narrow tail-thunk and count-producing instructions (bounded provenance only)

~~~asm
005092e0: 83 c1 08              add    ecx,0x8
005092e3: e9 78 cb fe ff       jmp    0x4f5e60

004f5e60: 56                   push   esi
004f5e61: 8b f1                mov    esi,ecx
004f5e67: 8b fa                mov    edi,edx
004f5e7f: 8b ce                mov    ecx,esi
004f5e81: e8 9a 14 f3 ff       call   0x427320
004f5ea0: 83 c0 0c             add    eax,0xc
004f5ea3: 89 38                mov    DWORD PTR [eax],edi
004f5ea5: 83 46 0c 01          add    DWORD PTR [esi+0xc],0x1
004f5ea9: 5f                   pop    edi
004f5eaa: 5e                   pop    esi
004f5eab: c3                   ret
~~~

**Publication:** this Markdown file only on `work/process-reports`. No source/runtime/P-code/renderer/guest-state modifications; no replay.
