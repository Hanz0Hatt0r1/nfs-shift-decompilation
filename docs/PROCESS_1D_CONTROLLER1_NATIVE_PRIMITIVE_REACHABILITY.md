# Process 1D — Controller #1 native primitive reachability join

## Purpose

PR #1699 turns manual-export-walk and direct-native transition mechanisms into a finite candidate frontier, but that frontier is not yet joined to the recovered Controller #1 worker.

This tool performs that join using the current direct internal callgraph:

```text
Controller #1 worker FUN_00662880
  -> direct-call graph
  -> #1699 primitive candidate function
```

It consumes `SHIFT.P1D.Controller1NativeApcPrimitiveFrontier/1` plus the Drive-backed Ghidra SQLite callgraph and emits `SHIFT.P1D.Controller1NativePrimitiveReachability/1`.

## What it records

For each primitive candidate it preserves:

- PEB/export-walk candidate flag;
- direct native transition flag;
- exact PEB/SYSENTER/INT 0x2e sites from the upstream frontier;
- whether the candidate is directly reachable from `FUN_00662880`;
- the shortest recovered direct path when reachable.

Directly unreachable candidates are rejected only from the **direct worker-call surface**. They are not rejected from indirect execution, callbacks, virtual dispatch, generated code, or external/native stubs.

## Reproduction

First produce the #1699 frontier on authoritative PC retail 1.02:

```text
ShiftNativeResolutionPrimitiveExporter.java out/p1d_native_resolution_primitives.jsonl
python3 tools/ghidra/analyze_p1d_controller1_native_apc_primitives.py \
  out/p1d_native_resolution_primitives.jsonl \
  --output out/p1d_native_apc_frontier.json
```

Then join it to Controller #1 reachability:

```text
python3 tools/ghidra/analyze_p1d_controller1_native_primitive_reachability.py \
  out/p1d_native_apc_frontier.json \
  out/shift_ghidra.sqlite \
  --output out/p1d_native_apc_reachability.json
```

## Promotion rule

A reachable candidate is still only navigation evidence. Before changing Controller #1 timing:

1. recover exact local machine flow;
2. identify the resolved API or syscall/service;
3. prove that it is APC-capable in the observed invocation form;
4. prove the target thread/thread handle is Controller #1.

Numeric constants such as PEB/export offsets or syscall transition opcodes are never sufficient on their own.

## Gate

Until authoritative retail primitive output is captured and adjudicated:

```text
tooling ready                         = true
retail primitive frontier captured    = false
retail reachability join captured     = false
manual export walking ruled out       = false
native/syscall APC injection ruled out= false
Controller #1 timing exhaustive       = false
P1.3D complete                        = false
external provider count               = 7
```
