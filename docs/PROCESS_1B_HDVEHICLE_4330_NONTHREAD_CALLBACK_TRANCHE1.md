# Process 1B — HDVehicle+0x4330 non-thread callback tranche 1

This tranche resolves 7 of the 11 callsites pinned by `SHIFT.P1B.HDVehicle4330NonThreadCallbackFrontier/1`.

- `RegisterClassExW` at `0x00634b89`, `0x00634c52`, `0x00634c93`: both `WNDCLASSEXW` records are explicitly populated with `FUN_00634870` as `lpfnWndProc` before registration.
- `ReadFileEx` at `0x006558d5`, `0x00655c15`: both pass `lpCompletionRoutine_006553e0`.
- `WriteFileEx` at `0x006559df`, `0x00655dca`: both pass `lpCompletionRoutine_00655410`.

The resolved callback entrypoints are `0x00634870`, `0x006553e0`, and `0x00655410`; none belongs to the 15-function exact `HDVehicle+0x4330` carrier set.

This closes only these seven registration sites. The two `SetWaitableTimer` sites and the `WSARecv`/`WSARecvFrom` completion-parameter sites remain open. Runtime callback registration, indirect entry, the manager `+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf` adjudication, P1.3, and provider removal remain fail-closed. Provider count remains 7.
