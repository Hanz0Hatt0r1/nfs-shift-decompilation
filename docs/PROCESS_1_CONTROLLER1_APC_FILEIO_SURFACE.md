# Process 1 — Controller #1 APC / async-file surface

This slice narrows the alertable-wake frontier for **Controller #1** using the
PC retail 1.02 executable and the matching full Ghidra C export. Xbox 360
recompilation evidence is not required for the claims below.

## What is proven

The Controller #1 worker and the asynchronous file-I/O implementation are
separate object families.

- Controller #1 is constructed by `FUN_006624a0`, calls base constructor
  `FUN_006551b0`, and installs vtable `0x00af0568`.
- The async-file base is constructed by `FUN_00652260` and installs vtable
  `0x00aef430`.
- The two vtable prefixes are independently byte-locked in
  `evidence/process1_controller1_apc_fileio_surface.json`.

The body of Controller #1 worker `FUN_00662880` contains no direct references
to `ReadFileEx`, `WriteFileEx`, either recovered completion routine, or the
known async-file initiation helpers checked by the analyzer.

The two completion routines are also source-specific:

- `lpCompletionRoutine_006553e0` recovers its owner from `OVERLAPPED+0x10` and
  continues through `FUN_00652710`.
- `lpCompletionRoutine_00655410` recovers the same owner slot and continues
  through `FUN_006529f0`.

That establishes a return to the owning async-file object. It does **not**
establish a direct completion into Controller #1.

## Controller queue direct-call surface

`FUN_00662ee0` is the Controller enqueue wrapper over generic queue function
`FUN_00650350`.

Across the exact PC Ghidra export there is one direct callsite to
`FUN_00662ee0` in addition to its definition. The caller is `FUN_006499e8`, in
a shutdown/teardown enumeration path that enqueues message `0` and then waits
100 ms.

No direct render/presentation -> `FUN_00662ee0` callsite is therefore proven.
This is deliberately a **direct-call** statement only.

## What is not proven

This slice must not be interpreted as proving that Controller #1 can never be
reached by APC-capable work. The following remain open:

- an indirect or aliased owner may reach the async-file initiation surface;
- render/presentation code may reach the generic queue through an alias rather
  than the named `FUN_00662ee0` wrapper;
- Controller #1 queue storage (`+0x5c` frontier) may escape through a pointer
  path not visible as a direct named call;
- the independent `SleepEx(10, TRUE)` pacing and the 30 Hz Physics Manager
  contract still must not be equated with rendered-frame cadence.

## Reproduction

Run the analyzer against the exact retail files:

```text
python tools/ghidra/analyze_process1_controller1_apc_fileio_surface.py \
  --source SHIFT.exe.c \
  --exe SHIFT.exe \
  --output evidence/process1_controller1_apc_fileio_surface.json
```

The analyzer fails closed on both file hashes, recovered source structure,
direct enqueue call count, PE machine spans, and vtable prefixes.

## Next Process 1 blocker

Trace indirect call/alias ownership from Controller #1 manager updates into the
async-file initiators, and search render/presentation producers for aliases of
Controller #1 queue storage. Direct file-APC and direct enqueue paths are now
negative; indirect aliasing is intentionally unresolved.
