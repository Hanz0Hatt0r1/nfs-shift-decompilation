# Process 3 — P1 display-list frontier, independent evidence audit (2026-10-21)

**Task:** evaluate the historical v672 display-list gate and new bounded v687 consumer-path evidence through `FUN_00831380` and `FUN_005e1d50`, with a narrowly scoped next probe before any D3D9 Draw* claim. This is **not** the earlier iterator audit or Process 1 producer/writer analysis.

**Provenance:** user-supplied full Ghidra pseudocode and bounded v672/v687 runtime trace summaries/excerpts; read-only GitHub context, no local raw logs, project or original executable inspected. Original PC retail SHIFT.exe PE32 x86 v1.02 SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Integrated recompiled runtime ancestry, as supplied: P1 DXT3 `e6f674a6`, P1 integration `1a25ef48`, P2 adapter capability `1fef18a8`; 54 module overrides and nonempty `SHIFT_D3D9_PACKET_CAPTURE_DIR`. **The v672 replay is not a native Windows execution.**

## Verdict — revised after v687

**The old “persistently empty display-list gate” candidate is ruled out as a general explanation for this bounded path.** The v672 trace stopped recording after 8,192 selected events and showed no `FUN_00831380` *in that prefix*. The later v687 evidence establishes **663 successful `FUN_00831380` calls from `FUN_00835590`** (return `AL=1`) and reports their output word as `0x3f800000`. In the same user-provided bounded evidence, **all 663 subsequent `FUN_005e1d50` getter returns on the main path are `EAX=0`**; `FUN_008352f0` was reached only twice from `FUN_008353e0`, **never from `FUN_00835590`** in this window. The nearest *observed* frontier has therefore moved from the old predicate check to **consumption/evaluation of the produced word and the subsequent control-flow decision**.

**Confidence:** high for the reported call/return counts, output word and negative selected Draw* observations *within the stated bounds*; moderate that this is a local skip/failed comparison in the represented consumer path; **no demonstrated causal dependency between this path and missing D3D9 Draw***. The Ghidra body for `FUN_005e1d50` was supplied as `mov eax,[ecx]; ret`; a returned zero with `ECX=0x3f800004` does **not** prove that address was mapped or the original guest load legitimately produced zero. The relevant read-validity and branch operands were not supplied. Nor is the nature/meaning of word `0x3f800000` established by its bit pattern.

Neither `host-frame-loop`, host frames, dispatches, nor selected Draw* absence proves menu/frontend readiness, a race, native retail execution or retail rendering. **No runtime/renderer or guest-state change is justified.**

## Directly established from the supplied functions

### `FUN_0082f3c0`

Full supplied body:

```c
bool __fastcall FUN_0082f3c0(int param_1) {
    return *(int *)(param_1 + 0x24) == 0;
}
```

- `EAX=1` from this Boolean getter entails `*(uint32_t *)(actual_receiver+0x24)==0` **at the moment of the read**, for the verified code path and a valid load. `EAX=0` would entail a nonzero DWORD.
- **Do not name `+0x24` a list length, queue count, pointer, or ownership flag** without producer/XREF evidence. In particular, a zero here proves neither that an Apt display list has zero objects nor that all related lists/states are empty.
- The first two supplied entry samples have distinct receivers: `ECX=0x2002d170` at return address `0x008355ab`, then `ECX=0x2002d1a4`; their concrete checked DWORD addresses would be `0x2002d194` and `0x2002d1c8`, **for those two samples only**. These offsets/addresses do not establish object or class identity.

### `FUN_00831380`

The full supplied pseudocode gates its success path on **`param_1[9] != 0` (offset `+0x24`)** and then `param_1[7]` (offset `+0x1c`) leading to a nonzero DWORD at `[param_1[7]+0x14]`. On that branch it writes one DWORD to `*param_2`, calls `thunk_FUN_00d699b0`, and returns `1`; otherwise returns `0`.

The computed source address includes `([iVar1+0x14]-1) * *param_1 + [iVar1+4]`. This is a **formula**, not proof of a particular buffer type, item count or safe index. The Ghidra `__fastcall` prototype remains a decompiler-derived calling convention.

