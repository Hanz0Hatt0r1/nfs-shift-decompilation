# Process 1 — `Controller #1` wake/message surface frontier

This slice continues from the already-admitted Controller #1 lifecycle/pacing and
retail-cadence join. It asks a narrower question: can ordinary Controller #1
messages wake the alertable worker sleep, and is any render/presentation wake
path already proven?

Authority remains the pinned PC retail 1.02 `SHIFT.exe.c` source. Xbox 360
recompilation is available on Google Drive as a search aid but is not required
for this promotion.

## 1. Controller #1 does not create an event-backed message queue

The shared controller base initializer `FUN_006551b0` clears the byte at object
`+0x50`.

When `FUN_00649b10` creates the worker message queue it selects queue mode `1`
while that byte is zero. `FUN_0064ff40` maps mode `1` to queue state bit `0x4`.
The separate event-backed bit is `0x8`, so the proven Controller #1 initialization
path does not create the queue event.

`FUN_00650350` appends a message and signals the queue event only if state bit
`0x8` is set. Therefore an ordinary enqueue on this proven queue configuration
does not signal an event that wakes Controller #1.

## 2. The Controller #1 worker polls that queue

`FUN_00662880` drains messages with `FUN_006550a0`, runs manager work, then calls:

```text
FUN_00649780(10, 1)
  -> SleepEx(10, TRUE)
```

It does not use the generic queue-event wait helper used by several other worker
classes. This keeps the previously recovered model intact:

```text
poll queue
-> run manager scheduler
-> alertable SleepEx(10, TRUE)
-> repeat
```

Ordinary message submission is therefore a producer for work consumed on a
worker iteration, but is not promoted to a wake signal for the sleep itself.

## 3. Alertable completion remains a separate open surface

The full pinned source has no source-visible `QueueUserAPC` call. That is useful
negative evidence but not enough to prove that the alertable sleep can never
return early.

The same executable contains generic asynchronous file-I/O code using
`ReadFileEx` and `WriteFileEx`, with completion routines
`lpCompletionRoutine_006553e0` and `lpCompletionRoutine_00655410`.

There is no direct `ReadFileEx` or `WriteFileEx` call in `FUN_00662880` itself.
However Process 1 has not yet proved that every deeper Physics Manager call made
on Controller #1 is unable to initiate such asynchronous work on that worker
thread. For that reason this slice explicitly leaves the global alertable
completion surface open.

## 4. Render/presentation phase-locking remains unproven

Nothing in this bounded queue path establishes a render or present producer:

- Controller #1 ordinary messages do not signal its queue event because the
  proven queue is not event-backed;
- the worker polls and then sleeps alertably;
- the existing Physics Manager cadence remains independently governed by the
  admitted 30 Hz / 33 ms manager-local scheduler contract;
- no exact render/present -> APC, async completion, or Controller #1 message
  transfer is promoted here.

Therefore these claims remain false:

```text
Controller #1 queue message == frame wake
worker iteration == rendered frame
Physics Manager dispatch == rendered frame
30 Hz Physics Manager cadence == presentation cadence
```

## Promoted frontier

```text
Controller #1 base init
  -> +0x50 = 0
  -> FUN_00649b10 selects queue mode 1
  -> FUN_0064ff40 produces queue state 0x4, not event bit 0x8
  -> FUN_00650350 enqueue cannot signal the absent queue event
  -> FUN_00662880 polls with FUN_006550a0
  -> manager work
  -> SleepEx(10, TRUE)
```

## Next Process 1 blocker

Two exact producer questions remain:

1. determine whether any `ReadFileEx`/`WriteFileEx` completion-capable path is
   reachable from Controller #1 manager work on the same worker thread;
2. independently trace any render/presentation producer into Controller #1
   message submission or another alertable wake mechanism.

Until one of those paths is proven by exact call/value transfer, the
render/presentation join remains fail-closed.
