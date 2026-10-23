# Process 1b — bounded original retail status-result body 0x00653480

**Date and bounded analysis:** 2026-10-22, UTC; report prepared at 2026-10-22T11:28:19.716Z. **Original PE identity (verified in assignment):** Need for Speed SHIFT PC retail 1.02, `SHIFT.exe`, PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. **Evidence:** complete original-PE objdump supplied with this assignment, transcribed in full in Appendix A. The assignment states that the retail SHA was independently checked; this report does **not** claim to have run a fresh replay, checked callee bodies or conducted a global scan.

**Exact original function boundary:** first instruction `0x00653480`, last instruction `0x0065354A: C2 10 00 / RET 0x10` spans `0x0065354A–0x0065354C`; end-exclusive `0x0065354D`. **`0xCD = 205 bytes`.** The following `INT3` padding `0x0065354D–0x0065354F` is not executable function body. No instruction, branch or direct call has been omitted from Appendix A.

**Scope and prohibitions:** just `0x00653480` and direct outgoing CALL ABI/return boundaries, related immediate calling context established by `0x0065FA60`. No source/runtime/P-code/renderer/guest-state edits; no global caller/writer sweep, callee body inspection, replay, native Windows/Wine launch or menu/race claim. Previous P-code runs are discussed **only as existing evidence** and never described as newly performed.

## 1. Exact ABI, receiver, arguments, epilogues

The previously byte-verified caller `0x0065FA60` calls **`0x00653480` at `0x0065FB0D`** with CPU return EIP **`0x0065FB12`**. It has computed **`V=P+0x64`**, where **P is the incoming receiver of `0x0065FA60` and was returned by `0x0065C0E0`**. The immediate register/stack inputs of the present function on that call are:

| Machine input | Value and proven provenance |
|---|---|
| **ECX** | **`V=P+0x64`**, register receiver for `0x00653480`; in one supplied dynamic probe `ECX=0x36214784` |
| **EDX** | **0**, set with full `XOR EDX,EDX` by caller |
| **`[EBP+8]`** | **0**, first explicit DWORD argument (last of four PUSH instructions) |
| **`[EBP+0xC]`** | **0**, second explicit DWORD argument |
| **`[EBP+0x10]`** | **0**, third explicit DWORD argument |
| **`[EBP+0x14]`** | **`0x005B0D50`**, fourth explicit DWORD argument (first PUSH) |
| **`[EBP+4]`** | CPU-pushed return EIP **`0x0065FB12`** |

Here **I** denotes the callback item from the earlier status chain, **O** denotes its original owner, and **P** denotes `0x0065FA60`'s own receiver. **V=P+0x64** is the local receiver of this specific function; its fields cannot be relabeled item-I or owner-O fields without independently proving alias/offset correspondence. The observed numeric address does not identify V as O.

Target prologue `PUSH EBP; MOV EBP,ESP; PUSH ESI; MOV ESI,ECX` gives **ESI=V**. `PUSH EDI; MOV EDI,EDX` occurs on all three branch paths and saves **EDI=original EDX=0** from the established caller. These registers are restored on exit. The function allocates no explicit local stack space.

All **three normal return sites** are **`RET 0x10`** (opcode `C2 10 00`) at **`0x0065349C`**, **`0x006534B7`**, and **`0x0065354A`**. They **callee-clean precisely four outgoing DWORD arguments (16 bytes)** furnished by `0x0065FA60`, so the caller needs no `ADD ESP,0x10` after `0x0065FB0D`. This is directly verified in this function, unlike assumptions about cleanup within its outgoing callees.

## 2. Exhaustive branches and provenance of EAX

### 2.1 First byte guard and direct forwarded early result

~~~asm
00653484: 8b f1                 mov    esi,ecx
00653486: f6 86 cc 00 00 00 02  test   BYTE PTR [esi+0xcc],0x2
0065348d: 57                    push   edi
0065348e: 8b fa                 mov    edi,edx
00653490: 74 0d                 je     0x65349f
00653492: 6a 03                 push   0x3
00653494: e8 47 ea ff ff        call   0x651ee0
00653499: 5f                    pop    edi
0065349a: 5e                    pop    esi
0065349b: 5d                    pop    ebp
0065349c: c2 10 00              ret    0x10
~~~

