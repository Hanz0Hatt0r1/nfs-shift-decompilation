# Process 3 — independent P1 worker/predicate scheduler audit (2026-10-21)

**Scope:** read-only independent audit of guest Win32 thread/scheduler semantics, historical v520 predicate stall, related in-repository evidence and regression tests. No runtime/renderer changes; no access to external local runtime, original PE, raw logs or Ghidra. All off-repository paths in historical evidence are provenance only, not inspected files.

**Retail identity:** SHIFT.exe, PE32 i386 retail 1.02, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Answer and status

**Closest testable v520 blocker: cooperative guest-worker starvation at the main-thread predicate polling loop after a valid ResumeThread, not a proven defective predicate or failed Win32 ResumeThread.** This is now much stronger than an open hypothesis: in-repository v527 evidence reports that after a **64 successful guest-call-return scheduling quantum**, guest worker **thread ID `0x00010006`**, writer `0x00649b10`, stored **`0x00000006`** at predicate word `0x27f39c64`; `0x006550f0` then returned `EAX=1`, and calls `0x00655110` and `0x005ab560` followed. This is a **bounded P-code replay observation** of a genuine guest write, not a forced predicate value. A synthetic fixture separately validates worker progress while the main guest thread busy-polls without `SwitchToThread`. This supports scheduler starvation as the v520-local cause. It does **not** prove fully faithful Win32 scheduling, frontend, race or game presentation, or the state of other workers in v666.

**Recommendation:** do not change guest thread/Win32 API semantics on v666 counters or the old v520 symptom. Retain the evidence-backed return quantum; use one bounded, address-scoped, read-only trace below if the symptom recurs or a new scheduler blocker is suspected.

## Evidence separated by certainty

### Direct in-repository historical observations

1. **v516:** caller `0x005ab6c0` completed calls to `0x00649cb0` (`EAX=0x008f3d01`) and `0x00655040` (`EAX=1`). It repeatedly invoked predicate `0x006550f0`, receiving `EAX=0` at return address `0x005ab6f7`; `0x00655110` was not reached before the bounded timeout.
2. **v517:** at the predicate call `ECX=0x24219ac0`, `[ECX+4]=0x27f39bf0`. The predicate uses **that pointer + `0x74`**, giving candidate address `0x27f39c64`. The logged direct `[ECX+0x74]` is **not** the indirect predicate word; do not confuse them.
3. **v518/v519:** actual indirect word `[0x27f39c64]=0x00000002`, so **bit 2 (mask `0x00000004`) is clear**. Last recorded writer `0x006496f0` stored `0x00000002` at dispatch 6,975,023. `0x00655040` tail-dispatches to `0x006496f0`; that body clears bit 3 and calls through pointer slot `0x00aa62b8`.
4. **v520:** live trace of `0x006496f0` records call through trap `0xf0000b30` resolved to `KERNEL32.dll!ResumeThread`, thread-handle argument **`0x00080060`**, return address `0x00649711`, `EAX=1` at dispatch 6,975,024. The 180-second run timed out in predicate polling; it did not expose a worker write. `EAX=1` means **previous suspend count 1 in the shown compatibility implementation**, not proof that this worker was scheduled or reached a particular writer.
5. **Pre-change main replay:** repeatedly false poll was stopped manually around dispatch 6,983,183; not a guest timeout, game result or frontend proof.
6. **v527 after return quantum:** exact reported predicate transition `0x27f39c64: 0x00000002 → 0x00000006`, last writer `0x00649b10` on guest thread ID `0x00010006`; poll `0x006550f0` returned 1; continuation reached `0x00655110`, `0x005ab560`. The replay subsequently stopped on unrelated missing P-code export `rvi_0057da20`. These are **in-repository reports with SHA-256 hashes of out-of-repository run files**; the underlying raw files were not independently inspected here.

