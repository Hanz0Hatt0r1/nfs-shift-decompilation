# Process 1D — Controller #1 named native call surface

## Result

The Drive-backed PC-retail Ghidra SQLite snapshot contains exactly four direct call records whose recovered target names begin with `Nt`, `Zw`, or `Rtl`.

All four target the same function:

```text
RtlUnwind @ 0x00a62594
```

Callsites:

```text
0x009084f9  caller 0x009084d5
0x00908e37  caller 0x00908e24
0x0091748e  caller 0x0091747e
0x00a6a0e9  caller 0x00a6a0a0
```

None of the four callers is directly reachable from the recovered Controller #1 worker `FUN_00662880` in the current direct-call graph.

The bounded APC-capable native-name set is:

```text
NtQueueApcThread
NtQueueApcThreadEx
ZwQueueApcThread
RtlQueueApcWow64Thread
```

There are zero direct named matches for that set and therefore zero direct worker-reachable named APC targets.

## What this closes

Only this narrow surface closes:

```text
Controller #1 worker
  -> direct internal callgraph
  -> direct named Nt*/Zw*/Rtl* target
  -> APC-capable target name
```

No candidate exists in the current retail SQLite snapshot.

## What remains open

This result does **not** rule out:

- direct `SYSENTER` / `INT 0x2e` or other syscall stubs;
- indirect calls through ntdll/native function pointers;
- generated or copied native stubs;
- wow64 transitions;
- manual, hashed, or generated export resolution;
- callbacks or virtual dispatch outside the direct graph;
- target-thread identity ambiguity.

The #1699 primitive frontier and the reachability join from #1712 remain the correct path for those classes.

## Reproduction

```text
python3 tools/ghidra/analyze_p1d_controller1_named_native_calls.py \
  out/shift_ghidra.sqlite \
  --output out/p1d_controller1_named_native_call_surface.json
```

Pinned source index:

```text
format = SHIFT.GhidraSQLiteIndex/1
sha256 = ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
```

## Gate

```text
direct named native call surface bounded                = true
named APC-capable target present                         = false
direct worker-reachable named APC-capable target present= false
direct syscall surface ruled out                         = false
indirect ntdll pointer surface ruled out                 = false
Controller #1 timing exhaustive                          = false
P1.3D complete                                           = false
external provider count                                  = 7
```
