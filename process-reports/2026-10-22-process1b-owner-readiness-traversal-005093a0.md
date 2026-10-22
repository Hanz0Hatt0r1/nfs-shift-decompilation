# Process 1b — bounded owner-readiness traversal, original 0x005093A0

**PE identity and scope:** original Need for Speed SHIFT PC retail 1.02 `SHIFT.exe`, PE32 x86, ImageBase `0x00400000`. Original-file SHA-256, verified locally in this task: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Original `objdump -D -M intel -w --start-address=0x5093a0 --stop-address=0x5096b3 /mnt/data/SHIFT.exe` and byte dump checked. Date 2026-10-22; bounded audit approximately 11:56–12:03 UTC. **Exact 787 bytes (`0x313`), entry `0x005093A0`, final instruction `0x005096B2: RET`, end-exclusive `0x005096B3`**; byte-perfect complete body appears in Appendix A. The immediate jump-table *data* starts outside the audited body (at `0x005096B4`). No new replay, global caller/writer survey, deeper callee-body analysis, code/runtime/P-code/renderer/guest-state changes, or claims of native Windows/Wine menu/race/rendering.

**Important control-flow caveat:** linear objdump's `0x005095D3–0x005095DF` instruction boundaries are not a verified executed basic block. `0x005095CD: JMP 0x0042C9CC` is a direct **out-of-function transfer**, and the bytes starting at `0x005095D4` admit another, plausible decoding (`JE 0x00509689; MOV EDX,[EBX]; MOV EAX,[EDX+0x14]; MOV ECX,EBX`). There is **no proven intra-function direct predecessor to `0x005095D4`**, so neither reachability nor register/flags after transfer via `0x0042C9CC` can be invented. **The physical original bytes at `0x005095E1: C6 43 2D 01` encode a write of 1 to [EBX+0x2D] if execution reaches that instruction**, but the source alone does not establish that it does. Appendix A preserves every byte without arbitrarily resolving this overlap. Similarly `0x00509689` is a real CALL site in the PE, but its incoming ECX and reachability from a particular conditional path are not established by a register reload at that site.

## 1. ABI and object/base provenance

At entry **ECX=B0**, unknown object pointer. `PUSH EBP; MOV EBP,ESP; SUB ESP,0xC; PUSH EBX; PUSH ESI; MOV EBX,ECX; PUSH EDI` saves nonvolatile registers and reserves three DWORDs of local space. **No explicit incoming stack parameter is read**; original EDX and EAX are not established independent semantic inputs. `DWORD[EBP−0xC]=B0` is initialized at `0x005093AB`, but that same slot's **address is later passed to other helpers** and may be overwritten: a later read is **not guaranteed to return B0**. More locals `[EBP−8]` and four bytes `[EBP−4..−1]` are initialized or used as iterator/branch state.

**EBX changes identity:** `0x00509461: ADD EBX,8` happens on the branch selecting `DWORD[B0+0x28]==3`. Subsequent `EBX-relative` accesses on that path refer to **B0+8**, not B0; where that path potentially continues into the later traversal via `0x005094F9/0x00509503`, it may retain the adjusted EBX. On another route, `EBX=B0`. **Never promote [EBX+0x2D] to [O+0x2D] without demonstrating B0=O and that EBX was not offset-adjusted.** Original owner O=`0x27DFA5FC` from separate finite traces is not mapped to B0 by this body.

**All four normal direct RET exits** are plain `RET`, no `RET imm` (at `0x00509447`, `0x005094F8`, `0x005095EF`, `0x005096B2`), restore EDI, ESI, EBX and the frame, and assign **EAX=0** before RET. All are **caller-managed argument count 0 at this function boundary**. The unconditional out-of-body `JMP 0x0042C9CC` has no direct local RET and its ultimate control flow is outside this audit. None of these exits returns the status 5 from `0x005088A0` as its own function result.

## 2. Exact bounded CFG with branches, loops and status handling

