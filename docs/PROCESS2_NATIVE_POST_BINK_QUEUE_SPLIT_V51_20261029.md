# Process 2 Native post-Bink worker-ring split — v51 assessment

Date: 2026-10-29
Status: GPU-side candidate identified; causal join to the guest worker-ring writes remains unproven.

## Paired capture identity

The supplied v51 comparison used the same retail XEX, host, ReXGlue runtime,
capture runner, and GDB trace script. The Native plugin hash was
`f213f4ca9b679660e18e17b68aa1cc6f64667388c8f0375ecd80b245db13f1c9` and the
resource manifest was `f26a6709fa57fc36e85b75578ac05563bc8aa12f3641faf045f6bc8cef9fc1f6`.
Native reached Bink 281/281 in an 85.316-second no-input capture. The probe did
not write guest memory and GDB exited successfully.

The local Native log is
`/home/pes/work/nfs-shift-p1-counter-eligible-v141-native-v51-20261029/bin/logs/nfs_shift_001.3.log`
(SHA-256 `dd59b824439142409d446a75180638bd67faa7f6ab16ed31544d78afaefbda22`).
The run metadata records GDB output SHA-256
`845e1f8239e4a9a13af766453a2c6c0d1182514fd66984a91e63b0c845657917` and trace
script SHA-256 `ad6f7ae4ceedcb95d0437e8082bd46da5eb1af28dcbe76b31ef9900fa5dda53c`.

## First stable Native PM4 event identity

The first captured source-1 callback that changed the watched guest wait word
is joined to this expanded PM4 packet:

```text
ring generation 1, guest ring 0x09752580
root batch 2, RPTR 25, WPTR 73
source IB 0x095D0120, nesting depth 1
expanded packet ordinal 108, IB byte offset 1304
type-3 opcode 0x54 (PM4_INTERRUPT), dispatch id 0x107
interrupt source 1, CPU 2
guest callback 0x823B37B8, callback data 0xB7365F00
guest callback thread id 3
```

The Native log records the same callback changing guest word `0x1B964004`
from 1 to 0. Use the packet tuple above as the stable cross-run identity;
`dispatch_id=0x107` is useful only inside this particular run because the ID
also counts vblank dispatches.

The first producer observation is `sub_823B90B0` with `r7=1`, `r5=0x097041A0`,
and caller LR `0x823B90B0`. The first eligible completion is
`sub_823B85D0`, token `0xC0000000`, manager `0xB7365F00`, worker ring
`0xB7368BE0`, and ring producer/consumer `4/2`. The first two eligible samples
remain at `4/2`; the third is `4/4`. `worker+76` remains `0xC96FCD80` in all 16
Native samples. These observations identify the first mismatch but do not yet
prove that the producer call and the packet above are the same logical work
item.

## Native GPU-path findings

`RingWorkerLoop()` handles opcode `0x54` by calling `DispatchGuestInterrupt()`
inline as it parses the expanded stream. That function invokes
`ExecuteInterrupt()` synchronously. The path does not wait for a Vulkan fence
before invoking the guest callback.

Captured Vulkan operations are submitted from the guest SWAP path. The Vulkan
renderer associates a completion fence with a submitted frame, but a normal
submit can return with that fence still in flight. The PM4 interrupt path does
not wait for those in-flight frames. This leaves a concrete ordering risk:
source-1 guest completion may run before preceding Native Vulkan work has been
submitted or completed.

In this specific v51 Native log, no `submitted ... indexed draw packets to the
Vulkan presenter` entry appears in any rotated log. Therefore this capture
does not establish that an outstanding Vulkan fence caused the queue split.
It does establish that the plugin dispatched the identified GPU callback
without evidence of a corresponding Vulkan frame submission.

There is a second candidate concurrency risk. Source-1 PM4 interrupts and
source-0 vblank both invoke `0x823B37B8` with CPU 2 and callback data
`0xB7365F00`, from the separate GPU-ring and vblank host workers. No lock
serializes `ExecuteInterrupt()` across those workers. In the local log, the
identified source-1 callback runs at `03:54:57.895`; a source-0 vblank callback
on the other worker changes the same watched guest word at `03:54:57.934`.
The samples show separate callbacks but do not prove that they overlapped or
that either wrote the worker-ring indices.

## Assessment

The strongest GPU-side hypothesis is premature or concurrent guest interrupt
dispatch, rather than PM4 ring pointer decoding: Native dispatches the guest
callback at packet-parse time, without Vulkan-fence ordering, while the same
guest callback is also invoked by a separate vblank worker. Either can affect
the guest completion path. Current evidence does not establish which one
explains the single producer call, repeated eligible completions, or stable
`worker+76`; no renderer fix or guest-state change is justified yet.

The exact writer of worker-ring `+56`, `+60`, and `+76` is also unknown from the
v51 probe: it samples those fields at completion entry but does not record the
instruction/thread that last changed them. This prevents attributing the
producer-ahead state to the GPU callback from current data alone.

## Minimal verification

Run one bounded no-input Native capture with the same XEX/runtime/plugin and:

1. Set `SHIFT_NATIVE_VULKAN_TRACE_RING=1`. Existing Native tracing then records
   PM4 interrupt packet identity, callback dispatch IDs, source-1 callback
   begin/return, and source-0 vblank duration/thread records.
2. Extend the GDB probe with capped write watchpoints on worker-ring
   `0xB7368BE0+56`, `+60`, and `+76`. Record old/new guest-endian values,
   writer PC/LR, host LWP, and timestamp; retain the existing producer and
   eligible-completion arguments and token pointers.
3. Add a diagnostic-only A/B run that serializes CPU-2 callback execution
   across source 0 and source 1, without changing guest memory or counters.
   If the first `+56/+60` split or repeated `worker+76` changes, callback
   concurrency is implicated. If not, keep that hypothesis open.
4. For the fence hypothesis, log the pending captured-operation/draw counts
   and latest submitted/completed Vulkan fence at each source-1 packet. Only
   test a forced fence wait in a capture that actually has a prior Vulkan
   submission; the supplied v51 run has none, so a wait there would be a
   vacuous test.

Keep the result as a diagnostic comparison. Do not alter the guest counter,
worker queue, wait predicates, or callback semantics based on this evidence.

## Limits

This is a read-only code/log assessment; no runtime or guest code changed, and
no tests or paired game run were performed. The packet tuple is a concrete
candidate and the callback ordering risk is verified in source, but neither is
yet a proven cause of the backend-dependent worker-ring behavior.
