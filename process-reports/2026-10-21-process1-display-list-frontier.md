# Process 3 — P1 display-list frontier, independent evidence audit (2026-10-21)

**Task:** classify the v672 `FUN_00835d80 → FUN_00835590 → FUN_0082f3c0` path, the observed absence of `FUN_00831380`, and the smallest non-invasive probe to distinguish empty state from missing producer/initialization before D3D9 Draw*. This is **not** the earlier iterator audit.

**Provenance:** user-supplied full Ghidra pseudocode and a bounded v672 runtime trace summary/excerpts; read-only GitHub context, no local raw logs, project or original executable inspected. Original PC retail SHIFT.exe PE32 x86 v1.02 SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Integrated recompiled runtime ancestry, as supplied: P1 DXT3 `e6f674a6`, P1 integration `1a25ef48`, P2 adapter capability `1fef18a8`; 54 module overrides and nonempty `SHIFT_D3D9_PACKET_CAPTURE_DIR`. **The v672 replay is not a native Windows execution.**

## Verdict

**High confidence for a *local, bounded gate observation*, low confidence for a causal Draw* blocker:** the recorded `FUN_0082f3c0` predicates returned true (`EAX=1`), so their checked **DWORD `[receiver+0x24]` was zero at each such invocation**, assuming the supplied decompilation accurately reflects the P-code path. This makes `FUN_00835590` skip its `while (predicate == 0)` bodies on those observed checks. The 8,192-entry trace prefix recorded no `FUN_00831380` calls. **No evidence distinguishes an intentionally empty/idle state from missing population/initialization**, and no typed/dynamic path to a D3D9 Draw* callsite is supplied. Treat the state-list gate as the *nearest useful measurement point*, **not a demonstrated rendering blocker**.

No guest semantic change (forcing the field nonzero, synthesizing entries, changing scheduling, or bypassing a branch) is justified.

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

**Conditional only:** if the real argument receiver for `FUN_00831380` were identical to the receiver previously checked by `FUN_0082f3c0`, and its `+0x24` word remained zero, the first guard in `FUN_00831380` would fail. **No such receiver alias was measured in v672:** that function has zero recorded calls.

### `FUN_00835590` and `FUN_00835d80`

- The supplied `FUN_00835590` pseudocode repeatedly tests `FUN_0082f3c0()` and iterates through `FUN_00831380()`, `_GetFirstItem_AptDisplayListState__QAEPAVAptCIH__XZ()`, and various virtual calls **only while the predicate returns zero**. The presence of the demangled `AptDisplayListState` accessor name supports that such an accessor is referenced, **not** that the `FUN_0082f3c0` receiver itself is an Apt display-list container or that a game menu/world is active.
- **Critical correction to the supplied pseudocode:** the **first** of the initial two virtual-call loops uses vtable slot **`+0x88`**; the **second** uses **`+0x28`** (not a duplicate `+0x88`). Other displayed slot offsets (`+0x10`, `+0x8c`, `+0x58`, `+0xac`, etc.) are just offsets, not method identities. Neither of these two loops executes its body if its predicate is true.
- The large pseudocode has unproved temporaries (e.g., `piStack_c` used across branches), numerous repeated checks, and indirect calls. Treat it as **Ghidra representation of control flow** requiring instruction-level confirmation for ownership/order and virtual calltargets; do not infer source-level intent, lock discipline or class relationships.
- In the supplied `FUN_00835d80` pseudocode, the call to `FUN_00835590` follows a nontrivial `param_1[0x11e]` gate, a virtual invocation at `+0x44` and other operations, then `D3DPERF_EndEvent`. The final `return (uint)(iVar2 == 0)` is a status for that earlier virtual invocation; **it is not evidence of `FUN_00835590` successfully producing display-list content**. If its early guard is taken, the alternate return masks out the low byte. Do not assign game-state semantics to either return.
- `FUN_00835590` is declared `void` by Ghidra. The observed `EAX=1` upon return is **not a documented Boolean success value**; it can simply be a residual register value from a prior predicate.

## Directly established by the bounded v672 trace (user-provided; raw log not re-read)

