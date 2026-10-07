# Process 1 — Controller #1 message queue does not establish a worker wake

This slice continues from:

```text
SHIFT.Process1Controller1AlertablePacing/1
SHIFT.Process1Controller1RetailCadenceJoin/1
```

and asks a narrower question: when another path enqueues a Controller #1
message, is that enqueue statically proven to wake the worker out of its
`SleepEx(10, TRUE)` pacing boundary?

The answer is **no** for the recovered message-queue path. This does not prove
that the worker can never return early from its alertable sleep; APC-capable
paths remain a separate blocker.

## 1. Controller thread queue can be created with or without an Event

`FUN_00649b10` selects the queue mode before calling `FUN_0064ff40`:

```text
controller+0x50 == 0 -> mode 1
controller+0x50 != 0 -> mode 3
```

`FUN_0064ff40` maps those modes into queue flags. Mode 3 sets queue bit `0x8`
and creates the named `MsgQueue Event` through `FUN_0064f570`; mode 1 does not.

This slice does not promote which mode Controller #1 uses in the selected retail
session. That byte's exact selected-session producer remains outside the proof.

## 2. Enqueue may call SetEvent

`FUN_00662ee0` reaches the generic queue insertion `FUN_00650350`.

After inserting the message, `FUN_00650350` tests queue bit `0x8`. When that bit
is enabled it calls `FUN_0064f530`, a thin `SetEvent` wrapper.

So the following is proven:

```text
Controller enqueue
  -> queue insertion
  -> if queue event bit 0x8 is set
     -> SetEvent(MsgQueue Event)
```

The existence of this signal is not the same as a Controller #1 worker wake.

## 3. Controller #1 worker polls the queue instead of waiting on its Event

The worker `FUN_00662880` repeatedly drains messages through:

```text
FUN_006550a0
  -> FUN_006500e0
```

`FUN_006500e0` removes a queued item, optionally under the queue lock. It does
not wait on the queue Event.

There is a separate generic helper `FUN_0064f540` that wraps
`WaitForSingleObjectEx` for queue/event-style objects, but the recovered
Controller #1 worker loop does not call it.

The PC retail worker order is:

```text
drain queued messages
  -> manager dispatch
  -> SleepEx(10, TRUE)
  -> stop-byte recheck
  -> loop
```

Therefore even when an enqueue path reaches `SetEvent`, the recovered worker
does not wait on that event. The static queue path consequently does not prove
that a message arrival interrupts the current `SleepEx(10, TRUE)` call.

This is deliberately phrased as a proof boundary: it does not claim that no
other mechanism can cause an early alertable return.

## 4. APC-capable APIs exist elsewhere, but ownership is not joined

The PC binary/source contains asynchronous file I/O using:

```text
ReadFileEx(..., lpCompletionRoutine_006553e0)
WriteFileEx(..., lpCompletionRoutine_00655410)
```

Those APIs can participate in alertable-completion mechanisms on the thread
that initiated the operation. However, this slice finds no source-backed join
showing that Controller #1 initiates those operations or owns those completion
callbacks.

The source does not contain a `QueueUserAPC` token, but that absence is not used
to prove that APC delivery is globally impossible. It is only a negative search
observation.

The source also contains FMOD waitable-timer setup. The inspected
`SetWaitableTimer` calls use a null completion routine and therefore do not
supply a recovered Controller #1 APC callback path.

Accordingly, the current evidence **does not prove an APC path** into Controller
#1, and it also does not prove that no such indirect path exists.

## 5. No render/presentation phase-lock is promoted

No recovered render/presentation callgraph is joined to:

- `FUN_00662ee0` Controller message enqueue;
- the Controller #1 queue Event;
- an APC producer owned by Controller #1;
- an alertable completion callback running on Controller #1.

Thus the current supported timing model remains:

```text
Controller #1 message queue: polled
Controller #1 pacing:        SleepEx(10, TRUE)
Physics Manager cadence:     existing RetailEvidence contract
render/presentation:         not joined
```

A queue `SetEvent` must not be promoted into a frame-triggered worker wake merely
because the worker's `SleepEx` is alertable.

## Machine-locked PC spans

The evidence pins:

- queue mode selection in `FUN_00649b10`;
- queue flag/event creation in `FUN_0064ff40`;
- generic dequeue `FUN_006500e0`;
- generic enqueue plus conditional `SetEvent` in `FUN_00650350`;
- Controller enqueue wrapper `FUN_00662ee0`;
- the worker queue-drain → manager-dispatch → `SleepEx` sequence.

See `evidence/process1_controller1_message_queue_wake.json` for the exact
addresses and SHA-256 values.

## Next Process 1 blocker

Trace ownership of the alertable APC-capable paths, especially the
`ReadFileEx`/`WriteFileEx` completion operations, and determine whether
Controller #1 can initiate or receive any of them. In parallel, search the
render/presentation callgraph for a concrete producer reaching either the
Controller #1 message queue or an owned APC path.

Until one of those joins is proven, neither message enqueue nor rendering is a
source-backed wake/phase-lock mechanism for Controller #1.