**Opening gate `0x005093AE–0x005093C1`:** `CALL 0x0040B870` returns pointer G; this body **reads DWORD[G]**, obtains function pointer `DWORD[DWORD[G]+0x48]`, and **CALL EAX** with `ECX=G` (no explicit stack arg). It compares returned **full EAX** against 1. ECX is reloaded to B0 before branching:
- **EAX==1:** call `0x00508ED0` (`ECX=B0`), compare **DWORD[EBX+0x28]** against returned EAX. If unequal, skip the early byte store and finish via `0x00509438`. If equal, **`0x005093D3: WRITE BYTE[EBX+0x2D]=AL`** (the **low byte of `0x00508ED0`'s return**). This is **not directly a constant zero**. The code then reads a pointer via `DWORD[EBX]`, chooses its **slot +0x14** and **CALL EAX** without freshly reloading ECX after `0x00508ED0` (the virtual-call ECX is therefore not fully proven). It traverses the EBX+8-derived structure using `0x0067DB80` and `0x004F5EB0`, with an item `Y=DWORD[ESI+0x0C]` and status **DWORD[Y+0xE4]**. On status <=7 a BYTE lookup at `0x005096BC` selects an indirect-jump index into `0x005096B4`; otherwise falls to the local successor. One branch invokes `0x00508970` on **ECX=Y**. As it advances, it reads node +4 and re-queries the iterator endpoint. Exit at `0x00509438` performs **`DWORD[EBX+0x28]=2`**, then EAX=0 and plain RET.
- **EAX!=1:** call `0x00508EF0` with **ECX=B0**. If returned **AL!=0**, jump to common exit `0x005096AA`, EAX=0. Otherwise read **DWORD[EBX+0x28]**. If ==3, follow the adjusted-EBX loop. If !=3, compare with 1 at `0x0050950D` and, if not 1, exit via `0x005096AA`. Note this second compare is also entered by fallthrough after a pair of `0x0062DE10` calls from a state3 status branch, so it may be comparing the **last callee's EAX**, not the originally read state field.

**State-3 loop `0x00509461–0x005094F8`:** shifts **EBX=B0+8** and initializes `BYTE[EBP−1]=1`. Iterator helpers on this adjusted EBX supply pointer EDI; for each `Y=DWORD[EDI+0xC]`, the code reads **DWORD[Y+0xE4]**, subtracts 3 and dispatches via an indirect jump table (`0x005096C4`) for values 0..4 (original statuses 3..7). Known branch blocks call `0x00508900` or `0x00508970` with **ECX=Y**, and a status-specific pair of `0x0062DE10` calls can fall through into the subsequent path. A block resets the local flag if specified conditions hold. Each iteration advances EDI via `DWORD[EDI+4]` when nonzero and re-evaluates the iterator. If local `BYTE[EBP−1]==0`, jump to shared `0x005096AA`; otherwise `0x005094E6` loads EAX from **[EBP−0xC]** (a caller/outparam-exposed local, **not guaranteed B0**), writes **DWORD[EAX+0x28]=2**, sets EAX=0 and RET.

**Second traversal `0x0050950D–0x0050968E`:** entry condition is **EAX==1** at `0x0050950D`. Initialize `ESI=EBX+8`, DWORD[EBP−8]=0, and flags: `BYTE[EBP−1]=1, BYTE[EBP−3]=1, BYTE[EBP−2]=0, BYTE[EBP−4]=0`. The stored 1 is the **low byte of EAX proved equal to 1**. Iterator calls `0x0067DB80`, `0x004F5EB0` with substructure receiver ESI. If no elements (as tested by comparison of EDI against helper-provided endpoint), jump straight to `0x00509694`; if elements exist, another `0x0040B870`/virtual slot+0x48 pair must return **EAX!=1** per iteration or control exits at `0x005096AA`. Each item `Y=DWORD[EDI+0x0C]` has **DWORD[Y+0xE4]** inspected, and <=7 passes through a jump table at `0x005096D8`. Different blocks call `0x005088C0, 0x005088E0, 0x00508900, 0x00508970, 0x005089C0` or update the local flags. Item `BYTE[Y+0xED]`, base `BYTE[EBX+0xAD]` and the flags provide additional branches. The item pointer may be stored at **DWORD[EBP−8]**. At normal loop continuation, **BYTE[EBP−1] is set to 0** at `0x00509588` on the fallthrough branch; other dispatch paths can skip this local assignment.

**Post-loop guard `0x005095A4–0x005095CD`:** when `BYTE[EBP−3]!=0`, `DWORD[EBP−8]!=0`, `BYTE[EBP−2]==0`, and `BYTE[EBP−4]==0`, it executes direct **`JMP 0x0042C9CC`** at `0x005095CD`. This is a transfer *outside the audited range*, **not a CALL**. What `0x0042C9CC` might do and whether it reaches `0x005095D4` cannot be established from this body. If a transfer eventually enters `0x005095D4`, its bytes decode as `JE 0x00509689` followed (on fallthrough) by loads of a vtable slot and the direct write `BYTE[EBX+0x2D]=1` at `0x005095E1`, indirect `CALL EAX` at `0x005095E5`, and EAX=0/RET. **The supplied linear objdump instead starts its decode at `0x005095D3`**; these physically overlapping interpretations must be kept distinct, and reachability is unknown without a separate control-flow proof.

**Status call `0x00509689` and exit through `0x0050968E`:** the PE has direct **CALL `0x005088A0`** at `0x00509689` with return EIP **`0x0050968E`**. This instruction has **no local MOV ECX,ESI immediately before it**; ECX on that edge must be proved from its actual predecessor/runtime trace, and the anomalous out-of-range `JMP` prevents an unqualified claim. Existing finite trace separately reported **one call from this site returning status 5**. On normal return, the **very next instruction** is **`CMP BYTE[EBP−1],0`** at `0x0050968E` — **it does not test EAX or compare it to 5**. Thus **no direct in-body predicate `(status == 5)` controls readiness here**.

**The unambiguous final readiness store `0x0050969B`:** common block `0x00509694` starts with **CMP BYTE[EBX+0xAD],0**, then **`MOV BYTE[EBX+0x2D],1`**, *before* the conditional JE to `0x005096AA`. There is **no additional immediate status-result test** in between. This block can be entered directly by the no-elements branch `0x0050954B → 0x00509694` or from `0x0050968E` when **BYTE[EBP−1]!=0** (JE otherwise exits). **The value written is always 1**, regardless of `BYTE[EBX+0xAD]`. If that +0xAD byte is nonzero, `0x005096A1` reads DWORD[EBX] then slot +0x14, explicitly restores **ECX=EBX** at `0x005096A6`, and **CALL EAX** at `0x005096A8`. Otherwise it skips the virtual call. Finally pop EDI/ESI/EBX, force EAX=0 and RET at `0x005096B2`.

### Exact readiness-byte store-site summary

| Original instruction | Direct write and condition | Source/identity limitation |
|---|---|---|
| **`0x005093D3`** | **BYTE[EBX+0x2D]=AL**; only on initial global virtual result EAX==1 *and* `DWORD[EBX+0x28]==EAX returned by 0x00508ED0`. AL is the **low byte of that returned value**. | EBX=B0 at this point; write is **not proven zero** |
| **`0x005095E1`** | Original bytes **`C6 43 2D 01`** encode **BYTE[EBX+0x2D]=1** if this instruction is reached. | **Reachability not proved** because `0x005095CD` jumps outside, and linear objdump is misaligned at `0x005095D3` |
| **`0x0050969B`** | **BYTE[EBX+0x2D]=1**, whenever control reaches `0x00509694`; direct `0x0050954B` edge or `0x0050968E` with nonzero `BYTE[EBP−1]`; **not gated by return EAX=5** | EBX may be B0 or B0+8 depending on path; never automatically O |

The separately observed `0x005092F0` writer of original owner **BYTE[O+0x2D]=0** is **another function** and is not a write performed at any instruction of `0x005093A0`. None of the listed write sites directly proves equality with that owner address, even if runtime O=`0x27DFA5FC` was seen elsewhere.

## 3. Exhaustive direct memory effect ledger (explicit operands; no callee effects)

**Entry/current EBX-relative data:**
- **READ DWORD[EBX]** at `0x005093D1` and `0x005096A1`; then **READ DWORD[loaded_vptr+0x14]** at `0x005093D6` and `0x005096A3`. Under a speculative alternative decode, similar reads at `0x005095DA/0x005095DC`, subject to its unproved entry.
- **READ DWORD[EBX+0x28]** at `0x005093CC`, `0x00509455` (state field); **WRITE DWORD[EBX+0x28]=2** at `0x0050943A`. After state3's EBX+8 shift, another store **DWORD[DWORD[EBP−0xC]+0x28]=2** at `0x005094EB`, not provably B0-relative because the local address was passed to helper calls.
- **WRITE BYTE[EBX+0x2D]** at `0x005093D3` (AL), `0x005095E1` (conditional reachability unknown, value 1), `0x0050969B` (value 1). See exact conditions in Section 2.
- **READ BYTE[EBX+0xAD]** at `0x005095F0`, `0x0050962B`, `0x00509694`.
- **`ADD EBX,8`** at `0x00509461` only changes the register/base, not memory.
- `LEA [EBX+8]` at `0x005093DB, 0x00509516, 0x00509598` creates addresses (no load); subsequent helper calls can access those objects, **unknown indirect effects**.

**Item/link/iterator-relative reads:**
- **READ DWORD[G]** `0x005093B3/0x00509556`, **READ DWORD[vptr+0x48]** `0x005093B7/0x0050955A` for the two global-object indirect CALLs (G comes from a direct `0x0040B870` return).
- **READ DWORD[returned iterator-pointer]** at `0x005093E8, 0x005093F4 (CMP), 0x00509472, 0x0050947E (CMP), 0x00509538, 0x00509544 (CMP), 0x0050959B/0x005095A0 (CMP)`.
- **READ DWORD[iterator node+0x0C]** at `0x00509400, 0x00509490, 0x00509568` and **READ DWORD[iterator node+4]** at `0x00509421, 0x005094C5, 0x0050958C`.
- **READ DWORD[item Y+0xE4]** at `0x00509403, 0x00509493, 0x005094B8, 0x0050956B, 0x00509600`; **READ BYTE[Y+0xED]** at `0x00509615, 0x0050963B`. These are reads, **not direct status writes**.
- **READ BYTE[table-base + index]** at `0x0050940E`; **indirect JMP DWORD[table-base + scaled index]** at `0x00509415, 0x005094A1, 0x00509576`. The table data lies just beyond the bounded code; the actual target must come from the original table content, so do not treat all entries as a single unconditional basic block.

**Explicit local memory effects:**
- **WRITE DWORD[EBP−0xC]=entry B0** at `0x005093AB`; later **READ DWORD[EBP−0xC]** `0x005094E6`. Addresses `&[EBP−0xC]` and `&[EBP−8]` passed to iterator helpers; their possible stores are **callee-side unknowns**.
- **WRITE BYTE[EBP−1]** at `0x00509469` (1), `0x005094C1` (0), `0x00509525` (AL=1 on this entry), `0x00509588` (0); **READ BYTE[EBP−1]** at `0x005094DC, 0x0050968E`.
- **WRITE DWORD[EBP−8]=0** at `0x0050951E`; **WRITE DWORD[EBP−8]=ESI** at `0x00509675`; **READ DWORD[EBP−8]** at `0x005095AE, 0x0050966B`.
- **WRITE BYTE[EBP−3]** at `0x00509528` (AL=1) and `0x00509584` (0), **READ BYTE[EBP−3]** at `0x005095A4`.
- **WRITE BYTE[EBP−2]** at `0x0050952B` (0) and `0x00509622, 0x00509648` (1), **READ BYTE[EBP−2]** at `0x005095B9`.
- **WRITE BYTE[EBP−4]** at `0x0050952F` (0) and `0x00509662` (1), **READ BYTE[EBP−4]** at `0x005095C3`.

**Implicit memory:** PUSH/POP/CALL/RET access machine stack; CALL pushes return address, outgoing PUSH instructions store explicit args. Byte reads from jump tables and any callee dereferences are not direct **object writes** of this body. This covers all identified explicit writes and owner/readiness-relevant reads; no direct **DWORD[O+0x14]** insertion-count write is present. Direct owner identity is unproved, and a referenced **vtable slot +0x14** must not be mislabeled owner data field O+0x14.

## 4. All immediate CALL boundaries (31 static sites; 26 direct rel32 and 5 CALL EAX)

**Table columns:** site → target, CPU return EIP, and **immediately byte-proven register/stack facts**. Calls with no freshly pushed args list “0”; unknown volatile inputs are not guessed. The body contains **no `RET imm`** and performs no caller-side `ADD ESP` for the two `0x0062DE10` outgoing pushes; balanced returns therefore require callee/equivalent cleanup, not a verified nested callee opcode.

| Site → callee | Return EIP | ECX / EDX / freshly pushed stack arguments |
|---|---|---|
| `0x5093AE → 0x40B870` | `0x5093B3` | ECX=B0; EDX not fixed; 0 |
| `0x5093BA → CALL EAX` | `0x5093BC` | ECX=G, EDX=DWORD[G], EAX=DWORD[DWORD[G]+0x48]; 0 |
| `0x5093C7 → 0x508ED0` | `0x5093CC` | ECX=B0; EDX not fixed; 0 |
| `0x5093D9 → CALL EAX` | `0x5093DB` | EAX=DWORD[DWORD[B0]+0x14], EDX=DWORD[B0]; **ECX unknown after 0x508ED0**; 0 |
| `0x5093E3 → 0x67DB80` | `0x5093E8` | ECX=B0+8; EDX=&[EBP−0xC]; 0 |
| `0x5093EF → 0x4F5EB0` | `0x5093F4` | ECX=B0+8; EDX=&[EBP−8]; 0 |
| `0x50941C → 0x508970` | `0x509421` | ECX=Y=DWORD[iterator+0xC]; EDX unknown; 0 |
| `0x50942F → 0x4F5EB0` | `0x509434` | ECX=B0+8; EDX=&[EBP−8]; 0 |
| `0x509448 → 0x508EF0` | `0x50944D` | ECX=B0, restored at 5093BF; EDX unknown; 0 |
| `0x50946D → 0x67DB80` | `0x509472` | ECX=adjusted EBX=B0+8; EDX=&[EBP−8]; 0 |
| `0x509479 → 0x4F5EB0` | `0x50947E` | ECX=B0+8; EDX=&[EBP−8]; 0 |
| `0x5094AA → 0x508900` | `0x5094AF` | ECX=Y=ESI; EDX unknown; 0 |
| `0x5094B3 → 0x508970` | `0x5094B8` | ECX=Y=ESI; EDX unknown; 0 |
| `0x5094D3 → 0x4F5EB0` | `0x5094D8` | ECX=adjusted EBX; EDX=&[EBP−8]; 0 |
| `0x5094FE → 0x62DE10` | `0x509503` | ECX/EDX unknown; 1 arg=`0x00AC5294` |
| `0x509508 → 0x62DE10` | `0x50950D` | ECX/EDX unknown; 1 arg=`0x00AC525C` |
| `0x509533 → 0x67DB80` | `0x509538` | ECX=ESI=EBX+8; EDX=&[EBP−0xC]; 0 |
| `0x50953F → 0x4F5EB0` | `0x509544` | ECX=ESI=EBX+8; EDX=&[EBP−0xC]; 0 |
| `0x509551 → 0x40B870` | `0x509556` | ECX/EDX not freshly fixed after iterator callee; 0 |
| `0x50955D → CALL EAX` | `0x50955F` | ECX=G, EDX=DWORD[G], EAX=DWORD[DWORD[G]+0x48]; 0 |
| `0x50957F → 0x5088C0` | `0x509584` | ECX=Y=ESI; EDX unknown; 0 |
| `0x50959B → 0x4F5EB0` | `0x5095A0` | ECX=EBX+8; EDX=&[EBP−0xC]; 0 |
| `0x5095E5 → CALL EAX` | `0x5095E7` | **Unproved reachability** after out-of-body jump; conditional alternative decode would load EAX from slot +0x14, ECX=EBX, EDX=vptr; 0 |
| `0x5095FB → 0x5088E0` | `0x509600` | ECX=Y=ESI; EDX unknown; 0 |
| `0x50960B → 0x508970` | `0x509610` | ECX=Y=ESI, from 5095F7 or 509609; EDX unknown; 0 |
| `0x509636 → 0x508900` | `0x50963B` | ECX=Y=ESI; EDX unknown; 0 |
| `0x509651 → 0x508970` | `0x509656` | ECX=Y=ESI; EDX unknown; 0 |
| `0x50965D → 0x508970` | `0x509662` | ECX=Y=ESI; EDX unknown; 0 |
| `0x50967F → 0x5089C0` | `0x509684` | ECX=Y=ESI; EDX unknown; 0 |
| `0x509689 → 0x5088A0` | `0x50968E` | **ECX not reloaded at this instruction**, actual predecessor uncertain; prior trace reports selected item in ECX; EDX unknown; 0 |
| `0x5096A8 → CALL EAX` | `0x5096AA` | ECX=EBX, EDX=DWORD[EBX], EAX=DWORD[DWORD[EBX]+0x14]; 0 |

A `CALL EAX` is a genuine immediate **indirect CALL boundary** but **not a verified constant target address**; no callee implementation is studied. The listed `0x005095E5` entry is a physical instruction sequence in linear disassembly whose reachability must be qualified as above. Immediate table-indexed JMPs at `0x509415, 0x5094A1, 0x509576` are **jumps, not CALLs**; the direct `JMP 0x0042C9CC` is also **not a CALL**. All return EIPs are fallthrough addresses from the original machine encodings.

## 5. Existing P-code trace evidence versus established static writes

Previous bounded P-code runs observed **O=0x27DFA5FC**, **DWORD[O+0x14]=9**, and **BYTE[O+0x2D]=0**. Earlier report attributed a **separate byte-clear writer to `0x005092F0`**. Another v791 report saw `0x005088A0` return status 5 from caller site `0x00509689`; a separate v795 trace followed the status-producer chain but does not identify a readiness/count causal edge. None of these traces is repeated in this assignment.

**Direct status-5 causality:** at `0x00509689` the original body calls `0x005088A0`; the very next local instruction `0x0050968E` tests **BYTE[EBP−1]**, **not returned EAX**. Therefore **the observed returned status 5 is not an immediate branch condition controlling `0x0050969B`**. The wrapper `0x005088A0` was previously shown to record the returned EAX into item-relative +0xE4. This body reads such item statuses at other loop locations, but that does not establish a direct status5-to-readiness write at this callsite. Callee effects and the odd out-of-body transfer remain unknown.

**Owner identity remains unresolved:** B0=entry ECX has **not** been shown equal to O by the supplied trace, and some paths change EBX to B0+8. The `0x0050969B` store is definitely **BYTE[EBX+0x2D]=1** at that executed instruction; it is **not** a direct known clear of **BYTE[O+0x2D]**. `0x005093D3` can store an **unknown low byte AL**, including potentially zero, if its two gates pass, but its receiver and actual value are not established by the finite observations. **No instruction directly proves original O+0x14 count changed**; a vtable slot +0x14 load is distinct from O+0x14 memory. The code does not prove that status 5 sets or clears original owner readiness.

**Bounded conclusion:** `0x005093A0` dispatches over item/status-linked iterators and has up to three physically encoded byte writes through its current EBX at offset +0x2D. The proven first gate writes the low byte of `0x00508ED0`'s return; the proven final block writes **1** if reached; an intermediate physical store of **1** has unresolved CFG reachability. **There is no direct test of status 5 immediately after `0x00509689`** and no proven alias between EBX and observed original O. This body alone therefore **cannot identify the observed O+0x2D=0 as caused by this status return**.

## 6. Exactly one next bounded evidence-backed target

**`0x00508ED0`** — the direct helper at **`0x005093C7`**, CPU return **`0x005093CC`**, called with **ECX=B0** and no newly pushed args. Its **full EAX** is immediately compared with **DWORD[EBX+0x28]**, and its low **AL** is **directly written into `BYTE[EBX+0x2D]`** when they agree. Auditing only this callee's full original PE body would resolve a byte-level **producer for the one nonconstant readiness-field write** without assuming B0=O, tracing all callers, or running replay. Its body is **not analyzed here**. This is the sole next target.

## Appendix A — complete original PE bytes, exactly 787 bytes

The following is a **complete contiguous original hexadecimal body**, 16 bytes per row (except the final 3), copied from SHA-verified original PE `objdump -s`; it is a lossless record of every code byte, including the ambiguous linear-decoding region at `0x005095D3`. The original full disassembly was used in Sections 1–4 for all branches, calls and memory accesses; the exact hex avoids silently choosing an unproven alternate instruction alignment.

~~~text
5093a0 558bec83 ec0c5356 8bd95789 5df4e8bd
5093b0 24f0ff8b 108bc88b 4248ffd0 83f8018b
5093c0 cb0f8581 000000e8 04fbffff 39432875
5093d0 678b1388 432d8b42 14ffd08d 7b088d55
5093e0 f48bcfe8 98471700 8b308d55 f88bcfe8
5093f0 bccafeff 3b300f95 c084c074 3b8d4900
509400 8b4e0c8b 81e40000 0083f807 77130fb6
509410 90bc9650 00ff2495 b4965000 e84ff5ff
509420 ff8b4604 85c07402 8bf08d55 f88bcfe8
509430 7ccafeff 3b3075c8 5f5ec743 28020000
509440 0033c05b 8be55dc3 e8a3faff ff84c00f
509450 85550200 008b4328 83f8030f 85ac0000
509460 0083c308 8d55f88b cbc645ff 01e80e47
509470 17008b38 8d55f88b cbe832ca feff3b38
509480 0f95c084 c0745feb 078da424 00000000
509490 8b770c8b 86e40000 0083c0fd 83f80477
5094a0 24ff2485 c4965000 8bcee851 f4ffffeb
5094b0 108bcee8 b8f4ffff 83bee400 00000775
5094c0 04c645ff 008b4704 85c07402 8bf88d55
5094d0 f88bcbe8 d8c9feff 3b3875b4 807dff00
5094e0 0f84c401 00008b45 f45f5ec7 40280200
5094f0 000033c0 5b8be55d c3689452 ac00e80d
509500 49120068 5c52ac00 e8034912 0083f801
509510 0f859401 00008d73 088d55f4 8bcec745
509520 f8000000 008845ff 8845fdc6 45fe00c6
509530 45fc00e8 48461700 8b388d55 f48bcee8
509540 6cc9feff 3b380f95 c084c00f 84430100
509550 00e81a23 f0ff8b10 8bc88b42 48ffd083
509560 f8010f84 42010000 8b770c8b 86e40000
509570 0083f807 7712ff24 85d89650 008bcee8
509580 3cf3ffff c645fd00 c645ff00 8b470485
509590 c074028b f88d55f4 8d4b08e8 10c9feff
5095a0 3b3875ad 807dfd00 0f84e000 00008b4d
5095b0 f885c90f 84d50000 00807dfe 000f85cb
5095c0 00000080 7dfc000f 85c10000 00e9fa33
5095d0 f2ff9018 0f84af00 00008b13 8b42148b
5095e0 cbc6432d 01ffd05f 5e33c05b 8be55dc3
5095f0 80bbad00 0000008b ce7510e8 e0f2ffff
509600 83bee400 00000175 0c8bcee8 60f3ffff
509610 e973ffff ff80beed 00000000 0f8466ff
509620 ffffc645 fe01e95d ffffff80 bbad0000
509630 00008bce 751be8c5 f2ffff80 beed0000
509640 00000f84 44ffffff c645fe01 e93bffff
509650 ffe81af3 ffffe931 ffffff8b cee80ef3
509660 ffffc645 fc01e921 ffffff83 7df8000f
509670 8513ffff ff8975f8 e90bffff ff8bcee8
509680 3cf3ffff e903ffff ffe812f2 ffff807d
509690 ff007416 80bbad00 000000c6 432d0174
5096a0 098b138b 42148bcb ffd05f5e 33c05b8b
5096b0 e55dc3
~~~

**Report-only GitHub publication.** No executable/source/runtime/P-code/renderer/guest-state edits, no new replay.