**Historical v672-only conditional:** if the real argument receiver for `FUN_00831380` were identical to a prior `FUN_0082f3c0` receiver and its `+0x24` remained zero, the first guard would fail. v672 recorded no calls **before trace truncation**; this is **not** an operative explanation for the later v687 path, where the function was called successfully 663 times.

### `FUN_00835590` and `FUN_00835d80`

- The supplied `FUN_00835590` pseudocode repeatedly tests `FUN_0082f3c0()` and iterates through `FUN_00831380()`, `_GetFirstItem_AptDisplayListState__QAEPAVAptCIH__XZ()`, and various virtual calls **only while the predicate returns zero**. The presence of the demangled `AptDisplayListState` accessor name supports that such an accessor is referenced, **not** that the `FUN_0082f3c0` receiver itself is an Apt display-list container or that a game menu/world is active.
- **Critical correction to the supplied pseudocode:** the **first** of the initial two virtual-call loops uses vtable slot **`+0x88`**; the **second** uses **`+0x28`** (not a duplicate `+0x88`). Other displayed slot offsets (`+0x10`, `+0x8c`, `+0x58`, `+0xac`, etc.) are just offsets, not method identities. Neither of these two loops executes its body if its predicate is true.
- The large pseudocode has unproved temporaries (e.g., `piStack_c` used across branches), numerous repeated checks, and indirect calls. Treat it as **Ghidra representation of control flow** requiring instruction-level confirmation for ownership/order and virtual calltargets; do not infer source-level intent, lock discipline or class relationships.
- In the supplied `FUN_00835d80` pseudocode, the call to `FUN_00835590` follows a nontrivial `param_1[0x11e]` gate, a virtual invocation at `+0x44` and other operations, then `D3DPERF_EndEvent`. The final `return (uint)(iVar2 == 0)` is a status for that earlier virtual invocation; **it is not evidence of `FUN_00835590` successfully producing display-list content**. If its early guard is taken, the alternate return masks out the low byte. Do not assign game-state semantics to either return.
- `FUN_00835590` is declared `void` by Ghidra. The observed `EAX=1` upon return is **not a documented Boolean success value**; it can simply be a residual register value from a prior predicate.

## Historical v672 bounded trace (prefix only; user-provided, raw log not re-read)

- Probe: 360 requested/rendered **host frames**, exit `0`, `host-frame-loop`, `blocker=null`, 1,737,380 P-code dispatches, 4,728 unique functions, three workers waiting, zero validation errors; `guest_draw_translation=false`, `retail_rendering_proven=false`, main guest function `0x00843ed0`. These are diagnostics, **not** frontend, race or native retail launch proof.
- The host bridge recorded 1,110 Clear requests / 360 submissions; 1,108 Present requests / 360 submissions and 748 pending Presents. **No conclusion about the producer of the checked field follows from these counts**.
- Selected-target/caller filters: `0x00835590,0x0082f3c0,0x00831380,0x00835d80`, caller filter `0x00835d80`, live logging; **no memory-slot sampling**. The selected trace **hit its hard cap of 8,192 entry/return events**: `guest_call_trace_truncated=true`. Any zero-call observation is limited to **that prefix**, not the entire execution.
- Recorded prefix: `FUN_00835590` **264 entries / 264 returns**, all its recorded `EAX=1`, called by `FUN_00835d80`; `FUN_0082f3c0` **5,544** completed calls from `FUN_00835590`, each `EAX=1`; `FUN_00831380` **zero** recorded entries; `FUN_00835d80` **265** calls and returns, `EAX=1`. The arithmetic ratio `5544/264=21` matches repeated predicate testing, **but does not by itself establish an exact per-invocation sequence, pairing or count after truncation**.
- First recorded edge: `0x00835d80 → 0x00835590` at return address `0x00835e9d`, thread `1125911`, dispatch `463038`; first getter `0x00835590 → 0x0082f3c0` returns to `0x008355ab`, thread `1125911`, dispatch `463039`, getter `ECX=0x2002d170`, `EAX=1` on return. Second getter entry `ECX=0x2002d1a4`. These are **specific call/return observations**, not a class identification.
- The raw local trace is identified by supplied SHA-256 `c96f00890cf4509b73b93c8f3e855880f2883ab8f9e665fa2efe2fd8f470b90e`; it was not accessible for this audit.

