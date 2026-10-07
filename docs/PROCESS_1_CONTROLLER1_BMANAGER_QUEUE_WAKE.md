# Process 1 — Controller #1 BManager queue wake

This slice classifies a previously ambiguous generic queue producer by **object identity**, not by the shared queue API name. Authority is the pinned PC retail 1.02 `SHIFT.exe` and `SHIFT.exe.c`. The Xbox 360 recomp was not required for this closure.

## Exact Controller #1 queue identity

`Controller #1` is created through `FUN_006339b0 -> FUN_0065b750`. The latter creates the controller in the BManager registry at `BManager+0x4c8`.

Its thread setup allocates the queue stored at `ThreadState+0x5c`; `FUN_00655000` binds that same queue to `Controller+0x08`. `FUN_00655220` dereferences `Controller+0x08` before calling the generic enqueue primitive `FUN_00650350`.

The worker `FUN_00662880` dequeues from that controller queue and explicitly handles message IDs `3`, `4`, `5`, `6`, and `7` before its idle `SleepEx(10, TRUE)`.

## Proven BManager producer

`FUN_0065bd10` redirects to `FUN_0065bd1c`, which iterates the exact `BManager+0x4c8` controller registry. Each registry node contributes its `Controller*` at `node+0x0c`, and the loop calls `FUN_00655220(controller, message)`.

PC state-transition callsites broadcast message IDs `3`, `4`, `5`, `6`, and `7`. Because Controller #1 is created in the same registry, these broadcasts are concrete Controller #1 queue producers. No shared-API-name alias assumption is needed.

## Why this does not explain the alertable wake

The queue path is non-APC and, for Controller #1, the optional message-queue event is not enabled:

1. the base controller constructor initializes the Controller `+0x50` event-enable byte to zero;
2. the recovered Controller #1 startup path does not call `FUN_00654ff0` before thread startup;
3. `FUN_00649b10` therefore passes queue-init argument `1`, not `3`;
4. `FUN_0064ff40` maps argument `1` to final queue flags `7`, so `MsgQueue Event` bit `8` is absent;
5. `FUN_00650350` calls `FUN_0064f530 -> SetEvent` only when bit `8` is set;
6. neither `FUN_00655220` nor `FUN_00650350` contains an APC-injection primitive.

Therefore BManager messages are real Controller #1 work, but this path does not provide a concrete APC source for `SleepEx(10, TRUE)` and does not signal the optional `MsgQueue Event` for the recovered Controller #1 queue configuration.

## Fail-closed boundary

This does **not** prove that Controller #1 can never receive an APC. Indirect/native APC injection remains unresolved. Non-broadcast callers of `FUN_00655220` / `FUN_00650350` also remain to be classified by exact Controller #1 object identity and lifecycle. Render/presentation phase locking remains unproven.

The next Process 1 slice should resolve indirect/native APC injection and classify the remaining non-broadcast queue producers by Controller #1 identity.