- Probe: 360 requested/rendered **host frames**, exit `0`, `host-frame-loop`, `blocker=null`, 1,737,380 P-code dispatches, 4,728 unique functions, three workers waiting, zero validation errors; `guest_draw_translation=false`, `retail_rendering_proven=false`, main guest function `0x00843ed0`. These are diagnostics, **not** frontend, race or native retail launch proof.
- The host bridge recorded 1,110 Clear requests / 360 submissions; 1,108 Present requests / 360 submissions and 748 pending Presents. **No conclusion about the producer of the checked field follows from these counts**.
- Selected-target/caller filters: `0x00835590,0x0082f3c0,0x00831380,0x00835d80`, caller filter `0x00835d80`, live logging; **no memory-slot sampling**. The selected trace **hit its hard cap of 8,192 entry/return events**: `guest_call_trace_truncated=true`. Any zero-call observation is limited to **that prefix**, not the entire execution.
- Recorded prefix: `FUN_00835590` **264 entries / 264 returns**, all its recorded `EAX=1`, called by `FUN_00835d80`; `FUN_0082f3c0` **5,544** completed calls from `FUN_00835590`, each `EAX=1`; `FUN_00831380` **zero** recorded entries; `FUN_00835d80` **265** calls and returns, `EAX=1`. The arithmetic ratio `5544/264=21` matches repeated predicate testing, **but does not by itself establish an exact per-invocation sequence, pairing or count after truncation**.
- First recorded edge: `0x00835d80 → 0x00835590` at return address `0x00835e9d`, thread `1125911`, dispatch `463038`; first getter `0x00835590 → 0x0082f3c0` returns to `0x008355ab`, thread `1125911`, dispatch `463039`, getter `ECX=0x2002d170`, `EAX=1` on return. Second getter entry `ECX=0x2002d1a4`. These are **specific call/return observations**, not a class identification.
- The raw local trace is identified by supplied SHA-256 `c96f00890cf4509b73b93c8f3e855880f2883ab8f9e665fa2efe2fd8f470b90e`; it was not accessible for this audit.

**Interpretation:** The selected prefix strongly supports an *empty-or-inactive predicate branch* on this `FUN_00835590` invocation family. **It does not prove the data structure is correctly empty, that its producer was called or skipped, or that this is the nearest cause of missing Draw*.** Alternative interpretations include intentionally idle state, a producer not reached yet, failed setup, different state object, later population after trace cap, another rendering path, or unrelated missing Draw* capture/dispatch coverage.

## Exactly one minimal next P1 probe (read-only, single bounded replay)

**Trigger/window:** the first `0x00835d80 → 0x00835590` call, then record a *conditional*, bounded history for the first **two distinct `FUN_0082f3c0` receiver addresses** plus any receiver that changes state, ending at (a) the first nonzero `+0x24` observed, (b) the first `FUN_00831380` entry, or (c) the end of the same 360-host-frame window. Keep coverage metadata, and preserve ordering **within the same run**. Do not change any guest memory, EFLAGS, branches, virtual calls or scheduling.

**Targets/callers:** exact guest addresses `0x00835d80` (caller), `0x00835590` (callee), `0x0082f3c0` (predicate target), `0x00831380` (candidate consumer); add the exact **`_GetFirstItem_AptDisplayListState__QAEPAVAptCIH__XZ`** runtime target only **after** its address is resolved from the actual import/callsite; do not invent an address. Record the four D3D9 `DrawPrimitive/DrawIndexedPrimitive/DrawPrimitiveUP/DrawIndexedPrimitiveUP` dispatch/imports only as terminal correlation markers, if reached.

**Ordered samples:**