**Historical interpretation only:** this **capped prefix** exhibited predicate values consistent with skipped loops, but **did not cover the whole bounded execution**. v687 later confirms many successful `FUN_00831380` executions. Consequently v672 cannot support an assertion that this gate remains empty or that consumer execution is absent. No inference about a missing producer, a UI/menu state or a Draw* blockage follows.

## New bounded v687 evidence (user-provided; latest checked window)

- Original retail PE identifier as above; **integrated recompiled P-code replay**, **not native SHIFT.exe execution**. Runtime SHA-256 `d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8`. The reported run covers **360 host frames**, exit 0, `host-frame-loop`, **1,741,305 dispatches**, **4,729 unique functions**, `blocker=null`, **3 waiting workers**, **0 validation errors**. `guest_draw_translation=false` and `retail_rendering_proven=false`.
- Raw trace SHA-256 **`13d0557bf9d30b9cba3633ec3d970527e9b5755d9e0c5ae245f5d907a2bd3eef`**, **8,315,388 bytes**, `guest_call_trace_truncated=false`. User reports the **sole selected caller filter `0x008353e0`**; **2,008 entry / 2,007 return** records in the filtered stream (one entry lacks a matched return within those counts), with **664 calls to `0x004cb900`**. This count does **not** establish the semantics or downstream effects of `0x004cb900`.
- Supplied same-v687 target-level observations additionally report **663 calls to `FUN_00831380` from `FUN_00835590`**, all returning `AL=1`; the output word was **`0x3f800000`**. **663 subsequent `FUN_005e1d50` getter invocations** on the `FUN_00835590` path each returned `EAX=0`. These reports **supersede the “no `00831380` observed” v672-prefix reading**. The v687 data do not show the precise branch instruction deciding what to do with the getter result.
- `FUN_008352f0` had **two** observed calls, both with caller `0x008353e0`; **none** with caller `0x00835590` in this bounded evidence. No selected `DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP` or `DrawIndexedPrimitiveUP` import appears in the bounded run. Neither result proves an actual Draw* call should have occurred on this path.
- **Important attribution/coverage caveat:** a trace configured with only `SHIFT_TRACE_GUEST_CALLER=0x008353e0` would normally select that **immediate caller** and not automatically every nested call from `0x00835590`. Therefore the provided 663 target calls and getter outcomes are treated as **user-provided bounded observations**, not independently reconstructed solely from the 2,008 caller-selected entries. Their trace-source association and the unmatched entry/return pair require confirmation before reconstructing a complete nested sequence from that one trace stream. `no truncation` does not by itself establish that unselected callers were recorded.
- **Layout/provenance limits:** the given `0x3f800000` is an observed 32-bit payload, **not proof of a float, object, class or valid dereference**. The previous user-provided Ghidra getter body `mov eax,[ecx]; ret` at `0x005e1d50`, with earlier recorded main-path getter `ECX=0x3f800004`, motivates a validity check; v687 does not provide a mapped/unmapped read verdict at that address. Do not turn a returned `EAX=0` into a claim of readable mapped data. No producer/writer/xref conclusion is attempted here; that work belongs to Process 1.

**Bounded interpretation:** the consumer executes and returns success on the main path, and a later getter consistently returns zero; the named follow-up helper is not observed with caller `FUN_00835590`. This localizes **where the candidate consumer path stops being demonstrated**. It does *not* establish whether the getter's zero comes from valid guest memory, an invalid/unreadable address, an absent initialization, a P-code fidelity defect, or game-intended branching. It also does not prove a causal chain to a Draw* call. Host activity is not game/menu launch proof.

## Exactly one minimal next consumer-to-Draw* check (read-only)

**One replay; one consumer-path conditional capture** around the **first successful `0x00835590 → 0x00831380` return followed by `0x005e1d50`** (plus at most one later confirming occurrence). Do **not** re-run producer/writer provenance or expand scope to unrelated classes. Retain the 360-host-frame boundary or stop earlier once a full consumer decision has been recorded; include `selected filters`, `guest_call_trace_truncated`, first/last covered dispatch/frame and matched entry/return counts.

