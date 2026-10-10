# Process 1B — HDVehicle+0x4330 non-thread callback tranche 2

This tranche resolves three of the four callsites left after tranche 1.

- `SetWaitableTimer` at `0x0099882b`: the pinned source initializes the completion-routine value to null before registration.
- `SetWaitableTimer` at `0x00998e13`: the pinned source explicitly sets `pfnCompletionRoutine = 0`.
- `WSARecv` at `0x005fdd21`: the final completion-routine argument is literal `0`.

The sole remaining non-thread callback site is `WSARecvFrom` at `0x005fdd09`. The current decompiler export shows only eight arguments for an API whose completion-routine position cannot therefore be trusted from that source alone, so this site remains fail-closed.

No global gate changes here: runtime callback registration, indirect entry, global runtime-derived `HDVehicle+0x4330` alias closure, the manager `+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf`, P1.3, and provider removal remain incomplete. Provider count stays 7.
