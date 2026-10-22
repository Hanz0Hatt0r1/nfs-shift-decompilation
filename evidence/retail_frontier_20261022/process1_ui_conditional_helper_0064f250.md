# Process 1b — bounded conditional UI cleanup wrapper 0x0064F250 (retail PE32)

**Date:** 2026-10-22. **Executable:** Need for Speed SHIFT PC retail 1.02 original PE32 x86, ImageBase `0x00400000`. **Original `/mnt/data/SHIFT.exe` SHA-256 independently verified:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Strict scope:** **the entire six-instruction wrapper `0x0064F250–0x0064F25C`** and *only* the immediate call chain needed to pin its known receiver and register provenance: `0x00474D70` → `0x00508E40` → `0x0064F250`. The outgoing callee `0x0064F090` is considered **only at its call boundary**, **not** decompiled/disassembled/analyzed. GNU `objdump -D -M intel -w` independently reproduced all six original instruction bytes and the narrow cleanup caller bytes from the SHA-matched PE. Byte `0xCC` padding after `0x0064F25C` is **not part of this function**.

No global caller/writer/vtable sweep, no unrelated target study, no source, runtime, P-code, renderer or guest-state modifications, no new controlled replay, no native Windows/Wine launch and no UI/menu/race/rendering claims.

## 1. Exact known incoming ABI at 0x0064F250

The previously verified parent setup `0x00474D70` receives **ECX=O** and invokes `0x00508E40` only if `DWORD[O+0x30]!=0`. The cleanup helper `0x00508E40` saves `O` in ESI, executes **`EDX=DWORD[O+0x30]`** at `0x00508E44` and `EBX=0`, and only reaches `0x00508E55` when it also finds **`BYTE[O+0x3C]==0`**. Precisely:

~~~asm
00508e44: 8b 56 30              mov    edx,DWORD PTR [esi+0x30]
00508e47: 33 db                 xor    ebx,ebx
00508e49: 3b d3                 cmp    edx,ebx
00508e4b: 74 10                 je     0x508e5d
00508e4d: 38 5e 3c              cmp    BYTE PTR [esi+0x3c],bl
00508e50: 75 08                 jne    0x508e5a
00508e52: 8b 4e 38              mov    ecx,DWORD PTR [esi+0x38]
00508e55: e8 f6 63 14 00        call   0x64f250
00508e5a: 89 5e 30              mov    DWORD PTR [esi+0x30],ebx
~~~

Therefore at this **specific invocation path** of wrapper `0x0064F250`:

| Machine component | Original instruction provenance | Actual meaning justified |
|---|---|---|
| **ECX** | `0x00508E52: MOV ECX,DWORD[ESI+0x38]`, ESI=O | **`ECX=old DWORD[O+0x38]`**; *not* O; nested callee could treat this as a receiver |
| **EDX** | `0x00508E44: MOV EDX,DWORD[ESI+0x30]` | **`EDX=old DWORD[O+0x30]`**, tested nonzero before this call; value remains unchanged until wrapper |
| EAX | Not assigned by immediately relevant cleanup-site preparation | **Unspecified incoming value**; not a proven input of this wrapper |
| Explicit stack method arguments | No `PUSH` between setup of ECX and `CALL 0x0064F250` | **Zero** at wrapper boundary |
| Return EIP | 5-byte `CALL` at `0x00508E55` | **`0x00508E5A`** on normal wrapper return |

Importantly, the `0x00508E40` helper's **own** incoming EDX was previously overwritten: the nested wrapper gets the **old O+0x30 field**, *not necessarily* the original EDX argument `A` of the higher parent `0x00474D70`. The original owner pointer `O` remains saved in cleanup's ESI, but **O is not directly passed as ECX to `0x0064F250`**.

### Entry stack shape

At entry of `0x0064F250`, **`[ESP]=0x00508E5A`** is the CPU-pushed return address. No explicit caller-pushed DWORD method arguments were provided. The setup caller's existing stack frame and saved ESI/EBX are its own bookkeeping, **not arguments** of the nested wrapper. There is no prologue, no saved registers, no local stack frame and no `RET imm16` in this wrapper.

## 2. All six wrapper instructions, exact branch and outgoing call ABI

The **complete** retail function is:

~~~asm
0064f250: 85 d2                 test   edx,edx
0064f252: 74 08                 je     0x64f25c
0064f254: 6a 00                 push   0x0
0064f256: 52                    push   edx
0064f257: e8 34 fe ff ff        call   0x64f090
0064f25c: c3                    ret
~~~

1. **`TEST EDX,EDX`** at `0x0064F250` sets flags, including ZF when EDX==0. The register EDX itself is **not changed**. No object field or pointer is dereferenced.
2. **`JE 0x0064F25C`** at `0x0064F252` is taken exactly when EDX==0. This leads directly to `RET`, **no nested call, no outgoing pushes**.
3. If EDX!=0, **`PUSH 0`** at `0x0064F254` puts an all-zero DWORD on the stack. **`PUSH EDX`** at `0x0064F256` then pushes the original nonzero EDX DWORD above it.
4. **`CALL 0x0064F090`** at `0x0064F257` is a **direct, five-byte relative call**, returns to **`0x0064F25C`**; the wrapper has no intervening instruction after CALL before `RET`.
5. **`RET`** at `0x0064F25C` returns to the wrapper's own caller, namely **`0x00508E5A`** in this observed/known static call chain. This is **plain opcode C3**, not `RET 8` or any other callee stack-argument cleanup.

