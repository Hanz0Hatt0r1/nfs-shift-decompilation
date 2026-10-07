# Process 1 — Controller #1 APC source inventory

This join consolidates the recovered PC retail 1.02 APC/completion surface around
`Controller #1` without turning an alertable wait into a claim that APC wakeups
actually occur.

## Exact imported completion surface

The pinned `SHIFT.exe` import directory contains the completion/APC-capable API
surface used by the recovered proofs:

- `SetWaitableTimer` at IAT `0x00aa6108`;
- `WriteFileEx` at `0x00aa6234`;
- `ReadFileEx` at `0x00aa6240`;
- `WSARecvFrom` at `0x00aa64e8`;
- `WSARecv` at `0x00aa64ec`;
- `WSAIoctl` at `0x00aa6524`.

The same import table does not contain `QueueUserAPC`, `NtQueueApcThread`,
`ZwQueueApcThread`, `SetWaitableTimerEx`, `WSASend`, or `WSASendTo`.

## Ownership join

Existing Process 1 evidence closes each imported completion surface as follows:

- `ReadFileEx` / `WriteFileEx`: every recovered direct callsite and completion
  routine belongs to `Base File: Async Thread`, a worker distinct from
  `Controller #1`;
- `SetWaitableTimer`: both physical callsites pass a null completion routine and
  null completion argument;
- `WSARecv` / `WSARecvFrom`: completion routines are null;
- `WSAIoctl`: both the overlapped pointer and completion routine are null.

The Controller #1 manager direct-call proof independently shows that the three
attached default manager update closures do not directly reach the recovered
ReadFileEx/WriteFileEx initiators.

Therefore no **concrete recovered imported completion source** is currently
joined to Controller #1's `SleepEx(10, TRUE)` alertable wait.

## Fail-closed boundary

This is not a universal no-APC theorem. It does not rule out an indirect target
that is populated dynamically, undocumented/native APC injection, or some
future newly recovered mechanism that does not appear in this pinned import
inventory. It also does not prove render/presentation phase locking.

The next Process 1 blocker is now narrower: resolve indirect/native APC injection
or prove no such source is joined to Controller #1; separately classify generic
queue producers by Controller #1 queue-object identity rather than by the shared
queue API name.
