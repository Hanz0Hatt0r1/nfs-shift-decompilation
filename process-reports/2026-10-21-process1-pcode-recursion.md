# Process 1 — static/runtime review of P-code recursion at 0x0064d020 / 0x0064d02a / 0x004727e3

**Date:** 2026-10-21  
**Repository:** Hanz0Hatt0r1/nfs-shift-decompilation  
**Report branch:** work/process-reports  
**Report path:** process-reports/2026-10-21-process1-pcode-recursion.md  
**Target original:** SHIFT.exe, PE32 x86, SHA-256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1  
**Scope:** only the three addresses above. No runtime/renderer modifications.  
**Provenance:** analysis exclusively of the literal evidence and code supplied in the request. Neither the original EXE bytes, Ghidra project, full function export, replay process, nor a local filesystem was accessed. This report does **not** claim independent binary/xref verification.

## 1. Decision

**Classification: unresolved.** The bounded native GDB backtrace supports *nested host-side execution of recompiled guest-function wrappers* in the order 0x0064d020 → 0x004727e3 → 0x0064d02a, routed through the runtime callback/dispatch bridge. It does **not** establish that these are three distinct valid original PE32 function entry points, that the execution constitutes genuine guest-level recursion, that the recursion is infinite, or that the P-code function boundaries or dispatch mapping are wrong.

The decompiler's reported one-call body for 0x004727e3 is consistent with the observed transition to 0x0064d02a, but the machine bytes and disassembly for all three locations were not provided. In particular the two candidate targets 0x0064d020 and 0x0064d02a differ by **0xA bytes**: this makes instruction- and function-boundary validation important, but *does not itself prove overlap, a bad target, a thunk or a shared block*. The observed CPU activity and ceased trace growth in an unfinished replay are not sufficient evidence of a hard hang.

## 2. Full relevant evidence, reproduced from the request

### Original executable and replay context

- Original: SHIFT.exe PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Current P1 full-game-root replay: runtime built from current branch `work/retail-runtime-d3d9-capture`, manifest **v659**, **1440 requested frames**.
- The process consumed CPU for a prolonged period, while the live trace stopped growing; the monitored getters `0x005a0ef0`, `0x005ab230`, `0x005ab3f0` had not been called. This was an **unfinished replay**, not proof of a hang or of game startup.
- Earlier replay reports **v660/v661** used an incomplete game root and are **not equivalent evidence** for the present full-root replay.
- Recompiled P-code module path supplied for identification only (not opened): `/home/pes/nfs-shift-recompilation-artifacts/shift-startup-probe-20261018/libnfs_shift_pcode_startup_20261018.so`.
- The Ghidra 12k-function export reportedly stopped around `0x005b9c00`; it therefore does **not** provide the bodies for `0x0064d020` or `0x0064d02a`.

### Exact bounded GDB native backtrace

~~~text
#0 rvi_read_value() from libnfs_shift_pcode_startup_20261018.so
#1 rvi_0064d02a() from libnfs_shift_pcode_startup_20261018.so
#2 shift::runtime::RecompiledPcodeModule::Impl::dispatch(...)
#3 shift::runtime::RecompiledPcodeModule::Impl::call_callback(...)
#4 rvi_call() from libnfs_shift_pcode_startup_20261018.so
#5 rvi_004727e3() from libnfs_shift_pcode_startup_20261018.so
#6 dispatch(...)
#7 call_callback(...)
#8 rvi_call()
#9 rvi_0064d020()
#10 dispatch(...)
#11 call_callback(...)
~~~

The supplied observation further states that the cycle repeats beyond these **top 12 native frames**, while total depth, guest registers and validity of guest function entry points are unknown. The actual deeper frames were not included.

### Exact provided Ghidra decompilation

~~~c
void FUN_004727e3(void) {
  FUN_0064d02a();
  return;
}
~~~

No byte listing, instruction-level disassembly, Ghidra FunctionManager boundaries, direct/indirect instruction references, decompilation of either 0x0064d020 or 0x0064d02a, or P-code dispatch-table mapping was supplied.

