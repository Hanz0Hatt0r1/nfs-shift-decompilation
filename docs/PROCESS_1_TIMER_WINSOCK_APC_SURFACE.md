# Process 1 — timer/Winsock APC completion surface

This slice narrows the alertable-wake frontier for `Controller #1` using the exact PC retail 1.02 `SHIFT.exe` and matching full Ghidra C export from the project Drive.

## Proven negative surface

The retail build contains APC-capable API families beyond `ReadFileEx`/`WriteFileEx`, but their completion-routine arguments are disabled at the recovered callsites:

- `FUN_009983fe` creates the FMOD record waitable timer and calls `SetWaitableTimer` with `pfnCompletionRoutine = NULL`, `lpArgToCompletionRoutine = NULL`, and `fResume = FALSE`;
- `FUN_00998936` does the same for the FMOD WASAPI output timer;
- `FUN_005fdc90` calls `WSARecv` with a null completion routine;
- the sibling `WSARecvFrom` branch shares a zero ninth ABI argument before the call, proving its completion routine is also null despite the decompiler dropping that argument from the rendered prototype;
- `FUN_005ff390` calls `WSAIoctl` with both `lpOverlapped = NULL` and `lpCompletionRoutine = NULL`.

Therefore these source-visible timer and Winsock callsites cannot deliver completion-routine APCs into `Controller #1`'s alertable `SleepEx(10, TRUE)` path.

The two physical `SetWaitableTimer` callsites are machine-verified. The Ghidra C export renders the `FUN_009983fe` callsite twice because of overlapping stack recovery; this document does not treat that duplicate rendering as a third physical callsite.

## Exact evidence

`SHIFT.Process1TimerWinsockApcSurface/1` pins:

- PC EXE MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
- PC EXE SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`;
- `SHIFT.exe.c` SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`;
- exact machine spans for the WSA receive branch, `WSAIoctl`, and both waitable-timer callsites.

### `WSARecvFrom @ 0x005fdd09` ABI reconstruction

The call at `0x005fdd09` reaches the `WS2_32.dll!WSARecvFrom` import through the thunk at `0x0061207c` and IAT slot `0x00aa64e8`. Let `S` be `ESP` after the function prologue and before the call arguments are pushed. The function places a `WSABUF` at `S+0x0c`: `len = 0x4f0` at `0x005fdcd7`, `buf = ESI+0xb0` at `0x005fdcd3`. `ESI` holds the receiver from the entry `EAX`.

| ABI position | Parameter | Exact call value | Push address |
| --- | --- | --- | --- |
| 1 | `s` | `[ESI+0x18]` | `0x005fdd08` |
| 2 | `lpBuffers` | `S+0x0c` | `0x005fdd07` |
| 3 | `dwBufferCount` | `1` | `0x005fdd01` |
| 4 | `lpNumberOfBytesRecvd` | `ESI+0xac` | `0x005fdd00` |
| 5 | `lpFlags` | `ESI+0x94` | `0x005fdcff` |
| 6 | `lpFrom` | `ESI+0x9a` | `0x005fdcfe` |
| 7 | `lpFromlen` | `ESI+0x90` | `0x005fdcf1` |
| 8 | `lpOverlapped` | `ESI+0x54` | `0x005fdce7` |
| 9 | `lpCompletionRoutine` | `NULL` (`EBP=0`) | `0x005fdce1` |

`0x005fdc98` executes `xor ebp,ebp`; no instruction writes `EBP` before `0x005fdce1` executes `push ebp`. The push precedes the branch at `0x005fdce2`, so it belongs to the `WSARecvFrom` path as well as the sibling `WSARecv` path. The call's ninth stack argument is therefore exactly zero. The machine-span hash and individually pinned instruction bytes in the analyzer fail closed on drift.

This completion-routine slot cannot carry a callback into any of the exact `HDVehicle+0x4330` carriers. This conclusion concerns this `WSARecvFrom` callback site only; it does not settle separate indirect calls, APC sources, or the vehicle receiver-identity joins. The external-provider count remains **7**.

Xbox recomp is not required for any promoted claim in this slice.

## Scope boundary

This is a bounded negative result, not a proof that APC delivery is globally impossible.

It does **not** adjudicate the separate `ReadFileEx`/`WriteFileEx` completion surface, does not rule out undocumented/native or indirect APC queueing, and does not prove any render/presentation phase lock. Those remain separate Process 1 ownership/reachability questions.

The next Process 1 step is to join the separately recovered async-file APC owner to the remaining indirect manager-dispatch surface above `Controller #1`, now that timer/Winsock completion-routine APCs are excluded.
