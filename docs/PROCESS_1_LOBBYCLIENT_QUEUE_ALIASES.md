# Process 1 — LobbyClient generic queue aliases

This slice narrows the remaining `FUN_00650350` generic queue-pointer frontier by proving two previously ambiguous producers belong to the **Plasma_Online / LobbyClient** object, not Controller #1. Authority is the exact PC retail 1.02 `SHIFT.exe` plus its matching full Ghidra `SHIFT.exe.c` export. Xbox 360 recompilation was available but is not required for any promoted claim.

## LobbyClient queue identity

`FUN_0057d9b0` lazily constructs the singleton at `DAT_00be4800` through `FUN_005aa390`. The constructor chain installs vtable `0x00ae3b00`; the source-visible constructor continuation names the owner `Plasma_Online` and initializes `this+0x2180` as `LobbyClient Output Message Queue`.

The PC vtable entry at `0x00ae3b00 + 0x88` points to `0x005aa4e0`. That seven-byte machine function is exactly `lea eax,[ecx+0x2180]; ret`. The queue destructor likewise destroys `this+0x2180`. This joins virtual slot `+0x88` to the embedded LobbyClient output queue by machine identity rather than naming inference.

## Resolved generic enqueue callers

`FUN_0057e5b0` and `FUN_0057e820` both ensure `DAT_00be4800` is initialized, call virtual slot `+0x88`, then pass the returned queue pointer to `FUN_00650350`. Because the slot is machine-proven to return `this+0x2180`, both direct callers target the LobbyClient output queue and cannot be the recovered Controller #1 queue (`Controller+0x08` / `ThreadState+0x5c`).

The thin wrapper `FUN_006503d0` has three source-visible direct callers. Two (`FUN_0057e1c0`, `FUN_0057e2a0`) also obtain their queue through the same LobbyClient `+0x88` accessor. The third (`FUN_005a8b90`) passes `this+0x2180` directly, but this slice does not promote its exact owner type; therefore `FUN_006503d0` remains fail-closed in the Controller #1 alias frontier.

## Fail-closed boundary

This is an object-identity narrowing, not a claim that Controller #1 has no asynchronous wake source. The following remain unresolved:

- exact queue ownership for `FUN_006333f0`;
- exact owner of the remaining `FUN_006503d0` call from `FUN_005a8b90`;
- exact queue ownership for `FUN_006880c0`;
- indirect/native APC injection;
- render/presentation phase locking to Controller #1 or Physics Manager cadence.

The next Process 1 slice should classify those three remaining generic queue-pointer surfaces by exact object identity, prioritizing any path reachable from render/presentation code.