The **`JE 0x0065349F`** tests whether **`BYTE[V+0xCC] & 0x02 == 0`**. Intervening PUSH and MOV do not alter EFLAGS.

- **If bit 0x02 is SET**: **PUSH literal 3**, `CALL 0x00651EE0` at `0x00653494` with **ECX=V** and **EDX=original incoming EDX=0** for this established call path. The callee returns at **`0x00653499`**; this function then **forwards its EAX unchanged** through `RET 0x10`. No direct V-field write occurs on this local branch. **A zero from this first callee is possible but not established**, so the normal return is not a fixed status 3 or any other literal.
- **If bit 0x02 is CLEAR**: go to the second guard.

The value **3 is an outgoing stack argument**, **not** a value this body assigns to its own EAX on this branch.

### 2.2 Second guard and a second forwarded early result

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

On the first guard's zero branch, **ECX=V+8** via LEA (address only), while EDX is still saved in EDI but **not reloaded into EDX** for this CALL. In the established entry path it is still EDX=0 *before* calling `0x00635E40`. The **first callee's returned AL** is tested by `TEST AL,AL`.

- **If AL!=0**: **PUSH literal 10**, restore **ECX=V** with `MOV ECX,ESI`, and `CALL 0x00651EE0` at `0x006534AF`. Since `0x00635E40` may clobber volatile EDX, **full EDX at this outgoing CALL is unknown**, not safely asserted 0. Return EIP **`0x006534B4`**. This body **forwards EAX from `0x00651EE0` unchanged** and `RET 0x10`. No direct object-field write on this path.
- **If AL==0**: branch at `0x006534A9` to the main initialization sequence `0x006534BA`. This is the **only** path reaching the direct V-relative writes listed below.

Neither early branch checks the return from `0x00651EE0` after that call. Its zero/nonzero result is unknown without auditing that different function or a trace of the exact callsite.

### 2.3 Main path — direct stores, argument-driven fallback choices

The main path is entered only if **initial `BYTE[V+0xCC]&2==0`** and **`0x00635E40` returned AL=0**. It reads full **`F=DWORD[V+0xCC]`** at `0x006534BA`, possibly after callee effects. It loads **0.0f** using the x87 instructions `FLDZ; FSTP DWORD[V+0x3C]`. This is a 32-bit floating zero store (bit representation **0x00000000**).

Next it **clears bit 0x04 and sets bit 0x00010000** in the **full DWORD[V+0xCC]**:

~~~asm
006534ba: 8b 86 cc 00 00 00     mov    eax,DWORD PTR [esi+0xcc]
006534c0: d9 ee                 fldz
006534c2: 8b 4d 08              mov    ecx,DWORD PTR [ebp+0x8]
006534c5: d9 5e 3c              fstp   DWORD PTR [esi+0x3c]
006534c8: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
006534cb: 83 e0 fb              and    eax,0xfffffffb
006534ce: 0d 00 00 01 00        or     eax,0x10000
006534d3: 89 86 cc 00 00 00     mov    DWORD PTR [esi+0xcc],eax
~~~

**Exact value:** `DWORD[V+0xCC]=(F & 0xFFFFFFFB) | 0x00010000`. Existing bit 0x02 is **not directly changed by this expression**; the meaning of individual bits is unproven.

All further stores before the first tail CALL (here **A1=[EBP+8]**, **A2=[EBP+0xC]**, **A3=[EBP+0x10]**, **A4=[EBP+0x14]**) are:

| EIP | Direct WRITE | General input | At established caller `(A1,A2,A3,A4)=(0,0,0,0x005B0D50)` |
|---|---|---|---|
| `0x006534C5` | `DWORD[V+0x3C]` | x87 floating zero | `0x00000000` |
| `0x006534D3` | `DWORD[V+0xCC]` | `(F & ~4) \| 0x10000` | Same expression |
| `0x006534DC` | `DWORD[V+0x48]` | A1 | 0 |
| `0x006534E3` | `DWORD[V+0x44]` | entry EDX saved in EDI | 0 |
| `0x006534E6` | `DWORD[V+0x50]` | entry EDX saved in EDI | 0 |
| `0x006534E9` | `DWORD[V+0x54]` | A2 | 0 |
| `0x006534EC` | `DWORD[V+0x5C]` | 0 | 0 |
| `0x006534EF` | `DWORD[V+0x78]` | 3 | 3 |
| `0x006534F6` | `DWORD[V+0x30]` | 0 | 0 |
| `0x006534F9` | `DWORD[V+0x34]` | 2 | 2 |
| `0x00653502` / `0x0065350A` | `DWORD[V+0x9C]` | A3 if A3!=0, else **`0x005F1830`** | `0x005F1830` |
| `0x0065351B` / `0x00653523` | `DWORD[V+0xA0]` | A4 if A4!=0, else **`0x005E3210`** | **`0x005B0D50`** |
| `0x0065352E` | `DWORD[V+0x98]` | 0 | 0 |

The body has **13 distinct V-relative store offsets** (15 static store instructions because each fallback pair is mutually exclusive). These are the **entire direct non-stack write-set**. The fact that some offsets resemble other item/owner fields does **not** identify V as the original owner O, callback item I or original setup receiver.

**Branch precision:**
- At `0x006534DF` **XOR ECX,ECX** initializes ECX=0. Then **CMP EAX,ECX** at `0x006534E1` compares A3 against 0. Several intervening MOV instructions do not change EFLAGS, so **`JE 0x0065350A`** is taken if A3==0; otherwise store A3 at V+0x9C and **JMP 0x00653514**.
- At `0x00653514` load A4 and compare with ECX=0. **`JE 0x00653523`** selects V+0xA0 fallback if A4==0; otherwise stores A4 and **JMP 0x0065352D**.
- For the known original caller, A3=0 means first fallback, and A4=0x005B0D50 means the nonfallback store to V+0xA0. These branch selections are **static deductions from known passed values**; they do not independently establish that the main path was taken in any given replay.

### 2.4 Main tail and forced EAX=0

~~~asm
0065352d: 56                    push   esi
0065352e: 89 8e 98 00 00 00     mov    DWORD PTR [esi+0x98],ecx
00653534: e8 57 bf 00 00        call   0x65f490
00653539: ba 03 00 00 00        mov    edx,0x3
0065353e: 8b c8                 mov    ecx,eax
00653540: e8 6b 85 01 00        call   0x66bab0
00653545: 5f                    pop    edi
00653546: 33 c0                 xor    eax,eax
00653548: 5e                    pop    esi
00653549: 5d                    pop    ebp
0065354a: c2 10 00              ret    0x10
~~~