**Select exact targets** `0x00831380,0x005e1d50,0x008352f0` and the four actual D3D9 `DrawPrimitive/DrawIndexedPrimitive/DrawPrimitiveUP/DrawIndexedPrimitiveUP` imports as **terminal correlation markers**; restrict detailed per-instruction capture to the actual `0x00835590` caller path. Do not mistake `SHIFT_TRACE_GUEST_CALLER=0x008353e0` alone for coverage of nested calls from `0x00835590`, and do not exhaust a fixed trace cap on unrelated events.

**Capture in this exact order:**

1. **C0 — producer-of-output as consumer entry, not writer analysis:** on the selected `0x00831380` call, thread ID, caller function and return site, entry `ECX` and `EDX`, valid/readable `*EDX` before return; immediately on return, record `AL/EAX`, valid/readable `*EDX` after return and observed **`0x3f800000`**. Treat `EDX` as the **observed output location only after verifying the actual x86 argument mapping**; a guest stack address must be bounds-checked.
2. **C1 — consumer address computation:** capture the exact `0x00835590` instruction(s) transforming the output to the next getter receiver; record input DWORD, computed `ECX` (prior example `0x3f800004`), `ESP/EBP/EFLAGS`, the immediate caller/callsite and thread. **Do not assume numeric `+4` proves a valid pointer or object layout**.
3. **C2 — getter instruction and memory result:** at `0x005e1d50` (`mov eax,[ecx]; ret` as supplied), capture target `ECX`, computed guest load address, **mapped/range/read-success flag** and raw 4-byte value *only if readable*, followed by `EAX` on return. Explicitly distinguish “valid mapped zero” from “unreadable/failed diagnostic sample” and from any runtime-generated default/incorrect load. Avoid unconditional read of `0x3f800004` if it is not a confirmed valid mapped guest address.
4. **C3 — immediate comparison/branch and descendant:** capture the **actual decoded guest compare/test and taken edge** after the `0x005e1d50` return (the return site was previously reported as `0x00835b5b`), with operands/flags, next call target, and whether `0x008352f0` or a particular indirect call is reached *from this `0x00835590` invocation*. If a selected Draw* import occurs, capture its direct caller and active guest ancestry; if none occurs, record the precise bounded negative only. Do not assign menu/world identity from the function addresses.

**Decision rule:** a validated memory read returning zero plus a confirmed taken skip proves **the local predicate branch**, not why that branch or initial value is appropriate. An unreadable guest load, incorrect register/stack mapping or disparity between read bytes and `EAX` establishes a concrete **runtime-fidelity candidate** for P1 to test. A downstream Draw* edge requires a directly observed matching call chain, not co-occurrence or host-frame count. If the branch is game-intended or lacks a verified Draw* descendant, the rendering gap remains elsewhere.

## Decision / limitations

**Revised bounded decision after v687:** v672 established only a capped prefix with zero `FUN_00831380` events; v687 establishes successful `FUN_00831380` execution from `FUN_00835590`, followed by zero-valued `FUN_005e1d50` returns and no `FUN_008352f0` call from that main path in the observed window. Therefore **persistent emptiness at `FUN_00831380` is no longer a supported current blocker**; the closest *testable local* frontier is the **consumer getter/load and the comparison/branch immediately afterward**. This is not yet a proven reason for missing Draw* imports, nor evidence that the original executable, frontend, race, or rendered image was launched.

**Unknowns:** exact read validity of `ECX=0x3f800004`; exact output-to-getter register transformation; actual taken branch from `0x00835b5b`; whether any excluded/unselected path eventually calls Draw*. Producer/writer/root-cause analysis is out of scope. No guest state, execution ordering or API value may be altered to manufacture progress.

**No runtime or renderer change recommended.**

**GitHub diagnostics/API known from earlier code review:** [`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp) documents `SHIFT_TRACE_GUEST_CALL_TARGETS`, `SHIFT_TRACE_GUEST_CALLER`, target-relative slot sampling, immediate-caller selection and bounded event trace; [call trace event fields](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/include/shift_recompiled_pcode_module.hpp). This report reuses GitHub code knowledge and user-supplied runtime/Ghidra facts; it does not independently validate raw local logs.
