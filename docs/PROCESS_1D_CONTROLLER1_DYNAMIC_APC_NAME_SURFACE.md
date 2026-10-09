# Process 1D — Controller #1 dynamic APC name surface

## Blocker

The normal Controller #1 worker loop is already recovered as:

```text
poll queue
-> manager dispatch
-> SleepEx(10, TRUE)
-> repeat
```

Direct/source-visible APC-capable imports are already bounded. The remaining timing ambiguity is indirect/native APC injection into the alertable worker.

## This step

`analyze_p1d_controller1_dynamic_apc_names.py` narrows one specific sub-surface: **plain-name dynamic API resolution**.

It reuses the hash-pinned PC retail import parser and checks two independent ingredients:

- resolver imports such as `GetProcAddress` / `LdrGetProcedureAddress`;
- embedded ASCII or UTF-16LE names for known APC-capable APIs such as `QueueUserAPC`, `NtQueueApcThread`, `NtQueueApcThreadEx`, `ZwQueueApcThread`, `RtlQueueApcWow64Thread`, and `SetWaitableTimerEx`.

Typical use:

```text
python3 tools/ghidra/analyze_p1d_controller1_dynamic_apc_names.py \
  --exe /path/to/SHIFT.exe \
  --output out/p1d_controller1_dynamic_apc_names.json
```

## Evidence boundary

An empty plain-name surface is **not** a universal no-APC proof.

It does not rule out:

- runtime-generated, encrypted or hashed API names;
- manual export-table walking;
- direct native/syscall APC injection;
- function pointers obtained through another subsystem;
- any path whose target thread identity has not been joined to Controller #1.

Conversely, finding an APC API name or resolver does not prove Controller #1 is targeted. Exact callsite and thread-handle provenance are still required.

## Next step

Run the analyzer against authoritative PC retail 1.02. If the plain-name surface is non-empty, trace each resolver/name callsite to its resulting function pointer and target thread identity. In parallel, separately bound manual export walking and native/syscall APC paths. Controller #1 timing remains fail-closed until all such indirect/native injection classes are resolved.