References:
- [Post-PR #2123 v506–v520 evidence](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261020/post_pr2123_retail_frontier_followup.json)
- [Process 1 scheduler return-quantum, v520/v523/v524/v527 evidence and limitations](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/process1_scheduler_return_quantum.json)
- [Frontier narrative](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/docs/RETAIL_FRONTIER_AUTOMATION.md)
- [PR #2129: schedule guest workers between dispatch returns](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2129)

### Scheduler and Win32 compatibility, checked against current source

Source: [`native_runtime/src/recompiled_pcode_module.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp).

- `GuestThread` holds `start_address`, `parameter`, `suspend_count`, `started`, `completed`, `runnable`, `waiting`, `wait_handle`, `wait_result`, deadline, guest stack/TEB and coroutine (approximately lines 818–858).
- `CreateThread` constructs a guest thread and honors creation flag `0x4` (`CREATE_SUSPENDED`) via `suspend_count=1`. It initializes guest stack/TEB; an initially unsuspended thread enters `run_guest_thread` (lines 5054–5127).
- `ResumeThread` (lines 5129–5147) validates the handle, **returns the old suspend count**, decrements it if nonzero; only after count reaches zero does it conditionally prepare/start or enqueue an unfinished thread. **No assertion in this API path states that the worker has actually executed.** The v520 `EAX=1` is compatible with an old count of 1 transitioning to 0.
- `run_guest_thread` (lines 5045–5052) starts synchronously when no guest coroutine is active; otherwise prepares the guest coroutine and queues it. `enqueue_guest_thread` (lines 4649–4658) skips absent, completed, **waiting**, still-suspended or already-runnable workers. A resumed-but-waiting thread therefore needs its separate wake path.
- `run_guest_scheduler` (lines 4836–4914) selects ready queue entries, discards completed/waiting/still-suspended work, runs guest coroutines via `swapcontext`, wakes expired waits and has bounded slices. A ready worker does not execute merely because its handle is in the map.
- `SwitchToThread` (lines 4211–4224) is an explicit guest yield when in cooperative scheduler; `Sleep(0)` also yields, and waits mark the caller waiting and yield (lines 4245–4287, 5392–5424). A busy polling guest function need not do any of those.
- **Fairness fix:** `call_callback` (approximately lines 1008–1031), only after successful nested dispatch in an active guest coroutine/scheduler, increments **per-thread** `dispatch_returns_since_quantum`; after **64** such returns, if `ready_guest_threads` is nonempty, it requeues the current guest thread and yields. This is cooperative fairness at guest-call boundaries, **not instruction-/time-based preemption**. A single long P-code function with no returning nested calls may still monopolize a slice. No guest memory or API return value is substituted by this logic.
- Scheduler snapshot `worker_waiting_count` (approximately lines 15267–15274) simply counts entries with `thread.waiting == true`; it omits their handles, `wait_handle`, cause, start function, or whether the v520 worker is among them.

These source facts justify scheduler starvation as the **nearest v520-specific compatibility gap**, while leaving correctness of all wait/wake paths and arbitrary thread interleavings unproven.

### Regression coverage and limits

- [`native_runtime/tests/recompiled_pcode_supplement_fixture.c`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/tests/recompiled_pcode_supplement_fixture.c#L185-L220): after suspend/resume, the main guest fixture polls a worker-written marker through nested `ctx->call(0x004010a0)` up to 1,024 times **without calling `SwitchToThread` inside the interval**. It requires the marker to become `0x1234`.
- [`native_runtime/tests/recompiled_pcode_module_check.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/tests/recompiled_pcode_module_check.cpp#L7940-L7964): checks pending entrypoint, marker written by worker, subsequent `run_guest_threads()` completion. Separate [thread API assertions](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/tests/recompiled_pcode_module_check.cpp#L7363-L7400) check suspended creation, previous suspend-count returns (2 then 1), GetExitCodeThread, wait and cleanup.
- Scheduler evidence reports focused CTest passed, 49 local workflow assertions, 61 fixture dispatches including 51 polls. These reports are **recorded** success, not tests independently rerun in this audit. They validate the specific synthetic scheduling pattern, not all Win32 wait/priority/time-slice cases or the exact retail program.

### Later retail checkpoint (facts supplied with the request, not proof of worker identity)

- v662: stop on unsupported managed texture description after 42,542,707 dispatches and 6,529 unique functions.
- v666: 1,440 requested/rendered **host** frames; 44,964,062 dispatches, 6,625 unique functions, `blocker=null`, `worker_waiting_count=11`, zero validation errors; `guest_draw_translation=false`, `retail_rendering_proven=false`. Additional Clear/Present counters are not guest-worker execution evidence.
- These supplied figures do **not** identify the waiting thread handles, their wake conditions, or the current predicate value. No conclusion that the v520 worker still stalls follows. They are not proof of Windows retail execution, frontend/race or a later successful guest draw.

## Precisely bounded, single read-only P1 probe (no semantic change)

**One replay, triggered on the first relevant `0x006496f0 → ResumeThread` sequence, stopped after the first successful `0x006550f0` poll or a fixed budget of 256 subsequent predicate polls, whichever occurs first.** Capture only the following ordered snapshots; do not patch memory or force a scheduler yield. Existing caller/provenance-tracing knobs shown in v518–v520 (`SHIFT_TRACE_GUEST_CALLER`, `SHIFT_TRACE_GUEST_CALL_STACK_SLOTS`, `SHIFT_TRACE_GUEST_PROVENANCE`, `SHIFT_TRACE_GUEST_CALL_LIVE_LOG`) may assist, but per-thread queue fields need read-only scheduler instrumentation or a debugger; they are **not** in the aggregate snapshot.

1. **S0 — before import at `0x006496f0`:** current guest thread ID/handle, actual guest import slot **`[0x00aa62b8]`**, resolved trap, **import argument thread handle** (v520 example `0x00080060`), guest `ESP`, `ECX`; `guest_threads[handle]` fields `id/start_address/parameter/suspend_count/started/completed/runnable/waiting/wait_handle/wait_result`; membership/order of `ready_guest_threads`; `scheduler_context_active/guest_coroutine_active`. Independently read `P=[ECX_poll+4]` and `Q=P+0x74` from the poll's *actual* `ECX` when it becomes available. v520's `Q=0x27f39c64` is **run-specific evidence, not a universal hardcoded address**.
2. **S1 — immediately after return at `0x00649711`:** `EAX` (previous suspend count), `guest_last_error`, same handle's **post** state and ready-queue membership, plus predicate word `[Q]` once computed. Observe whether `suspend_count 1→0` leads to queued or synchronous execution, *not merely* a successful API return.
3. **S2 — the first scheduler decision while main thread polls:** per-thread successful-dispatch-return counter (especially reaching 64), `ready_guest_threads` head/size, `current_guest_thread_handle`, whether `yield_current_guest_thread(true)` occurred, next selected worker handle and entry target. Record skipped queue entries with their `waiting/suspend_count/completed` state. This separates *ready but starved* from *not ready or legitimately waiting*.
4. **S3 — first actual execution of the resumed handle and first write touching `Q`:** guest thread ID/handle, function entry and return sequence, `start_address`, wait/API outcome if it blocks, and any 4-byte write covering `Q` with **before/after DWORD** and writer address. Specifically include evidence for or absence of **`0x00649b10`**, known v527 writer; do **not** assume only that function can ever write the field.
5. **S4 — next predicate call/return `0x005ab6c0 → 0x006550f0`, return site `0x005ab6f7`:** poll `ECX`, `[ECX+4]`, derived `Q`, DWORD before/after, `EAX` and whether the caller advances to `0x00655110`. Preserve thread identity and sequential event order from S0–S4.

**Classify from the one trace:**
- **Resume count zero + runnable queued + repeatedly executing main poll + no scheduler switch/opportunity:** guest fairness/starvation path.
- **Resume count zero but worker not queued:** inspect `waiting`, `completed`, `started`, coroutine state and applicable wake transition; possible compatibility defect **or legitimate wait**, not enough to call it a bug by itself.
- **Worker scheduled and reaches intended writer, `Q` changes to include `0x4`, poll returns 1:** v520-local gate passed; investigate elsewhere.
- **Worker is scheduled but blocks or skips writer, poll stays false:** worker dependency/game state versus guest wait/error semantics remains unresolved; correlate the exact guest wait handle, result, and producer. Do not force bit 2.
- **Worker completes normally without setting bit 2:** compare actual guest control flow and prerequisites before labeling the zero state a runtime error.

## Other remaining alternatives / proof boundaries

- Correct (game-defined) delay or unmet worker prerequisite; worker might be waiting on a real event/semaphore/IO rather than starved.
- Guest wait/wake, suspend/resume, startup parameter or thread-context compatibility mismatch on **another** path; no full Windows semantic-equivalence proof.
- Unexpected ordering of pointer/word initialization and later updates; v517 shows why the indirect `[ECX+4]+0x74` must be traced rather than inferring a type from nearby offsets.
- Trace truncation/timeouts and host scheduler fairness differences; the v520 bounded timeout and v524 manual stop alone cannot establish a permanent deadlock.
- v666 aggregate waiting count cannot identify any particular guest worker. Return quantum is heuristic cooperative scheduling, not preemption of non-returning P-code loops.

**Decision:** the v520 starvation diagnosis is supported by the controlled v527 transition and regression. Do **not** introduce a new scheduler or Win32-semantic workaround solely based on the old v520 observation or v666 dispatch/frame/waiting counts. Only a fresh address- and handle-scoped ordered trace can justify a new change.

**Source/audit boundary:** reviewed GitHub public branch sources, evidence JSON and docs, PR #2129 and static test source; no local logs, binaries or Ghidra were opened; no tests were rerun. This report changes no runtime files.