**Outgoing argument order**, with register/stack values *at entry* to `0x0064F090` when nonzero:

| Input to `0x0064F090` | Exact value |
|---|---|
| **ECX** | Still **`old DWORD[O+0x38]`** — the wrapper contains no ECX assignment |
| **EDX** | Still **`old DWORD[O+0x30]`** — nonzero; `TEST` and `PUSH` do not modify EDX |
| `[ESP]` | Return EIP **`0x0064F25C`**, pushed by direct `CALL` |
| **`[ESP+4]`**, first stack arg | **`old DWORD[O+0x30]`**, from the **second PUSH, `PUSH EDX`** |
| **`[ESP+8]`**, second stack arg | **`0`**, from the **first PUSH, `PUSH 0`** |

This demonstrates the same old `O+0x30` value is forwarded **both in EDX and as stack argument 1**, with **ECX=old O+0x38**. The callee's body/typed signature is **not** inspected here: it is unknown which register(s) or stack arguments `0x0064F090` truly consumes as semantic inputs, whether it frees/releases/invalidates data, and what return EAX means.

### Cleanup of the two pushed arguments

There is **no `ADD ESP,8`, `POP` or other stack repair** after `CALL 0x0064F090` in `0x0064F250`. The wrapper's own `RET` also has **no immediate**. Therefore for a **normally returning, balanced** nonzero branch, the callee `0x0064F090` must effectively **consume/clean its two explicit pushed DWORDs (8 bytes)**, or provide an equivalent stack-balanced exit; otherwise the wrapper `RET` would use an argument value instead of its caller's saved return address. This is a **strict callsite stack-balance inference**, *not* a claim to have verified `0x0064F090` contains a literal `RET 8`. Determining the callee's exact epilogue is out of scope.

The wrapper itself **does not perform caller-side cleanup** for its outgoing stack arguments and **does not clean any explicit stack arguments of its own caller** (there are none in the known path).

### EAX behavior

The wrapper **never reads, compares, masks, writes, or otherwise locally computes EAX**:
- if **EDX==0**, there is **no outgoing CALL**, so the wrapper's return EAX is **unchanged from its own input EAX** (unknown value);
- if **EDX!=0**, it makes `CALL 0x0064F090`, and the resulting EAX from that callee, whatever it is, passes **unchanged** through wrapper `RET`.

There is no wrapper-level success/failure synthesis, boolean conversion, HRESULT handling or return check. The known caller `0x00508E40` similarly does not test this returned EAX and proceeds to clear fields.

## 3. Complete direct memory effects and limits

**Explicit memory operands in all six original wrapper instructions: none.** Specifically:
- `TEST EDX,EDX` accesses only the EDX register and EFLAGS; `JE` branches using ZF.
- `PUSH 0` and `PUSH EDX` each **write one 32-bit value to the machine stack** and change ESP when the nonzero path is taken. They are **real memory writes to the stack**, not memory writes addressed from ECX/O.
- `CALL 0x0064F090` **implicitly pushes a return address** (another stack write) and transfers control. The callee's memory effects are wholly **unknown** and not included in the direct instruction-level set.
- `RET` **implicitly reads a return address from the machine stack** and pops it. There is **no explicit [ECX+offset], [EDX+offset], [O+offset] or global data operand** within the wrapper.

The full wrapper **does not directly read or write** any fields of the original owner `O`, including **`DWORD[O]` (vptr), `DWORD[O+0x14]` (list count), `BYTE[O+0x2D]` (readiness-associated field), `DWORD[O+0x30]`, `DWORD[O+0x38]`, or `BYTE[O+0x3C]`**. Its incoming registers contain *values loaded from* two such owner fields by the caller, but **forwarding register values is not the same as dereferencing those fields in this wrapper**.

The **nested function `0x0064F090` receives ECX=old O+0x38**, which could denote an allocated object, handle, owner alias, interior pointer or otherwise. **The class/type, allocation lifetime and possible aliasing with O are not established.** It may perform side effects on this or reachable objects: neither the absence of such effects nor an indirect write to O is provable from these six wrapper instructions. The conditional wrapper has **no direct mutation of the old-state values** (only stack forwarding); the higher cleanup helper later performs explicit zero stores.

## 4. Exact context and what can be concluded about old-state cleanup

The known conditional path is:

