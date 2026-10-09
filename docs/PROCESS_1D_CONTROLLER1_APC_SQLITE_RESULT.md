# Process 1D — Controller #1 APC SQLite result

## Result

The current Google Drive Ghidra acceleration database (`shift_ghidra.sqlite`) is now pinned as concrete P1.3D evidence rather than remaining an unused external artifact.

Database identity:

```text
format   = SHIFT.GhidraSQLiteIndex/1
sha256   = ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
functions= 41538
calls    = 200598
strings  = 53433
```

The callgraph contains **100** direct calls to `GetProcAddress` from **18** unique functions, so dynamic resolution is genuinely present in the retail binary.

However, the indexed string surface contains no exact rows for:

```text
QueueUserAPC
NtQueueApcThread
NtQueueApcThreadEx
ZwQueueApcThread
RtlQueueApcWow64Thread
SetWaitableTimerEx
```

The only queue-like strings owned by a `GetProcAddress` caller are `alSourceUnqueueBuffers` and `alSourceQueueBuffers` in `0x009a7e04`; these are OpenAL source-buffer APIs and are not APC evidence.

## Adjudication

This closes only the **plain embedded-name + GetProcAddress** sub-surface on the available Ghidra SQLite snapshot. It does **not** close hashed/generated API-name resolution, manual export walking, indirect function-pointer injection, or direct native/syscall APC injection.

Therefore:

```text
plain-name APC resolution supported by SQLite = false
Controller #1 timing exhaustive                = false
P1.3D complete                                 = false
provider count                                 = 7
```

## Compatibility

The available Drive index is schema `/1`, while the newer general-purpose query helper expects `/2`. The dedicated P1D analyzer reads `raw_json` records and accepts both `/1` and `/2`, so the current evidence can be reproduced without rebuilding or migrating the database.

## Next step

Consume the native/manual primitive inventory introduced by P1D PR #1699. Any positive candidate must prove exact local machine flow and then join to Controller #1 worker/thread identity before any timing gate changes.
