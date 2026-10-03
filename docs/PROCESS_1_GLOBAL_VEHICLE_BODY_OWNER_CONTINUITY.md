# Process 1 — global vehicle to BODY-array owner continuity

## Playable-slice blocker reduced

PR #1194 / `SHIFT.GlobalVehicleComponentBaseIdentity/1` proves that the normal
outer-update receiver is the global vehicle component base:

```text
FUN_00770e80 receiver = &DAT_00c13700 = 0x00c13700
```

It also proves that the anonymous `*record+0x340` update-child pointer does not
need to be relabelled as that vehicle base.  The remaining BODY-pose identity
frontier is downstream:

```text
DAT_00c13700 / FUN_00770e80
  -> FUN_00765470 receiver
  -> FUN_007b2270 BODY-array owner
```

Process 1 #1188 already proves the retail BMW chassis is SDF BODY index 0.  If
this receiver/owner edge is positive, Process 2 Phase 698/700 can consume the
persistent BODY 0 pose without the obsolete update-child-equality requirement.

No original game execution and no new runtime capture are used.

## Analyzer

```text
tools/ghidra/analyze_global_vehicle_body_owner_continuity.py
```

Output:

```text
SHIFT.GlobalVehicleBodyOwnerContinuity/1
```

The analyzer consumes the existing global-vehicle identity, BMW chassis
identity and BODY-frame contracts plus the pinned retail `SHIFT.exe.c`, raw
Ghidra metadata, and a targeted `SHIFT.GhidraFunctionInstructions/2` export for
`FUN_00765470`.

## First edge is already source-backed

The pinned outer-update source contract contains two calls:

```text
FUN_00765470(this, 0.5, ...)
```

inside `FUN_00770e80`.  The new analyzer independently parses the pinned source
and requires both calls to forward the exact `this` expression.

Together with #1194 this establishes:

```text
0x00c13700 outer receiver
  -> same pointer as FUN_00765470 receiver
```

without using callgraph adjacency as object identity.

## Final edge: exact call 0x0076582a

Process A already freezes:

```text
0x0076582a  FUN_00765470 -> FUN_007b2270
```

and `FUN_007b2270` owns the BODY array through:

```text
owner+0x10  BODY count
owner+0x14  BODY array pointer
stride      0x170
```

The analyzer requires:

1. the raw Ghidra direct edge at exactly `0x0076582a`;
2. `CALL` p-code and a flow to `FUN_007b2270` in the targeted instruction export;
3. `__thiscall` ABI for both `FUN_00765470` and `FUN_007b2270`;
4. the pinned recovered source to call `FUN_007b2270(this, ...)` exactly once;
5. ECX at `0x0076582a` to trace back to `FUN_00765470` entry ECX without pointer arithmetic or memory reload.

## Callee-saved register handling

A simple local reverse trace is too conservative here because the half-step
function executes solver/post-solve calls before `0x0076582a`.  The specialized
trace therefore allows an entry receiver saved in `EBX`, `ESI`, `EDI` or `EBP`
to cross a **direct** call only when the target has a standard supported x86 ABI
(`__thiscall`, `__cdecl`, `__stdcall`, `__fastcall`).

It still fails closed on:

- caller-saved `EAX/ECX/EDX` crossing a call;
- any indirect call;
- unsupported/unknown target ABI;
- branch/control-flow barriers;
- non-copy register redefinitions;
- non-zero pointer arithmetic;
- memory reloads/alias assumptions.

Thus a shape such as:

```text
entry ECX
  -> MOV ESI,ECX
  -> direct calls preserving ESI
  -> MOV ECX,ESI
  -> CALL FUN_007b2270
```

can be proven as exact numeric pointer continuity without promoting any class or
method name.

## Positive handoff

Only when both source and machine receiver joins are verified does the report
emit:

```text
outer_receiver_to_BODY_owner_continuity_proven = true
vehicle_BODY_selection_ready = true
selected_BODY_index = 0
phase698_positive_selection_admissible = true
```

This composes #1194 global vehicle identity with #1188 chassis BODY identity.
It does not require or claim:

```text
*record+0x340 == DAT_00c13700
```

## Preserved blockers

Even a positive BODY-owner result does **not** prove:

- BODY origin/basis -> renderer SVWT/world-matrix convention;
- per-frame mutation of the Process 3 BMW renderer subgroup;
- camera-follow convention;
- automatic deep-physics scheduling from `fixed_step()`;
- the exact semantic `rear_axle` SDF BODY index.

After BODY selection becomes positive, the next cross-process vertical-slice
blocker is the exact BODY pose -> renderer world-transform convention.

## Offline invocation

With the existing static inputs:

```bash
python3 tools/ghidra/analyze_global_vehicle_body_owner_continuity.py \
  /path/to/SHIFT.exe.c \
  out/shift_ghidra_database \
  out/body_owner_instructions.jsonl \
  out/global_vehicle_component_base_identity.json \
  out/bmw_chassis_body_identity_frontier.json \
  out/body_frame_integration_static.json \
  --json-out out/global_vehicle_body_owner_continuity.json
```

The required targeted export is only `FUN_00765470`; no game launch or runtime
capture is needed.

## Current repository limitation

The repository contains the static contracts and Ghidra analyzer infrastructure,
but not the real targeted `SHIFT.GhidraFunctionInstructions/2` row for
`FUN_00765470`.  Therefore this change prepares and regression-tests the exact
proof without preclaiming the retail result.  Once that one offline instruction
row is available, the analyzer either closes the BODY-selection gate or emits
the exact register/clobber reason that keeps it closed.
