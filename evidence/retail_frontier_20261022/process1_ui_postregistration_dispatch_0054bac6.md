# Process 1b — bounded postregistration virtual dispatch at 0x0054BAC6 (retail PE; v783/v791)

**Date:** 2026-10-22. **Original binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`; original `/mnt/data/SHIFT.exe` SHA-256 **`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`**. The full 167-instruction caller `0x0054B8B0–0x0054BB15`, including exact byte addresses, was independently checked via GNU objdump against the original PE. Its entire machine-code block is in Appendix A.

**Scope:** only the **postregistration callsite `0x0054BAC6`** and the complete containing retail caller for control-flow/context, plus previously verified immediate guard/writer evidence and user-supplied finite P-code guest replay observations. Do **not** treat the prior item-producer/caller investigation as an active task or deepen other functions. No global vtable/caller/writer sweep, source modifications, P-code/runtime/renderer/guest-state edits, forced values, new replay, native Windows/Wine launch or claim of rendered UI/race.

## 1. Exact PE dataflow, receiver, vtable source and stack shape

At full caller entry `0x0054B8BE: MOV ESI,ECX` sets `S=incoming ECX`; `0x0054B8D2: LEA EDI,[ESI+4]` sets **`O=EDI=S+4`**. The nine consecutive insertion sites `0x0054BA56, BA63, BA70, BA79, BA86, BA93, BAA0, BAAD, BABA` all pass this **same `ECX=EDI=O`** to direct tail thunk `0x005092E0` with distinct member-like payload addresses in EDX. This register relationship is from *retail instructions*, not a C++ class assertion.

**Exactly at the requested site, four consecutive instructions:**

~~~asm
0054babf: 8b 17              mov    edx,DWORD PTR [edi]
0054bac1: 8b 42 0c           mov    eax,DWORD PTR [edx+0xc]
0054bac4: 8b cf              mov    ecx,edi
0054bac6: ff d0              call   eax
0054bac8: d9 ee              fldz
~~~

Let `V=DWORD[O]` and `F=DWORD[V+0x0C]`. The literal PE computes **`EDX=V`**, **`EAX=F`**, **`ECX=O`**, then **`CALL EAX`**. The slot offset is **`+0x0C`**, i.e. DWORD slot **index 3** in the *specific runtime object vtable*. The code uses a **runtime-loaded function pointer**: **`0x005092F0` is not encoded** in these instructions and cannot be inferred as the unique target from PE bytes alone.

**Outgoing call ABI:** receiver is passed in register **ECX=O**. No PUSH is made in the entire immediate call preparation `0x0054BABF–0x0054BAC6`, and **no explicit stack arguments** are supplied for this call. The CPU `CALL` pushes **return EIP `0x0054BAC8`** onto the stack; this is *not* a user-method argument. Existing saved caller frame/locals do not become newly pushed call arguments. The previously studied concrete writer `0x005092F0` accepts its object in ECX, reads no explicit stack arguments, and ends with ordinary `RET`; thus its ABI is **compatible** with this dispatch. No exact source-level class/method name or method signature beyond register receiver/no new args is justified by PE bytes.

The **vtable pointer itself** comes from **`DWORD[O]`**, not `DWORD[S]`, `S+0xE40` or the list node. No extra pointer dereference beyond `DWORD[O]` and `DWORD[V+0xC]` is present. The same O storage is referenced at the earlier bounded indirect call `0x0054B8DC` (there `EAX=DWORD[DWORD[S+4]+4]`); intervening calls could alter the vptr, so the two lookups must **not** be asserted to have the same runtime V unless independently observed.

## 2. v783: evidence of the selected target for this **particular** dispatch

**User-supplied v783 controlled replay observation**, not independently repeated: original retail PE executed in a **Linux P-code guest runtime**, not native Windows/Wine. It recorded the **target/writer function `0x005092F0`**, **caller function `0x0054B8B0`**, **return address `0x0054BAC8`**, observed original object **`O=0x27DFA5FC`**, and its readiness-byte provenance **`BYTE[O+0x2D]=0`** from that target; reported thread **`0x00175C45`** and associated writer dispatch **461058**. The earlier v783 context also reported guard reading nonzero list-count and AL=0. These are **specific linked trace fields**, not a claim about other runs.

**Why this identifies this callsite in the observed trace:** the PE instruction **`0x0054BAC6: FF D0 CALL EAX`** is a two-byte call, so the actual return address is **`0x0054BAC8`**. The recorded **observed target EIP `0x005092F0`** combined with **call-return address `0x0054BAC8`**, containing caller `0x0054B8B0`, and object/receiver O matches the slot-3 call whose source is `DWORD[DWORD[O]+0xC]`. The attribution is **not inferred solely from writer `0x005092F0` having written `O+0x2D`**; the target plus return address and caller/receiver are the discriminating evidence.

**Conclusion at appropriate level:** v783 **supports that this exact dynamic callsite selected `0x005092F0`** in its observed invocation; the PE independently proves the callsite's instruction and ABI. It does **not** prove `DWORD[DWORD[O]+0xC]` is fixed at `0x005092F0` for every instance, lifetime, replay or alternate receiver, or identify an original vtable cell/constructor that this task has not inspected.

**v791 (different user-supplied controlled replay):** 360 host frames to host-frame-loop, exit 0, **1,751,486 P-code dispatches**, **4,733 functions**, **0 Vulkan validation errors**, untruncated trace. It independently repeated **count=9, guard AL=0, byte zero store**; **`guest_draw_translation=false`**, **`retail_rendering_proven=false`**. Those fields corroborate the observed bounded predicate/write chain, but **v791 is not independently stated to have recorded this site's concrete virtual-call target**; do not substitute the v783 target provenance for a v791 trace event. Neither trace demonstrates menus, racing, native graphics, or an intrinsic rendering failure cause.

## 3. Is EAX consumed after CALL? Exact continuation and return nuance

On normal return from dynamic `CALL` at `0x0054BAC6`, EIP resumes **`0x0054BAC8`**. The return register is **not compared, tested, stored, or passed as a deliberate input** by the immediate caller continuation:

~~~asm
0054bac8: d9 ee                    fldz
0054baca: 83 be e0 1e 00 00 00    cmp    DWORD PTR [esi+0x1ee0],0x0
0054bad1: d9 96 fc 1e 00 00       fst    DWORD PTR [esi+0x1efc]
0054bad7: d9 9e 00 1f 00 00       fstp   DWORD PTR [esi+0x1f00]
0054badd: c6 86 04 1f 00 00 00    mov    BYTE PTR [esi+0x1f04],0x0
0054bae4: 75 29                   jne    0x54bb0f
~~~

The **conditional jump** reads flags from **`CMP DWORD[S+0x1EE0],0`**, not flags/status from the previous virtual call. The x87 instructions push/write **+0.0** to `FLOAT32[S+0x1EFC]` and `FLOAT32[S+0x1F00]`; the explicit byte store writes **`BYTE[S+0x1F04]=0`**. None modifies EAX. Do **not** confuse this `S+0x1F04` byte with writer readiness **`O+0x2D=S+0x31`**.

- If **`DWORD[S+0x1EE0]!=0`**, `JNE 0x0054BB0F` jumps directly to epilogue **POP EDI; POP ESI; POP EBX; MOV ESP,EBP; POP EBP; RET**. No instruction between `CALL` and RET overwrites EAX, so the **underlying virtual call's EAX can pass through as the caller's final EAX** on this branch, even though it is never deliberately tested/used. In the v783 observed target `0x005092F0`, the writer returns 0 on its early/normal paths or 1 on its special path, but **the runtime path and caller return EAX are not measured here**.
- If **`DWORD[S+0x1EE0]==0`**, the caller runs:
  - `0x0054BAE6: LEA ECX,[EBP-0x18]; CALL 0x00836AD0`;
  - `0x0054BAEE: ECX=DWORD[0x00C26058]`; `EAX=DWORD[ECX]` then `EAX=DWORD[EAX+0x1C4]`;
  - `0x0054BAFC: EDX=&[EBP-0x18]; CALL EAX`, then stores new **EAX** to **`DWORD[S+0x1EE0]`** at `0x0054BB04`;
  - `0x0054BB0A: CALL 0x008F3DF0`, then normal epilogue.
  On this branch EAX is **overwritten by subsequent operations**, so it is **not** an intentionally consumed writer result. The final EAX is not given a proven semantic type by this caller.

Thus the precise statement is: **postregistration virtual-call EAX is not inspected or directly consumed for a decision**, though it **may survive unmodified as final EAX** on the nonzero `S+0x1EE0` branch. Saying the caller *always* discards EAX is too strong.

## 4. Exact join from nine registrations to readiness predicate: facts vs inference

The caller emits **nine consecutive direct calls** to `0x005092E0`, all using **`ECX=O=S+4`**. Their payload register values are owner-relative addresses:

| Ordinal / CALL EIP | Incoming EDX forwarded as payload |
|---|---|
| `0x0054BA56` | `S+0x780` |
| `0x0054BA63` | `S+0x1840` |
| `0x0054BA70` | `S+0x1B80` |
| `0x0054BA79` | `S+0x1180` (via EBX) |
| `0x0054BA86` | `S+0xC0` |
| `0x0054BA93` | `S+0x420` |
| `0x0054BAA0` | `S+0xAE0` |
| `0x0054BAAD` | `S+0x14E0` |
| **`0x0054BABA`** | **`S+0xE40`** |

The previously confirmed thunk changes `ECX=O` to **`C=O+8`** and jumps to insertion producer `0x004F5E60`. Its specific `0x004F5EA5: ADD DWORD[C+0xC],1` increments **`DWORD[O+0x14]`** after each normally completed insertion. On the **last** call, the PE supplies return address **`0x0054BABF`**. The *very next call in the same caller* is virtual **`0x0054BAC6`** with **ECX=O**. There is no explicit conditional branch between the nine callsites and this virtual dispatch.

**Trace-grounded path:** v788 previously attributed a **4-byte store value 9** to `0x004F5E60` at `O+0x14` (return `0x0054BABF`); v783 attributed this subsequent call's target to `0x005092F0` (return `0x0054BAC8`); v791 later reconfirmed count=9 / AL=0 / readiness zero reset for its finite run. Guard `0x00554050` receives `ECX=O+8` and returns **AL=1 iff `DWORD[O+0x14]==0`**. On observed **9** it returns **AL=0**. Writer `0x005092F0` therefore executes **`0x00509314: BYTE[O+0x2D]=0`** under its documented normal guard path. This proves the mechanical relationship between registrations, incrementing count, selecting the observed writer, testing nonzero count and direct byte-zero reset **for the supported traces**.

**Not proven:** that nine is the universally correct *live list length*, the complete initial count or absence of other mutations, a particular item type/registration meaning, the source of a positive readiness-byte write, whether the reset causes any progress plateau or missing menu, or that the virtual dispatch always resolves to the same original code. Both replay configurations remain **P-code guest** observations without retail draw translation proof; no native Windows/Wine launch, rendered menu or actual race is asserted.

## 5. Evidence ledger and limits

**PE instruction facts independently verified:** original SHA-256; 167-instruction enclosing function; `EDI=ESI+4` and all nine registration sites; callsite `0x0054BAC6` exactly `FF D0` with receiver ECX=O, vptr loaded from `DWORD[O]`, method pointer loaded at `DWORD[vptr+0x0C]`; no newly pushed method arguments; immediate return address `0x0054BAC8`; caller's subsequent `FLDZ`, count-unrelated `CMP[S+0x1EE0]`, floats, explicit byte-zero store and EAX control-flow distinction. Initial vptr construction/owner class **not resolved**.

**User-supplied runtime observation (not reproduced):** v783 identified target `0x005092F0` with caller/return `0x0054B8B0` / `0x0054BAC8`, O and read/reset details. v791 separately reported finite replay figures/count/zero byte and no proven render translation. Do not collapse these distinct samples into one trace or infer unreported virtual table values.

**Inference/unknown:** the direct virtual slot is plausibly the worker's update/registration-complete method but **no source symbol or class semantics is justified**; indirect downstream effects are outside this bounded caller, except the already studied particular v783 target. Whether different O objects carry different vptrs/implementations is not determined.

## 6. Exactly one next evidence-backed target

**`0x0054B8DC` — the earlier **virtual dispatch on the same O receiver**, in this very caller, through **`DWORD[DWORD[O]+0x04]`**. Original retail bytes:

~~~asm
0054b8cc: 8b 46 04             mov    eax,DWORD PTR [esi+0x4]
0054b8cf: 8b 40 04             mov    eax,DWORD PTR [eax+0x4]
0054b8d2: 8d 7e 04             lea    edi,[esi+0x4]
0054b8d5: ba 0c 50 ac 00       mov    edx,0xac500c
0054b8da: 8b cf                mov    ecx,edi
0054b8dc: ff d0                call   eax
~~~

This is one narrowly justified next target: it reads **the same original object's vptr storage `DWORD[O]`** and another precise slot +4, before the nine registrations and the later +0xC dispatch. A separate bounded task could establish its outgoing register ABI and single observed dispatch target (if separately instrumented) to better delimit O's interface; this is **not** a claim of a static method identity or reason to globally sweep vtables. **No other next target** is proposed.

## Appendix A — complete original retail function 0x0054B8B0–0x0054BB15 (167 decoded instructions; unchanged original machine bytes)

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

## Appendix B — essential prior provenance (context, not new callee investigation)

~~~asm
005092e0: 83 c1 08              add    ecx,0x8
005092e3: e9 78 cb fe ff       jmp    0x4f5e60
004f5ea3: 89 38                 mov    DWORD PTR [eax],edi
004f5ea5: 83 46 0c 01          add    DWORD PTR [esi+0xc],0x1

00554050: 83 79 0c 00          cmp    DWORD PTR [ecx+0xc],0
00554054: 0f 94 c0             sete   al
00554057: c3                   ret

00509314: c6 47 2d 00          mov    BYTE PTR [edi+0x2d],0
~~~

**This Markdown document is the only requested repository change.** No PE/source/P-code/runtime/renderer/guest-state or P2 edits, no replay or PR.