Main branch pushes one outgoing DWORD **V**, sets **DWORD[V+0x98]=0**, then calls **`0x0065F490`** at `0x00653534`. **ECX remains 0** since `0x006534DF: XOR ECX,ECX` and the intervening instructions do not change it; **EDX=A2** from `0x006534C8`, which is 0 for the known call. No caller `ADD ESP,4` follows, so normal stack-balanced return implies effective callee cleanup or equivalent (the callee's actual epilogue is not inspected).

After it returns, set **EDX=3** and **ECX=the returned EAX of `0x0065F490`**, then call **`0x0066BAB0`** at `0x00653540` (zero newly pushed args). This second callee's returned EAX is **discarded** by **`XOR EAX,EAX` at `0x00653546`**. Thus, provided both calls return normally, the entire **main path returns exactly EAX=0** **regardless** of the values returned by `0x0065F490` and `0x0066BAB0`. It does not check return EAX for success and does not directly set any original owner-readiness field.

### 2.5 All return paths at a glance

| Gate/path | Direct EAX at return | EAX source and proof |
|---|---|---|
| `BYTE[V+0xCC]&0x02 !=0` | **Unspecified** (may be 0 or nonzero) | EAX returned by `0x00651EE0(3)` forwarded unchanged via RET 0x10 |
| bit 0x02 clear; `AL(0x00635E40)!=0` | **Unspecified** (may be 0 or nonzero) | EAX returned by `0x00651EE0(10)` forwarded unchanged |
| bit 0x02 clear; `AL(0x00635E40)==0` | **0**, unconditionally if all calls return | Local `XOR EAX,EAX` after calls to `0x0065F490` and `0x0066BAB0` |

A zero return therefore does **not prove the main path was selected**: either early `0x00651EE0` call could also return zero. Conversely if all calls return normally and the main path executes, a zero return is **guaranteed directly** by the body. No EAX=0 claim is made for early paths without inspecting/observing `0x00651EE0`.

## 3. Exhaustive direct reads/writes and unknown effects

**Direct explicit non-stack reads:** `0x00653486` **READ BYTE[V+0xCC]** for first bit test; `0x006534BA` **READ DWORD[V+0xCC]** for main-path flag computation. There are **no other explicit dereferences of object fields** in this function. `LEA [V+8]` is only an address computation. Calling a helper with that pointer is **not** evidence the present body directly read the object at V+8.

**Direct explicit stack reads:** `0x006534C2` reads incoming DWORD A1 at `[EBP+8]`; `0x006534C8` reads A2 at `[EBP+0xC]`; `0x006534D9` reads A3 at `[EBP+0x10]`; `0x00653514` reads A4 at `[EBP+0x14]`. All are main-path only. PUSH/POP/CALL/RET implicitly write/read the ordinary machine stack, including saved EBP/ESI/EDI, outgoing helper arg(s), return EIPs, and cleanup of 16 inbound argument bytes. No explicit local stack allocation occurs.

**Direct explicit non-stack writes:** 13 offsets enumerated precisely in Section 2.3, all to **V-relative DWORDs**, including **x87 `FSTP DWORD[V+0x3C]` storing zero float** and the flag DWORD update at **V+0xCC**. Early branches have **zero direct V-field writes**. The full direct write-set excludes **I**, **O**, their respective vptrs, `DWORD[O+0x14]` count and `BYTE[O+0x2D]` readiness **by proven base identity**; V is not shown equal to I/O. If other pointers alias V, these writes could overlap arbitrary object storage, but **such aliasing is unknown and cannot be assigned as a proven owner write**.

**Unknown nested callee effects:** all four distinct callee bodies at five sites — `0x00651EE0` (two calls), `0x00635E40`, `0x0065F490`, `0x0066BAB0` — are **out of scope**. They receive V-derived pointers or values and could mutate reachable memory or have asynchronous consequences; neither their purity nor their resource/lifecycle semantics is established. **No direct write from this body to original owner readiness is proven**, but absence of indirect owner writes cannot be asserted.

## 4. Every immediate outgoing CALL boundary — five static callsites

The following are **all** direct CALL instructions in the complete function; return EIP is the next original instruction. “Stack arg” is a freshly pushed explicit DWORD for that target, not the four existing incoming args of this function.

| Callsite → target | Return EIP | Provable ECX/EDX and fresh stack argument(s) |
|---|---|---|
| **`0x00653494 → 0x00651EE0`** | **`0x00653499`** | If BYTE[V+0xCC] bit 0x02 set: **ECX=V**, **EDX=entry EDX=0** for established status-chain call, **one pushed DWORD=3** |
| **`0x006534A2 → 0x00635E40`** | **`0x006534A7`** | If bit 0x02 clear: **ECX=V+8**, **EDX=entry EDX=0**, **zero newly pushed args** |
| **`0x006534AF → 0x00651EE0`** | **`0x006534B4`** | If `AL(0x00635E40)!=0`: **ECX=V**, **EDX unknown after the prior call**, **one pushed DWORD=10** |
| **`0x00653534 → 0x0065F490`** | **`0x00653539`** | Main path: **ECX=0**, **EDX=A2=[EBP+0xC] =0** for established caller, **one pushed DWORD=V** |
| **`0x00653540 → 0x0066BAB0`** | **`0x00653545`** | Main path: **ECX=EAX returned by 0x0065F490**, **EDX=3**, **no newly pushed args** |

For the one-argument calls to `0x00651EE0` and `0x0065F490` there is **no local caller-side `ADD ESP,4`** after the CALL. Normal stack balance implies the callees restore the corresponding outgoing arg or an equivalent convention; this report **does not claim the literal RET opcode in any callee**. The current body itself unambiguously cleans its **own four incoming arguments with RET 0x10** on every return. The call to `0x00635E40` consumes only its register state as prepared here; nothing about its typed signature is asserted.

## 5. Existing dynamic observations, distinct provenance and bounded conclusion

**Previously supplied new bounded original-PE P-code probe (not run here):** at dispatches **605092/605095/605245**, one actual path passed through `0x00634F50 → 0x0065EC50 → 0x0065FA60 → 0x00653480`; `0x00653480` entered with **ECX=0x36214784**, **EDX=0**, **EAX=0x00010000**, and returned **EAX=0**. Both `0x0065FA60` and `0x0065EC50` subsequently returned **0**. **Entry EAX=0x00010000 does not select any branch here**: this body first tests `BYTE[V+0xCC]` and then follows callees; no instruction consumes incoming EAX as a substantive argument before the first CALL.

The probe later **timed out at 180 seconds (exit 124) after 890 guest Present requests**, without reaching a host-frame checkpoint; no proved draw translation, rendered menu or race. The record supplied here does not include the **first tested byte** or the **`0x00635E40` AL** or either **`0x00651EE0` returned EAX**, so the observed zero **cannot be localized unambiguously** to this body's main path. It cannot establish which of its 13 V-relative field writes executed in that run. This is precisely why the early return distinction matters.

**Older v229–v239 request-path probes (not repeated):** separately observed a `0x00653480` return EAX=0 in another context, along a request-path sequence involving `0x00653140, 0x00652190, 0x0066CC00, 0x00653480`, under `guest_draw_translation=false`. Those historical observations must **not** be counted as evidence newly produced by this static audit or automatically attributed to the status-query invocation.

**Earlier v790/v791 status and owner field observations remain separate:** one v790 inner `0x00508C70` returned 5; v791 five outer `0x005088A0` calls returned 5 without identifying all inner callback targets; v791 independently observed `O+0x14=9` and `BYTE[O+0x2D]=0` written by `0x005092F0`. The new bounded P-code path does establish **one** dynamic visit to this specific downstream helper, but not that this was the same v790 inner callback or that it wrote owner readiness. **Do not infer a causal link from this body to O's vptr, list count or readiness**.

**Newly established by this full original-body analysis:** exactly three returns with RET 0x10, five direct CALL boundaries, two early **callee-determined** returns, one **locally forced EAX=0** return, the exact 13-offset direct receiver write-set restricted to the main path, and the caller-specific fallback choices A3=0 and A4=0x005B0D50. No global caller/writer investigation is needed for these conclusions.

**Bounded conclusion:** original `0x00653480` may return a callee-derived value at either early exit, but **always returns zero after completing the main initialization path**. The supplied dynamic EAX=0 does not reveal which path was taken. This complete body directly writes **V-derived state only**; it does not by itself explain `DWORD[O+0x14]` or `BYTE[O+0x2D]`, and no source-language meaning for the offsets or functions is proven.

## 6. Exactly one next evidence-backed target

**`0x00635E40`**, a single direct outgoing callee at **`0x006534A2`**, return EIP **`0x006534A7`**, with **ECX=V+8**, **EDX=0** in the verified status-chain call, and **no outgoing stack args**. This is the next narrowest target because its **return AL is tested immediately** and determines whether the execution reaches **the locally forced-zero main path** or calls `0x00651EE0` for a callee-dependent early result, assuming the first bit0x02 gate is clear. The original body of `0x00635E40` is **not analyzed here**; pursuing this target would require a separate bounded assignment. No second target, global sweep or replay is proposed.

## Appendix A — full original retail 0x00653480–0x0065354C (205 bytes)

~~~asm
00653480: 55                    push   ebp
00653481: 8b ec                 mov    ebp,esp
00653483: 56                    push   esi
00653484: 8b f1                 mov    esi,ecx
00653486: f6 86 cc 00 00 00 02  test   BYTE PTR [esi+0xcc],0x2
0065348d: 57                    push   edi
0065348e: 8b fa                 mov    edi,edx
00653490: 74 0d                 je     0x65349f
00653492: 6a 03                 push   0x3
00653494: e8 47 ea ff ff        call   0x651ee0
00653499: 5f                    pop    edi
0065349a: 5e                    pop    esi
0065349b: 5d                    pop    ebp
0065349c: c2 10 00              ret    0x10
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
006534ba: 8b 86 cc 00 00 00     mov    eax,DWORD PTR [esi+0xcc]
006534c0: d9 ee                 fldz
006534c2: 8b 4d 08              mov    ecx,DWORD PTR [ebp+0x8]
006534c5: d9 5e 3c              fstp   DWORD PTR [esi+0x3c]
006534c8: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
006534cb: 83 e0 fb              and    eax,0xfffffffb
006534ce: 0d 00 00 01 00        or     eax,0x10000
006534d3: 89 86 cc 00 00 00     mov    DWORD PTR [esi+0xcc],eax
006534d9: 8b 45 10              mov    eax,DWORD PTR [ebp+0x10]
006534dc: 89 4e 48              mov    DWORD PTR [esi+0x48],ecx
006534df: 33 c9                 xor    ecx,ecx
006534e1: 3b c1                 cmp    eax,ecx
006534e3: 89 7e 44              mov    DWORD PTR [esi+0x44],edi
006534e6: 89 7e 50              mov    DWORD PTR [esi+0x50],edi
006534e9: 89 56 54              mov    DWORD PTR [esi+0x54],edx
006534ec: 89 4e 5c              mov    DWORD PTR [esi+0x5c],ecx
006534ef: c7 46 78 03 00 00 00  mov    DWORD PTR [esi+0x78],0x3
006534f6: 89 4e 30              mov    DWORD PTR [esi+0x30],ecx
006534f9: c7 46 34 02 00 00 00  mov    DWORD PTR [esi+0x34],0x2
00653500: 74 08                 je     0x65350a
00653502: 89 86 9c 00 00 00     mov    DWORD PTR [esi+0x9c],eax
00653508: eb 0a                 jmp    0x653514
0065350a: c7 86 9c 00 00 00 30 18 5f 00 mov DWORD PTR [esi+0x9c],0x5f1830
00653514: 8b 45 14              mov    eax,DWORD PTR [ebp+0x14]
00653517: 3b c1                 cmp    eax,ecx
00653519: 74 08                 je     0x653523
0065351b: 89 86 a0 00 00 00     mov    DWORD PTR [esi+0xa0],eax
00653521: eb 0a                 jmp    0x65352d
00653523: c7 86 a0 00 00 00 10 32 5e 00 mov DWORD PTR [esi+0xa0],0x5e3210
0065352d: 56                    push   esi
0065352e: 89 8e 98 00 00 00     mov    DWORD PTR [esi+0x98],ecx
00653534: e8 57 bf 00 00        call   0x65f490
00653539: ba 03 00 00 00        mov    edx,0x3
0065353e: 8b c8                 mov    ecx,eax
00653540: e8 6b 85 01 00        call   0x66bab0
00653545: 5f                    pop    edi
00653546: 33 c0                 xor    eax,eax
00653548: 5e                    pop    esi
00653549: 5d                    pop    ebp
0065354a: c2 10 00              ret    0x10
~~~

**Only a report Markdown is published on branch `work/process-reports`. No source/runtime/P-code/renderer/guest-state changes, replay or game-run claim.**
