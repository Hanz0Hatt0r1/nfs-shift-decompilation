# Process 1b — exact producer of UI worker O+0x14: tail thunk 0x005092E0, insertion 0x004F5E60 (v787/v788)

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`. **SHA-256 independently verified against mounted original `/mnt/data/SHIFT.exe`:**
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Scope:** the entire two-instruction retail tail thunk `0x005092E0–0x005092E7` and entire retail function `0x004F5E60–0x004F5EAB`; only the direct known original callsite at `0x0054BABA`, the accepted UI guard relationship, and the user-supplied controlled replay v787/v788 event facts. Source instruction bytes independently rechecked with GNU `objdump -D -Mintel -w` on the SHA-matched original PE. No global caller/writer/vtable sweep and no deep analysis of other callees. **No code/runtime/P-code/renderer/guest-state changes, no new replay, game launch or claims of native Windows/Wine runtime execution.**

## 1. Executive bounded finding

**Precisely proven field join** for the user-identified UI worker object `O`:
- `0x005092E0` receives `ECX=O` and computes **`ECX=O+0x8`**; it preserves incoming `EDX` and uses `JMP 0x004F5E60`, not CALL.
- `0x004F5E60` then treats that `ECX` as a list/container-like base `C=O+8` and preserves incoming `EDX` in EDI as the **payload DWORD**.
- **`0x004F5EA5: ADD DWORD PTR [ESI+0x0C],1`**, with `ESI=C`, increments **`DWORD[C+0xC] = DWORD[O+0x14]`** by one modulo 2^32. This is the direct producer instruction for the replayed 4-byte last write `9` to `0x27DFA610`.
- The accepted guard `0x00554050` compares **`DWORD[O+0x14]`** with zero and writes **only AL=(value==0)**; after a nonzero `9` it returns **AL=0**. The outer UI writer `0x005092F0` therefore reaches its direct clear **`BYTE[O+0x2D]=0`**. This is a **logical path explanation consistent with the v788 dispatch/write observations**, not proof of menu readiness or the progress plateau's root cause.

**Count qualification:** the field is an **insertion-updated counter** by exact opcode. An observed new value of 9 means the immediately previous 32-bit value for that increment was 8. A repeated conventional list insertion sequence supports the *inference* that it tracks a list size/count, but this single bounded producer does **not** prove a complete lifecycle or that exactly nine valid nodes remained linked at the observation point.

## 2. Exact thunk ABI, tail-call relationship and return

Complete original thunk in Appendix A:

~~~asm
005092e0: 83 c1 08              add    ecx,0x8
005092e3: e9 78 cb fe ff        jmp    0x4f5e60
~~~

- At entry, **`ECX=O`** is the proven object pointer from the user-supplied v788 callsite and prior UI worker analysis. **`EDX` is preserved unchanged** across this thunk; the thunk does not examine or overwrite EDX or EAX.
- `ADD ECX,8` performs 32-bit pointer arithmetic, so the callee sees **`ECX=C=O+8`**. It also changes flags, but the target function does not use those flags to select its incoming branch.
- The unconditional near `JMP` **does not push a new return address**, create a new stack frame, save any register or add a stack argument. The original caller's return address remains at the top of the stack; the body at `0x004F5E60` ultimately returns directly to that original caller.
- This block contains no `RET`, no memory read/write and no conventional stack args. The **combined** thunk+function ABI has two demonstrated register inputs: **ECX=O**, **EDX=payload**; the callee receives **ECX=O+8**, **EDX=payload**.
- The instruction modifies ECX and flags only; its transfer target is statically resolved as `0x004F5E60`. The behavior of the combined call is determined by the target function, not an independent thunk result.

## 3. Full function 0x004F5E60: incoming registers, internal call ABI and cleanup

The complete 32-instruction original retail block is reproduced in Appendix B.

**Entry contract inferred from explicit usage, not a C++ type declaration:**
- **`ECX=C`** → `0x004F5E61: MOV ESI,ECX` preserves the container base in ESI.
- **`EDX=payload`** → `0x004F5E67: MOV EDI,EDX` retains this original DWORD across nested calls. EDX is later overwritten for dispatch, but the payload remains EDI.
- There are **no explicit incoming stack arguments read** from `[ESP+...]` or `[EBP+...]`.
- Prologue `PUSH ESI` and `PUSH EDI` preserves both nonvolatile registers; epilogue `POP EDI; POP ESI; RET` restores them. Final `RET` is plain `C3`, with **no `RET imm16`** and no callee cleanup of any caller-pushed parameter DWORDs. The normal stack return goes through the tail thunk to its original callsite. EAX is returned unmodified after an `ADD EAX,0xC`, so on normal successful allocation it is **`node+0xC`** (payload-address pointer), **not** a proven HRESULT, Boolean or resulting count.

### 3.1 Initial conditional branch

At `0x004F5E63: CMP DWORD[C],0`, `0x004F5E69: JNE 0x004F5E7F`:
- **`DWORD[C]!=0`:** skip the `0x004F5E10` initialization-like call and proceed to allocate/link a node.
- **`DWORD[C]==0`:** use values from **`[C+0x18]`, `[C+0x8]` and `[C+0x4]`** as outgoing arguments/register inputs to **`CALL 0x004F5E10`**.

Exact initial call preparation:
1. `EAX=DWORD[C+0x18]` (`0x004F5E6B`);
2. `ECX=DWORD[C+0x8]` (`0x004F5E6E`);
3. `EDX=DWORD[C+0x4]` (`0x004F5E71`);
4. `PUSH EAX`, `PUSH 0x1F`, `PUSH ECX`; then **`ECX=C`** at `0x004F5E78`; **`CALL 0x004F5E10`** at `0x004F5E7A`.

Thus the helper is called with **register ECX=C**, **register EDX=DWORD[C+4]**, and three explicit outgoing stack DWORDs in callee order **`[ESP+4]=DWORD[C+8]`, `[ESP+8]=0x1F`, `[ESP+0xC]=DWORD[C+0x18]`**. The original caller performs **no explicit ADD ESP** after this call; correct normal resumption at the next instruction depends on the helper's ABI cleaning the three outgoing DWORDs (or otherwise preserving stack balance). **The helper's behavior, allocator policy, and exact semantic meaning of the three fields are not established here.** The original PE at `0x004F5E10` is a jump thunk to `0x00D86830`; that destination is **not analyzed**.

This condition **is not** a check of `DWORD[C+0xC]`. A zero/nonnull test of `DWORD[C]` alone does not establish that this DWORD is a size, root or initialized marker. In particular it does **not** prove the initial value of the count field.

### 3.2 Node allocation/producer boundary

At `0x004F5E7F: MOV ECX,ESI`, `0x004F5E81: CALL 0x00427320`, the function invokes a separate direct helper with **ECX=C** and **no new stack arguments**. **EAX on return** is immediately used as a writable node pointer `N`. The meaning "allocator/node provider" is a **bounded structural inference** from this returned pointer's later use; neither allocator implementation, object ownership nor its failure behavior is proved by these machine bytes. There is **no local check that EAX/N is nonzero or valid** before the subsequent writes.

### 3.3 Exact node links, payload and count update

Let **`H=DWORD[C+0x14]`** and **`F=DWORD[H]`** (both obtained by explicit PE loads), and **`N=EAX`** returned by `0x00427320`. The machine code performs the following in order:

| Original EIP | PE-proven operation | Structural role, conditional inference |
|---|---|---|
| `0x004F5E86–0x004F5E8B` | `DWORD[N]=DWORD[H]` | New node's first link gets previous head-link value `F` |
| `0x004F5E8D–0x004F5E90` | `DWORD[N+4]=H` | New node's second link points back to anchor H |
| `0x004F5E93–0x004F5E98` | `DWORD[F+4]=N` | Previous linked item's second link updated to new node |
| `0x004F5E9B–0x004F5E9E` | `DWORD[H]=N` | Anchor first link updated to new node |
| `0x004F5EA0–0x004F5EA3` | `EAX=N+0xC; DWORD[EAX]=incoming payload (EDI)` | Store one 32-bit payload at `N+0xC` |
| **`0x004F5EA5`** | **`DWORD[C+0xC]+=1`** | **Direct 4-byte count producer; with C=O+8, exact field `O+0x14`** |
| `0x004F5EA9–0x004F5EAB` | `POP EDI; POP ESI; RET` | Restore registers, return `EAX=N+0xC` to thunk's original caller |

Minimal descriptive pseudocode (structural notation only):

~~~c
if (*(uint32_t *)(C + 0x00) == 0) {
    helper_004F5E10(C, /* EDX */ *(uint32_t *)(C+4),
                    *(uint32_t *)(C+8), 0x1F, *(uint32_t *)(C+0x18));
}
uint8_t *N = (uint8_t *)node_provider_00427320(C);
uint8_t *H = *(uint8_t **)(C+0x14);
uint8_t *F = *(uint8_t **)H;
*(uint8_t **)N = F;
*(uint8_t **)(N+4) = H;
*(uint8_t **)(F+4) = N;
*(uint8_t **)H = N;
*(uint32_t *)(N+0xC) = incoming_EDX_payload;
++*(uint32_t *)(C+0xC);
return N+0xC;
~~~

These particular writes are **consistent with inserting a new node adjacent to the anchor in a doubly linked list**, possibly circular if H is a sentinel and properly initialized, but the constructor, sentinel invariants, node class and removal behavior are **unproven**. The record has a **DWORD payload at offset +0xC**; the 4-byte gap at `node+8` is not accessed by this block, so its meaning remains unresolved. No bounds check, null-pointer check, uniqueness check, allocation-failure branch or global element count validation occurs in the original block.

**Field layout established strictly by use:** `C+0x00` is a zero/nonzero initial-call gate; `C+0x04`, `C+0x08` and `C+0x18` are forwarded to the conditional helper; **`C+0x0C`** is an incremented 32-bit counter; **`C+0x14`** is a pointer to a link anchor used as above. **`N+0`, `N+4`** are linked-pointer fields, **`N+0xC`** stores payload. No source-level standard-container template type or exact capacity follows from this alone.

## 4. Does O+0x14 mean number of list elements? What does nine prove?

At the PE level **`DWORD[C+0xC]` is incremented exactly once per ordinary completed invocation of this insertion path**, after node linking and payload assignment. This strongly supports calling it an **insertion-maintained count**.

The statement "**there are exactly nine currently valid list elements**" requires additional premises not established by this bounded producer: the initial count was correct, no other function writes the count, no node was removed without updating it, and every link/allocator operation completed correctly. **None of these premises is proven here.** The statement "**the field's immediately preceding value was 8**" *is* justified for the observed `ADD DWORD,...,1` yielding value 9 (ordinary 32-bit addition).

For UI readiness the already proven guard maps:
- `C=O+8`, so **`DWORD[C+0xC]=DWORD[O+0x14]`**.
- `0x00554050: CMP DWORD[C+0xC],0; SETE AL` yields **AL=1 iff count==0**. For 9, **AL=0**.
- The direct writer `0x005092F0` tests AL and, when zero, executes **`0x00509314: MOV BYTE[O+0x2D],0`**.

**It is therefore evidenced that a nonzero insertion-maintained field causes the guard to select the writer's reset branch on that invocation**, not that the counter universally denotes readiness or that nine elements caused the progress=30 plateau. The list insertion code **never itself writes `BYTE[O+0x2D]`**.

## 5. User-supplied controlled replay v787/v788: precise correlation, no new execution claims

### v788 reported evidence (not newly reproduced)

- **120 host frames**, exit **0**, **0 Vulkan validation errors**, **815451 P-code dispatches**, **3934 unique functions**, complete v659 startup manifest, **23 trace events (not truncated)**. This was **original retail PE under P-code guest runtime**, not a native Windows/Wine executable launch.
- Object **`O=0x27DFA5FC`**, container base **`C=O+8=0x27DFA604`**, count/guard address **`O+0x14=C+0xC=0x27DFA610`**.
- **Exact-address last-write provenance:** direct four-byte store **value 9** attributed to function **`0x004F5E60`** on **dispatch 461055**, with **`ECX=0x27DFA604`**, reported caller thunk **`0x005092E0`**, **call return address `0x0054BABF`**, thread **`0x00177D80`**.
- **Guard at dispatch 461057** read field **9**, returned **`EAX=0x00509200`**, so **AL=0**. The upper 24 EAX bits are **not guaranteed by the guard itself**, which writes only AL; that full EAX value is a fact of the recorded replay.
- Following the guard, the prior writer clears `BYTE[O+0x2D]` as established by PE and the user-supplied prior last-write provenance. The trace does not establish live device draw translation.
- Both v787/v788 report **`guest_draw_translation=false`**, **`retail_rendering_proven=false`**.

### v787 independent observation as supplied

A second bounded replay with **120 host frames**, **0 Vulkan validation errors** and **815088 P-code dispatches** independently observed input **9** and guard **AL=0**. This corroborates the *guard's immediate predicate polarity in that replay*, but it is not a universal value guarantee or proof of any rendered menu/race.

### Exact PE corroboration of v788 return address

Narrow, independently checked original-PE bytes immediately preceding recorded **`call_return_address=0x0054BABF`**:

~~~asm
0054bab2: 8d 96 40 0e 00 00     lea    edx,[esi+0xe40]
0054bab8: 8b cf                 mov    ecx,edi
0054baba: e8 21 d8 fb ff        call   0x5092e0
0054babf: 8b 17                 mov    edx,DWORD PTR [edi]
~~~

Thus the **actual direct CALL site** is **`0x0054BABA`**, immediately before the recorded return address; it presents **ECX=EDI=O** on the observed path and **EDX=ESI+0xE40**, an address-like payload pointer derived from its caller's ESI (numeric ESI unknown here). The thunk increases ECX by eight and tail-transfers to `0x004F5E60`. The reported **dispatch 461055** is thereby connected to a specific original retail instruction that increments exactly the address observed. This is **not** a global caller scan or full analysis of the surrounding caller function.

### Evidence levels and causal limits

**PE-byte proven:** thunk's ECX+8 and tail JMP; insertion function's two register inputs, optional helper arguments, node writes, payload at N+0xC, **`ADD DWORD[C+0xC],1`**, output EAX and plain RET; narrow direct source callsite and return address.

**Runtime (user-supplied, not independently executed in this task):** field value 9, exact write address, dispatch IDs, thread, guard EAX/AL, frames/validation data and rendering flags.

**Inference only:** container is probably an owning linked collection with a count; payload perhaps a pointer to UI/list-related item. The PE does not provide a C++ container class, guaranteed element count, lifetime contract, why nine items were registered, why progress remained 30, or whether gameplay/race rendering was reached. Do not promote those hypotheses to retail facts.

## 6. Exactly one next evidence-backed target

**`0x0054BABA` — the *specific direct caller site* of the tail thunk**, confirmed by the original PE `E8 21 D8 FB FF` and v788 `call_return_address=0x0054BABF`. In a **separate bounded** static task, analyze only the immediate producer of **`ESI+0xE40`** payload and the local sequence around this **precise call** to learn what object type/address is being inserted into the list at the moment count reaches 9. This is the only proposed next target: **no global caller/writer sweep, no speculative list-helper work, no runtime forcing**.

## Appendix A — entire retail tail thunk 0x005092E0–0x005092E7

~~~asm
005092e0: 83 c1 08              add    ecx,0x8
005092e3: e9 78 cb fe ff        jmp    0x4f5e60
~~~

## Appendix B — entire original retail function 0x004F5E60–0x004F5EAB

~~~asm
004f5e60: 56                    push   esi
004f5e61: 8b f1                 mov    esi,ecx
004f5e63: 83 3e 00              cmp    DWORD PTR [esi],0x0
004f5e66: 57                    push   edi
004f5e67: 8b fa                 mov    edi,edx
004f5e69: 75 14                 jne    0x4f5e7f
004f5e6b: 8b 46 18              mov    eax,DWORD PTR [esi+0x18]
004f5e6e: 8b 4e 08              mov    ecx,DWORD PTR [esi+0x8]
004f5e71: 8b 56 04              mov    edx,DWORD PTR [esi+0x4]
004f5e74: 50                    push   eax
004f5e75: 6a 1f                 push   0x1f
004f5e77: 51                    push   ecx
004f5e78: 8b ce                 mov    ecx,esi
004f5e7a: e8 91 ff ff ff        call   0x4f5e10
004f5e7f: 8b ce                 mov    ecx,esi
004f5e81: e8 9a 14 f3 ff        call   0x427320
004f5e86: 8b 56 14              mov    edx,DWORD PTR [esi+0x14]
004f5e89: 8b 0a                 mov    ecx,DWORD PTR [edx]
004f5e8b: 89 08                 mov    DWORD PTR [eax],ecx
004f5e8d: 8b 56 14              mov    edx,DWORD PTR [esi+0x14]
004f5e90: 89 50 04              mov    DWORD PTR [eax+0x4],edx
004f5e93: 8b 4e 14              mov    ecx,DWORD PTR [esi+0x14]
004f5e96: 8b 11                 mov    edx,DWORD PTR [ecx]
004f5e98: 89 42 04              mov    DWORD PTR [edx+0x4],eax
004f5e9b: 8b 4e 14              mov    ecx,DWORD PTR [esi+0x14]
004f5e9e: 89 01                 mov    DWORD PTR [ecx],eax
004f5ea0: 83 c0 0c              add    eax,0xc
004f5ea3: 89 38                 mov    DWORD PTR [eax],edi
004f5ea5: 83 46 0c 01           add    DWORD PTR [esi+0xc],0x1
004f5ea9: 5f                    pop    edi
004f5eaa: 5e                    pop    esi
004f5eab: c3                    ret
~~~

## Appendix C — original retail linked guard/predicate, not a new audit

~~~asm
00554050: 83 79 0c 00           cmp    DWORD PTR [ecx+0xc],0
00554054: 0f 94 c0              sete   al
00554057: c3                    ret
~~~

**Report-only publication on work/process-reports. No source code, P-code, runtime, guest state, renderer, replay, P2 or PR changes.**