1. Parent setup `0x00474D70` tests **`DWORD[O+0x30]!=0`** and, on true, calls cleanup `0x00508E40`.
2. Cleanup `0x00508E40` re-reads old `DWORD[O+0x30]`, checks it for nonzero, then checks **`BYTE[O+0x3C]==0`**; only when both conditions hold does it load **`ECX=old DWORD[O+0x38]`** and make **`CALL 0x0064F250`**.
3. In that specific path, old `DWORD[O+0x30]` was loaded into EDX and tested nonzero by cleanup, with no intermediate instruction modifying EDX. So **the wrapper's `TEST EDX,EDX` is deterministically nonzero for this directly established call path**, and its `0x0064F090` call is reached on normal sequential execution.
4. After wrapper returns to **`0x00508E5A`**, cleanup directly clears **`DWORD[O+0x30]=0`**, then **`DWORD[O+0x34]=0`**, **`DWORD[O+0x38]=0`**, before returning. Higher parent `0x00474D70` subsequently installs new setup-field values in `O+0x38`, `O+0x30`, `O+0x34` and sets `BYTE[O+0x3C]=1` on a normal return.

**Byte-proven limited conclusion:** the wrapper **forwards the old +0x30 and +0x38 values** into one direct nested call, before the outer cleanup helper zeroes these old-state fields and the parent replaces them. Its placement is consistent with a cleanup/release path, **but it is not evidence that the nested function releases a resource or changes O at all**. The meaning of these fields is not established from source symbols, and there is **no direct path through this wrapper to readiness `O+0x2D` or list count `O+0x14`**.

**Explicit exclusions:** No provided v791 trace proves that parent/cleanup/wrapper/nested call actually executed. Earlier finite v791 original PE P-code guest observations of **`DWORD[O+0x14]=9`** and writer `0x005092F0`'s **`BYTE[O+0x2D]=0`** remain **separate observations**. They do **not prove** the wrapper's role in causing, repairing or maintaining either value. Neither actual UI/menu/race rendering nor native Windows/Wine execution is established.

## 5. Evidence ledger (PE, replay, inference)

**Original PE bytes independently verified:** exactly six wrapper instructions at `0x0064F250–0x0064F25C`; register-only TEST, one conditional branch, two pushes, single direct CALL, plain RET; exact outgoing values and stack order; normal call return EIPs `0x0064F25C` and `0x00508E5A`; no explicit owner-relative read/write.

**Prior bounded original PE caller bytes:** caller `0x00508E40` loads EDX from `DWORD[O+0x30]` and ECX from `DWORD[O+0x38]` only when byte `O+0x3C` is zero and previous field nonzero; it subsequently zeros `O+0x30/+0x34/+0x38`. The parent `0x00474D70` replaces them on normal return. These facts provide incoming-register provenance, but do not identify what the old values represent.

**User-supplied finite v791 guest replay:** separately sampled count 9 and writer readiness zero in a P-code guest execution, with no recorded execution/target effect for this cleanup path. Not newly run.

**Inference/unknown:** callee `0x0064F090`'s body, stack epilogue opcode, returns, memory writes, ownership/refcount/free semantics, object aliasing and dynamic invocation occurrence. Balanced stack on normal return strongly implies two-argument callee cleanup but **does not constitute independent inspection** of the callee code.

## 6. Exactly one next evidence-backed target

**`0x0064F090`** — direct nested call from **`0x0064F257`**, with **`ECX=old DWORD[O+0x38]`**, **`EDX=old DWORD[O+0x30]`**, **stack first=old O+0x30, second=0**, and return EIP **`0x0064F25C`**. It is the **only** next target supported by the wrapper's bytes, and a separate bounded audit could establish its immediate ABI, actual cleanup/return and direct writes. **Its body is deliberately not audited now.** No other targets or global scans are proposed.

## Appendix A — complete original retail wrapper, all instructions

~~~asm
0064f250: 85 d2                 test   edx,edx
0064f252: 74 08                 je     0x64f25c
0064f254: 6a 00                 push   0x0
0064f256: 52                    push   edx
0064f257: e8 34 fe ff ff        call   0x64f090
0064f25c: c3                    ret
~~~

`0x0064F25D` and following observed `CC` padding are **not function instructions**.

## Appendix B — immediate original caller callsite, exact operand source

~~~asm
00508e44: 8b 56 30              mov    edx,DWORD PTR [esi+0x30]
00508e47: 33 db                 xor    ebx,ebx
00508e49: 3b d3                 cmp    edx,ebx
00508e4b: 74 10                 je     0x508e5d
00508e4d: 38 5e 3c              cmp    BYTE PTR [esi+0x3c],bl
00508e50: 75 08                 jne    0x508e5a
00508e52: 8b 4e 38              mov    ecx,DWORD PTR [esi+0x38]
00508e55: e8 f6 63 14 00        call   0x64f250
00508e5a: 89 5e 30              mov    DWORD PTR [esi+0x30],ebx
00508e5d: 89 5e 34              mov    DWORD PTR [esi+0x34],ebx
00508e60: 89 5e 38              mov    DWORD PTR [esi+0x38],ebx
~~~

**Report-only publication in `work/process-reports`.** No changes to PE/source/runtime/P-code/renderer/guest-state, replay, native launch, live-game assertion or PR.
