# Process 1B — non-thread callback frontier for exact HDVehicle+0x4330 carriers

After thread-start callback closure, the remaining runtime callback-registration surface still includes Win32/Winsock APIs that can receive code pointers independently of ordinary direct callgraph entry.

This contract inventories the finite direct-call subset present in the pinned Ghidra SQLite index:

- `RegisterClassExW`: 3 callsites
- `RegisterClassA`: 0 callsites
- `SetWaitableTimer`: 2 callsites
- `ReadFileEx`: 2 callsites
- `WriteFileEx`: 2 callsites
- `WSARecv`: 1 callsite
- `WSARecvFrom`: 1 callsite

Total: 11 direct callsites. None of the callers is itself one of the 15 exact HDVehicle+0x4330 carrier functions.

This is deliberately a navigation frontier, not a callback-identity conclusion. A non-carrier caller can still pass a carrier address as an argument, so callback argument provenance remains open. The next pass must machine-adjudicate WndProc, file-completion, waitable-timer and Winsock completion parameters at the pinned callsites.

Global gates remain fail-closed: runtime callback registration is not ruled out; indirect entry into exact carriers is not ruled out; the manager+0x374 -> HDVehicle+0x4330 identity join and final `0x004b86cf` rejection remain false; provider count remains 7.
