# Process 1 — Controller #1 control timing frontier

## BLOCKER

P1.3 still needs the retail input -> drivetrain/wheel/control producer chain. Controller #1 timing was previously described too broadly, mixing control execution with render/presentation phase locking.

## INPUT

This join reuses existing positive PC-retail contracts only. No new machine/source semantics are introduced. The inputs cover alertable pacing, retail cadence, BManager queue messages, async-file APC ownership, timer/Winsock completion behavior, Controller #1 manager reachability, APC source inventory, queue-object identity, and the remaining generic queue layout exclusion.

## CLOSED SURFACE

The recovered normal Controller #1 execution model is:

```text
poll queue
-> manager dispatch
-> SleepEx(10, TRUE)
-> repeat
```

BManager state messages `3..7` are positively joined to Controller #1. The normal queue initializes with argument `1`, resulting flags `7`, while the message-event bit is `8`; normal enqueue therefore does not interrupt the alertable sleep through the queue event.

Known `ReadFileEx`/`WriteFileEx` operations belong to the separate `Base File: Async Thread`. Recovered waitable-timer and Winsock completion paths do not target Controller #1. Direct named closures of the three attached Controller #1 managers do not reach the known async-file initiators, and the source-visible generic queue-alias frontier is closed.

## REMAINING FRONTIER

One exact timing question remains: indirect/virtual/function-pointer or native APC injection into Controller #1 has not been ruled out. Therefore an exhaustive statement that `SleepEx(10, TRUE)` can never return early is still forbidden.

Render/presentation phase locking remains unproven, but it is not promoted to a prerequisite for proving the input -> drivetrain/wheel/control producer chain. It stays a separate presentation/camera synchronization question.

## GATES_CHANGED

- Controller #1 direct/source-visible control timing surface: **ready**;
- Controller #1 timing exhaustive: **false**;
- P1.3 complete: **false**;
- retail control chain complete: **false**;
- external-provider count: **7**.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Continue the actual input -> drivetrain/wheel/control producer provenance while separately narrowing the sole remaining timing ambiguity: indirect/native APC injection into the alertable Controller #1 worker. Do not block P1.3 provenance work on render-frame phase locking.
