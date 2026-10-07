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

Xbox recomp is not required for any promoted claim in this slice.

## Scope boundary

This is a bounded negative result, not a proof that APC delivery is globally impossible.

It does **not** adjudicate the separate `ReadFileEx`/`WriteFileEx` completion surface, does not rule out undocumented/native or indirect APC queueing, and does not prove any render/presentation phase lock. Those remain separate Process 1 ownership/reachability questions.

The next Process 1 step is to join the separately recovered async-file APC owner to the remaining indirect manager-dispatch surface above `Controller #1`, now that timer/Winsock completion-routine APCs are excluded.