## 3. What the backtrace demonstrates — and does not

Read from older caller to newer callee (frames #9 → #5 → #1):

~~~text
rvi_0064d020
  -> rvi_call
    -> call_callback -> dispatch
      -> rvi_004727e3
        -> rvi_call
          -> call_callback -> dispatch
            -> rvi_0064d02a
              -> rvi_read_value
~~~

**Proved at the host call-stack level:** the sample contains wrappers named `rvi_0064d020`, `rvi_004727e3`, `rvi_0064d02a` and intervening dispatch/callback frames. The uppermost sampled operation is `rvi_read_value`. The sampled wrappers are nested, not merely separate historical trace events.

**Not proved:** exact original x86 CALL/JMP opcodes, the guest EIP at which each callback was requested, the identity of the dispatch mapping used for each target, a static edge from 0x0064d02a back to 0x0064d020, guest-stack growth, repeated guest register/memory state, an absent base case, the exact native/guest call depth, or the meaning of `rvi_read_value` at that point. Native call-stack growth may reflect runtime wrapper recursion and need not by itself correspond one-for-one to original guest CALL frames.

The decompiled 0x004727e3 body supplies one **reported** static callee edge to 0x0064d02a. A decompiler call expression alone does not establish its original machine encoding (CALL versus tail transfer/other normalized control flow) without the instruction listing.

## 4. Bodies, bytes, exact boundaries and xrefs: evidence inventory

| Candidate address | Exact machine bytes | Instruction body / return | Ghidra function boundaries | Supported xref/callsite claim |
| --- | --- | --- | --- | --- |
| 0x004727e3 | **Not provided** | Provided *decompilation only*: calls FUN_0064d02a then returns; no assembly-level branch/RET verification | **Not provided** | Decompiler represents a call to 0x0064d02a; exact instruction address and xref kind unknown |
| 0x0064d020 | **Not provided** | **Not provided**; runtime wrapper appears at native frame #9 | **Not provided** | Host chain reaches 0x004727e3 through callback/dispatch; no verified original instruction xref |
| 0x0064d02a | **Not provided** | **Not provided**; runtime wrapper appears at native frame #1 before rvi_read_value | **Not provided** | Reported decompiler callee of 0x004727e3; exact original xrefs and any outgoing/back edge unknown |

The last two addresses differ by ten bytes. Possibilities include two valid nearby functions, a small entry thunk, a shared-code/tail-entry convention, an interior instruction boundary, or a wrong split/lookup. **None can be selected with the supplied evidence.** Neither a symbol name such as `rvi_0064d02a` nor a decompiler label such as `FUN_0064d02a` proves a valid function entry in the original executable.

To make a genuine static determination, export original PE32 bytes and the exact Ghidra instruction listing for a small window spanning both nearby targets (for example 0x0064cff0–0x0064d060) plus 0x004727d0–0x00472810. For each target retrieve `getFunctionAt`, `getFunctionContaining`, the function entry/end and body address-set ranges, `getInstructionAt`, `getInstructionContaining`, block successors/predecessors, and `getReferencesTo`/outgoing instruction references. Confirm whether each target starts a decoded instruction and which specific instruction transfers control to it. Record **bytes and x86 instruction boundaries**, not solely decompiler output. These are requested probes, **not completed analysis**.

## 5. Competing explanations and minimum falsifying evidence

1. **Normal, finite guest-level nested calls:** possible if original boundaries and call targets are valid and a returning path/conditional or changing recursion parameter exists. Requires original control-flow graph, guest stack observations and either actual unwinding or decreasing/terminating state.
2. **Unbounded recursive guest control flow:** possible if a repeated back edge actually exists with no reachable termination under the observed guest state. Requires repeated guest PC/callsite cycles and monotonically growing guest call stack (or equivalent guest call depth) without observed unwind; for an unconditional static cycle, the verified original CFG would provide stronger proof.
3. **Function boundary, overlap or dispatch error:** possible because 0x0064d020/0x0064d02a are close and dispatch reconstructs control flow. Requires proof that a dispatched target is inside a non-entry instruction or wrong function range, or that the callback target does not match the target computed by original P-code/callsite. **Do not correct either address based on proximity alone.**
4. **Another unresolved execution/pathology issue:** a very slow valid path, a repeated dynamic callback, trace buffering/cap, or an operation inside `rvi_read_value` could also produce the sampled symptoms. The top frame alone cannot identify an invalid memory access.

The current state is **unresolved**, not classified as an infinite loop, normal recursion or a confirmed dispatch defect.

## 6. Minimal non-semantic runtime probe

Record a **bounded** diagnostic ring buffer at the dispatch/callback bridge and at entries to the three wrappers (for example the last 128–256 relevant transfers, retained even if the normal live trace stops). No guest control-flow modification, call skipping, artificial return, altered state or new recursion cutoff should be introduced.

For each guest transfer/event, collect:

- Ordered event counter, guest frame/tick if known, host thread ID, native recursion depth, guest call depth if tracked.
- **Guest callsite PC**, decoded transfer type (direct call, indirect call, jump, or runtime callback) and expected/computed **guest target VA**.
- Dispatch table key, selected recompiled wrapper symbol/entry, containing function/range (if known), and a flag for a target landing on a known original instruction/function boundary.
- Guest **EIP, ESP, EBP, ECX, EAX, EDX, EFLAGS**, plus the first 32–64 bytes of guest stack at ESP (with memory-read validity); the immediate guest return address where applicable.
- For `rvi_read_value`, the original guest P-code op/instruction PC, operand identifier/type and address/space/size being read, if exposed by existing diagnostics, with success/error status. Do not assume it is a memory load without an op record.
- On each observed return, guest ESP/EIP and matched call ID; log branch predicate and selected edge on repeated guest control-flow transitions if obtainable without state changes.

Correlate *both* `guest-PC + callsite + target` and `guest ESP + return-address + register snapshot` across at least several cycles. If guest ESP shrinks on every repeated original CALL and no corresponding return occurs, the data support true recursive call accumulation; if guest ESP stays constant while host frames grow, suspect wrapper/callback recursion or guest tail-control-flow mapping. Do not treat a single ESP delta as dispositive: x86 functions can adjust ESP, allocate locals, and use nonstandard control flow.

A single decisive static/runtime alignment record is:

~~~text
original_guest_callsite_PC=<instruction address>
original_instruction_bytes=<hex>
transfer_kind=<CALL/JMP/indirect/...>
computed_guest_target=<VA>
dispatch_selected_wrapper=<rvi_...>
target_is_instruction_start=<yes/no>
target_function_entry_or_containing_range=<...>
guest_EIP/ESP/EBP/ECX/EAX/EDX/EFLAGS=<...>
guest_stack_return_address=<VA or unavailable>
next_guest_control_transfer=<...>
~~~

If bytes/boundaries cannot be inspected yet, first collect the runtime record without asserting `target_is_instruction_start`.

## 7. Nearest safe P1 action

**Observe before repairing.** Capture a bounded chain of original guest callsite PCs, computed targets, selected dispatch entries, and guest ESP/return values for the three addresses. Then compare it against an authoritative Ghidra byte-level listing and exact function/instruction boundaries. Keep the replay/data-root provenance attached to the trace (full-root v659, 1440 requested frames); do not combine with incomplete-root v660/v661 reports. Do not patch the 0x0064d02a target, split/merge functions, suppress callbacks, add an arbitrary recursion limit, or change renderer/runtime guest semantics based only on this native backtrace.

## 8. Explicit limits / completion status

This report **cannot supply verified disassembled bodies, bytes, exact Ghidra function extents, xref counts or edge instruction addresses** from the pasted evidence. The only source-level body is the reproduced decompilation of 0x004727e3. All other requested static facts are assigned a concrete verification method rather than invented. No local paths were opened and no runtime or renderer files were modified.

**Repository publication:** this Markdown report is authored for branch `work/process-reports`. Its creating commit SHA must be taken from GitHub's file-creation result / the file history, rather than embedded as a self-referential commit hash in the commit content.
