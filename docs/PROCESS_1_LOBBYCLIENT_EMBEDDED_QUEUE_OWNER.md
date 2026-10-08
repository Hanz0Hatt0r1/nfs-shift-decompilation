# Process 1: LobbyClient embedded queue owner

This slice closes the last unresolved direct caller of the thin generic queue wrapper `FUN_006503d0` without broadening the Controller #1 wake claim.

## PC retail proof

The authoritative inputs are the exact PC retail 1.02 `SHIFT.exe` and matching full Ghidra `SHIFT.exe.c` export.

The Lobby/online constructor chain is source-visible and machine-locked:

1. `FUN_005aa390` enters the derived constructor and reaches `FUN_0047f69c`.
2. PC machine code at `0x0047f69c` stores vptr `0x00ad96d8` into the same `ESI` object, then tail-jumps to `0x005aa3a9`.
3. That constructor tail identifies the object as `Plasma_Online` and initializes `ESI+0x2180` as `LobbyClient Output Message Queue`.
4. The exact retail vtable entry at `0x00ad96d8 + 0x2a0 = 0x00ad9978` is `0x005a8b90`.
5. `FUN_005a8b90` therefore executes with that same derived object as `this`. Its fail branch computes `this+0x2180`, loads message id `4`, and directly calls `FUN_006503d0`.

The previous Process 1 slice already joined the other two source-visible direct callers of `FUN_006503d0` (`FUN_0057e1c0` and `FUN_0057e2a0`) to the same LobbyClient queue through the separately proven `+0x88` queue accessor. With this derived-vtable join, all three direct callers are now bound to LobbyClient queue objects and cannot be the recovered Controller #1 queue.

## What changed

`FUN_006503d0` is removed from the remaining Controller #1 generic queue-pointer frontier for its complete source-visible direct-call surface.

The remaining generic queue-owner questions are:

- `FUN_006333f0`;
- `FUN_006880c0`.

## Fail-closed boundary

This proof does **not** establish that every possible indirect call to the underlying generic enqueue primitive belongs to LobbyClient. It does not rule out dynamically populated or native APC injection and does not prove render/presentation phase locking. It also does not equate the LobbyClient queue with Controller #1 merely because both use the same generic queue implementation.

Xbox 360 recomp files were available on Drive and inspected as a navigation aid, but they are not required for any promoted claim here; all positive claims are PC-backed.
