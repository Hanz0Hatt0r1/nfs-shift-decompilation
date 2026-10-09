# Process 1D — Controller #1 module-literal reachability

## Result

The Drive-backed PC-retail Ghidra SQLite snapshot contains eight exact literal rows for the bounded module-name set:

```text
kernel32
kernel32.dll
ntdll
ntdll.dll
```

Those rows belong to seven functions. Exactly four owners are reachable from the recovered Controller #1 worker `FUN_00662880` through the current direct-call graph:

- `0x0090aa27` — local strings `EncodePointer`, `KERNEL32.DLL`;
- `0x0090aa9e` — local strings `KERNEL32.DLL`, `DecodePointer`;
- `0x0090abb8` — local strings `EncodePointer`, `KERNEL32.DLL`, `DecodePointer`;
- `0x009189cd` — local strings `InitializeCriticalSectionAndSpinCount`, `kernel32.dll`.

All four are already members of the previously bounded direct `GetProcAddress` resolver surface. Therefore literal `KERNEL32`/`NTDLL` module-name ownership adds **zero new direct worker-reachable manual-resolution candidates** beyond that existing resolver subset.

The same indexed string surface contains **zero** `NTDLL` literal rows.

## What this closes

This closes only the direct-callgraph + literal-module-name sub-surface:

```text
Controller #1 worker
  -> direct internal path
  -> function owning literal KERNEL32/NTDLL module name
  -> candidate outside known GetProcAddress surface
```

There are no such new candidates in the current retail SQLite snapshot.

## What remains open

This is not a no-manual-resolution theorem. The following remain open:

- PEB/LDR traversal without literal module names;
- hashed, encrypted, generated, or case-transformed module/API names;
- indirect calls, callbacks, and virtual dispatch outside the direct graph;
- pre-resolved function pointers obtained elsewhere;
- direct native/syscall injection (`SYSENTER`, `INT 0x2e`, native stubs) from the #1699 primitive frontier;
- exact Controller #1 target-thread identity for any positive APC-capable mechanism.

The absence of an `NTDLL` literal is therefore only a narrow negative result.

## Reproduction

```text
python3 tools/ghidra/analyze_p1d_controller1_module_literal_reachability.py \
  out/shift_ghidra.sqlite \
  --output out/p1d_controller1_module_literal_reachability.json
```

The pinned source index is `SHIFT.GhidraSQLiteIndex/1` with SHA-256:

```text
ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
```

## Gate

```text
direct literal module-name surface bounded       = true
new reachable candidate outside GetProcAddress   = false
PEB/hash/manual export walk ruled out             = false
native/syscall APC injection ruled out            = false
Controller #1 timing exhaustive                   = false
P1.3D complete                                    = false
external provider count                           = 7
```

The next P1D step is to adjudicate the native/manual primitive inventory from #1699 with exact local machine flow. Only a proven API/service identity plus Controller #1 target-thread identity can change the timing gate.
