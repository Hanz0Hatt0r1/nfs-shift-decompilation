# Process 1D — Controller #1 GetProcAddress argument-flow frontier

## Result

The Drive Ghidra SQLite index has already reduced the Controller #1 worker-reachable direct `GetProcAddress` surface to six functions and eleven calls. Their locally contained strings look like CRT/UI targets, but contained-string membership is not argument-flow proof.

This stage converts that remaining direct named-resolver question into an instruction-level check.

Pinned functions/callsites:

```text
0x0090748b : 0x009074a0
0x0090aa27 : 0x0090aa7b
0x0090aa9e : 0x0090aaf2
0x0090abb8 : 0x0090abfd, 0x0090ac0d
0x009189cd : 0x00918a26
0x0091c073 : 0x0091c0bc, 0x0091c0d9, 0x0091c0ee, 0x0091c123, 0x0091c13b
```

`tools/ghidra/analyze_p1d_controller1_getproc_argument_flow.py` accepts the targeted `SHIFT.GhidraFunctionInstructions/2` export and the Ghidra SQLite string index. For each pinned callsite it recovers only the bounded x86 stdcall case where the second-nearest pre-call `PUSH` (the `lpProcName` argument) resolves to exactly one indexed literal string address.

Register-computed, stack-built, decoded, hashed, generated or otherwise nonliteral names stay unresolved. This is intentional.

## One-command headless run

```bash
GHIDRA_HOME=/path/to/ghidra \
  ./tools/ghidra/run_p1d_controller1_getproc_argument_flow.sh \
  /path/to/project-dir SHIFT SHIFT.exe \
  /path/to/shift_ghidra.sqlite out/p1d_controller1_getproc
```

The wrapper reuses the existing read-only targeted function exporter, so it does not rerun whole-program analysis.

## Promotion rule

The direct named-resolver sub-surface may close negative only when all eleven pinned calls recover exact literal `lpProcName` values and none is one of:

```text
QueueUserAPC
NtQueueApcThread
NtQueueApcThreadEx
ZwQueueApcThread
RtlQueueApcWow64Thread
SetWaitableTimerEx
```

Even then the following stay open:

```text
indirect resolver calls                  = false / not ruled out
hashed/generated names                   = false / not ruled out
manual export walking                    = false / not ruled out
native/syscall APC injection             = false / not ruled out
Controller #1 timing exhaustive          = false
P1.3D complete                           = false
provider count                           = 7
```

Exact PC-retail machine flow remains semantic authority. Local string context, numeric addresses, or a resolver caller's reachability alone do not promote API identity.