1. **S0 — caller gate:** thread ID, guest function/callsite, caller `ECX` (the `FUN_00835d80` receiver), `ESP`, `EAX`, `[caller_ECX + 0x478]` corresponding to `param_1[0x11e]` **only if the receiver is a verified valid guest address**, and whether `0x00835590` was reached. Record the return address `0x00835e9d` if observed, without making it a universal invariant.
2. **S1 — each sampled getter entry before the load:** guest thread, nested caller and return address, exact `ECX`, computed `A=(uint64_t)ECX+0x24`, address/range-validity, and **32-bit DWORD `[A]`**. For the supplied first two receiver values, `A=0x2002d194` and `0x2002d1c8`. Skip invalid/low addresses; do not dereference arbitrary pointers or use offsets with the wrong base. Immediately following the getter's return record `EAX`, the Boolean branch taken in `FUN_00835590`, and timestamp/sequence.
3. **S2 — producer/write provenance during this same window:** attach **read-only observation** to DWORD writes touching each validated dynamic `A`; record old/new DWORD, writer guest function and instruction, thread ID, caller ancestry, and whether an initialization routine was actually executed. Capture the first valid existing value **before** the first getter, not only its last value. A write of 0 is an event, not proof of an incorrect value. If no writer appears, report exactly the covered interval; producer could have run before the probe.
4. **S3 — first `FUN_00831380` call if observed:** record actual argument receiver and output pointer, `[receiver+0x24]`, `[receiver+0x1c]`, and only **after** validating the latter pointer, `[nested+0x14]` and `[nested+0x4]`; `*param_1`, `*param_2` before/after, return value and any subsequent `GetFirstItem` / indirect callsite. Compare receiver identity with S1; the guards may concern a different instance. If not reached, record *not observed in window*, not globally absent.
5. **S4 — correlation/coverage:** annotate the first matching Draw* call if one occurs, with guest thread/caller ancestry; otherwise report **zero observed within the bounded filtered window**. Include `guest_call_trace_truncated`, selected-event count and last covered frame/dispatch. Aggregation must keep **first/last per (thread, receiver, callsite), every value change, every writer event, first consumer entry and terminal event** without exhausting 8,192 slots on 5,544 repetitive true predicates. If the existing fixed trace API cannot do that without truncation, use read-only conditional guest-memory watch/diagnostic sampling at these exact points rather than claiming full coverage from `SHIFT_TRACE_GUEST_CALL_TARGETS` alone.

**Do not use the old trace's `SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS` without checking its base:** GitHub's `record_guest_call_trace` samples those relative to **target entry ECX for every selected target**, whereas caller slots use caller-entry ECX. The shown default target selection would sample unrelated `0x00835d80`/`0x00835590` receivers. For `+0x24`, sample **only on actual `0x0082f3c0` entry** and only if `ECX+0x24` does not overflow 32-bit address space, is outside reserved low memory and passes the guest memory validity read. Distinguish unreadable slots from valid zero DWORDs.

**Classification boundary:**
- A previously nonzero `[A]` with observed producer write, then a correctly checked transition to zero, can support a completed/drained state **for that receiver and window** if callsites corroborate it.
- A known producer **seen failing/skipping an expected write** before a persistent zero getter and consumer never entered can identify a *candidate missed-initialization path*, but the producer precondition and exact writer semantics still require xrefs/instruction proof.
- Only zero getter results, even for all 360 frames, **cannot by themselves tell normal emptiness from missing initialization**; a missing write within the window might have happened before it or be intentionally absent.
- Nonzero `[A]` followed by `FUN_00831380` execution shows an alternate guest path, **not by itself a Draw* precursor**. Link to Draw* only with actual call ancestry/dispatch evidence.

## Decision / limitations

**Current evidence: high confidence in the zero-DWORD predicate observation and lack of consumer entries in the capped prefix; medium confidence that those checks explain skipping the represented loops; no supported causal claim about missing Draw*, menu/frontend readiness, race, class identity or correct population.** The nearest tractable question is *who owns/writes each checked `+0x24` word and whether the branch changes during an observed frame window*. A single ordered, receiver-scoped, read-only probe can strengthen the classification; absent a known producer contract, it may still leave the normal-empty vs missed-producer distinction unresolved.

**No runtime or renderer change recommended.**

**GitHub diagnostics/API checked in prior P1 audit:** [`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp) (`SHIFT_TRACE_GUEST_CALL_TARGETS`, `SHIFT_TRACE_GUEST_CALLER`, `SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS`, `record_guest_call_trace`, fixed event cap), [`native_runtime/include/shift_recompiled_pcode_module.hpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/include/shift_recompiled_pcode_module.hpp) (call event fields). This report cites the specified Ghidra/raw-log facts as *user-provided*, not newly independently verified.
