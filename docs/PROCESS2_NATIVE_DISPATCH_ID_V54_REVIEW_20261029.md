# Native dispatch-ID join and ring-worker idle review — v54

Date: 2026-10-29
Scope: review the supplied P1 v54 dispatch-ID join against the Native plugin
implementation. No runtime or guest state was changed.

## v54 observation supplied by Process 1

P1 reports a direct join for the guest worker-ring producer store
`0 -> 1` at `0xB7368C18`: GDB sampled dispatch ID `0xEE5` at
`sub_823B8C60+333` while executing inside `sub_823B37B8`. The matching Native
record is source-1 PM4 trace #1190, generation 1, ring `0x09752580`, batch
`6062/6065`, source IB `0x09743F20+0x5C`, raw words `[0xC0005400, 0x4]`, CPU
mask `0x04`. Callback entry was 04:18:03.340, the producer store 04:18:03.345,
and callback return 04:18:03.348.

This is a direct per-thread dispatch-ID join, not a timestamp-only match. It
confirms this one store happened inside that source-1 callback. The run saw no
consumer-index store or eligible completion; the manager counter remained
`+1`. The capture ended with the GPU RingWorkerLoop asleep and the main guest
thread at `sub_823B31A0`. This run therefore does not show the guest consumer
processing the queued record.

## Getter safety

In `native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp`:
`active_gpu_dispatch_id` is a `thread_local uint64_t`, initialized to zero
(line 100).
`ScopedGpuDispatchId` saves the previous value, installs the current dispatch
ID, and restores the saved value on scope exit. `DispatchGuestInterrupt` creates
that scope immediately around the synchronous `ExecuteInterrupt` call. The
scope is at lines 106–112 and 2096–2098; the exported
`shift_native_gpu_trace_dispatch_id_v1()` at lines 4347–4350 only returns the
calling thread's TLS value.

Consequently the getter itself performs no guest-memory write, shared-state
mutation, lock acquisition, or cross-thread read. Concurrent callbacks on
different host threads see their own IDs, and nested scopes restore the prior
ID. A call on a thread outside an active callback returns zero. The v54 value
`0xEE5` at the producer watchpoint is consistent with the callback thread and
scope described above.

GDB still has to execute an inferior function call to sample the export; that
debugger stop/call/resume can perturb host scheduling even though the getter is
side-effect-free. P1 reports scheduler-locking was restored immediately after
the read and observed no guest writes by the probe. The exact packet-ID join
is valid; for timing-sensitive comparisons, retain a no-getter control run or
sample the TLS value through a debugger-side read if the TLS address is
available.

## Why the GPU ring worker can be asleep

`RingWorkerLoop` waits under `ring_mutex_` until shutdown or
`ring_initialized_ && ring_read_pointer_ != ring_write_pointer_`. A CP_RB_WPTR
MMIO update stores the new GPU-ring write pointer and calls
`ring_changed_.notify_one()` (wait predicate at lines 2499–2502, notification at
2352). At batch completion, the worker publishes its read pointer. When the
GPU PM4 ring is empty, the next wait is expected.

The watched guest worker-ring producer/consumer at `0xB7368BE0+56/+60` is a
different queue from the plugin's CP PM4 ring RPTR/WPTR. Writing guest worker
producer `+56` does not itself notify `ring_changed_`. Thus the callback can
enqueue one guest worker record, return, let the Native GPU ring finish its
available PM4 batch, and leave `RingWorkerLoop` sleeping while the guest
worker consumer has not advanced. That state is permitted by the current
implementation and is not, by itself, evidence that the callback was lost or
that the dispatch-ID getter caused the sleep.

The supplied v54 stop snapshot does not include the final CP RPTR/WPTR pair,
the guest consumer thread's wait state, or the wake-source history. It cannot
establish why the guest worker did not consume the record, whether another
PM4 write pointer update was expected, or whether callback overlap affected
the guest queue. No queue/callback serialization or wait change is justified
from this snapshot.

## Minimal next capture fields

To distinguish an ordinary empty GPU ring from a lost wake or guest worker
stall, retain at the same bounded stop:

1. GPU ring generation, RPTR/WPTR, and last completion record.
2. Guest queue producer `+56`, consumer `+60`, slot pointer `+76`, and the
   consumer thread's PC plus wait/runnable state.
3. Every subsequent CP_RB_WPTR update and `ring_changed_` wake after dispatch
   `0xEE5`.
4. Dispatch IDs at producer/consumer watchpoints; the getter is safe to use
   for this correlation, subject to debugger scheduling perturbation above.

The source-0/source-1 overlap question remains separate. The v54 record joins
one source-1 store but does not test a serialized callback A/B or identify a
source-0 write to the watched fields.
