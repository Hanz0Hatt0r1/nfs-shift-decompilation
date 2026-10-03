# Process 1 — outer-update scheduling gate frontier

The persistent native physics path already executes the statically proven
`FUN_00770e80` two-half-step schedule, but Process 2 still has to invoke that
outer boundary explicitly because retail cadence ownership is not proven.

The existing static path above it is:

```text
FUN_00715380
  -> FUN_00713050
      -> FUN_00794a30
          -> FUN_00770e80
```

`SHIFT.OuterUpdateCallsiteStatic/1` also proves two facts that can be joined more
narrowly:

1. `FUN_00713050` contains exactly three source-visible calls to
   `FUN_00794a30`, corroborated by three direct Ghidra callgraph edges;
2. `FUN_00794a30` reaches `FUN_00770e80` only through a source gate containing
   `param_5 != 0` and `caller +0x234 == 0`.

This block answers only the first scheduling question that follows from those
facts:

```text
which FUN_00713050 source call(s) can satisfy the explicit param_5 gate?
```

Tool:

```text
tools/ghidra/build_outer_update_scheduling_gate.py
```

Output:

```text
SHIFT.OuterUpdateSchedulingGate/1
```

No original-game execution and no new runtime capture are used.

## Inputs

Generate the existing source/callgraph contract first:

```bash
python3 tools/ghidra/build_outer_update_callsite_contract.py \
  /path/to/SHIFT.exe.c \
  out/shift_ghidra_database \
  --json-out out/outer_update_callsite_static.json
```

Then build the scheduling-gate frontier:

```bash
python3 tools/ghidra/build_outer_update_scheduling_gate.py \
  /path/to/SHIFT.exe.c \
  out/outer_update_callsite_static.json \
  --json-out out/outer_update_scheduling_gate.json
```

The recovered source is pinned by SHA-256. The input callsite contract must also
still prove:

```text
outer update        0x00770e80
first caller        0x00794a30
upstream batch      0x00713050
upstream owner      0x00715380
```

and must retain the exact source gate:

```text
param_5 != 0
caller +0x234 == 0
```

The three direct `FUN_00713050 -> FUN_00794a30` Ghidra edges must remain direct,
unique, and present.

## Source gate result

For every `FUN_00794a30(...)` call in the pinned `FUN_00713050` source body, the
builder parses the sixth argument without renaming it semantically.

The current source yields:

```text
source ordinal 0 -> param_5 = 0
source ordinal 1 -> param_5 = 0
source ordinal 2 -> param_5 = 1
```

Therefore the report can promote this narrow fact to `proven`:

```text
exactly one source-visible FUN_00794a30 call has a non-zero param_5 constant
```

The first two source calls are statically blocked by the explicit
`param_5 != 0` predicate. The third source call is only **param_5-gate eligible**.
It is not a guaranteed outer update because `FUN_00794a30` still requires:

```text
caller +0x234 == 0
```

The report deliberately uses `param5-gate-eligible` rather than naming the
argument as a timestep mode, fixed-step flag, render flag, or physics-enable
flag.

## Why this is not yet a machine-callsite identity

The Ghidra callgraph independently contains three direct machine call
instructions from `FUN_00713050` to `FUN_00794a30`.

The frontier records those finite machine candidates, but it does **not** zip
source lexical order to ascending instruction address. Decompiled source order
is not accepted as an independent proof that source ordinal 2 corresponds to one
specific CALL instruction.

Accordingly:

```text
source_to_machine_callsite_mapping_state = unknown
source_to_machine_callsite_mapping_proven = false
```

The next targeted instruction pass should reopen only `FUN_00713050` and prove
the constant sixth argument at each exact machine CALL site before selecting one
machine instruction as the unique gate-eligible callsite.

## Why this is not cadence proof

Even a uniquely identified gate-eligible machine call would still not establish
how frequently the statement executes.

The current frontier does not prove:

```text
one FUN_00713050 invocation == one physics tick
one FUN_00713050 invocation == one rendered frame
one gate-eligible statement executes exactly once per invocation
FUN_00715380 is the cadence owner
FUN_0070fe90()+0x388 is a named physics-frequency field
1.0 / rate_source is a final named fixed timestep
```

The already recovered source-visible accumulator and reciprocal expressions are
useful discovery evidence, but their physical semantics and enclosing dynamic
control-flow multiplicity remain separate proof obligations.

The report therefore keeps:

```text
outer_update_dynamic_call_count_state = unknown
cadence_owner_state = unknown
fixed_step_cadence_owner_proven = false
rendered_frame_cadence_proven = false
```

## Remaining blockers

When the current `0, 0, 1` source gate is recovered exactly, the remaining
frontier is:

```text
source_call_to_machine_callsite_identity_not_proven
gate_eligible_statement_dynamic_execution_count_not_proven
FUN_00713050_invocation_cadence_owner_not_proven
FUN_0079b2d0_dispatch_owner_not_proven
rendered_frame_relation_not_proven
```

This is smaller than the previous scheduling boundary: two of the three
source-visible `FUN_00713050 -> FUN_00794a30` sites can no longer be candidate
outer-update scheduling sites through the proven `param_5 != 0` gate.

## Handoff to Process 2

This artifact is a negative/selection contract, not permission to introduce a
new native timer.

Process 2 may use it to understand that the current retail static chain has one
source-visible `param_5`-eligible path, but must keep explicit outer execution
until Process 1 additionally proves:

```text
exact machine callsite identity
+ dynamic statement multiplicity
+ upstream invocation cadence owner
```

No rendered-frame/fixed-step equivalence should be introduced from the numeric
`1.0 / rate_source` expression alone.

## Fail-closed behavior

The builder rejects:

- source hash drift;
- source bytes that do not match the callsite contract;
- missing or weakened source/callgraph prerequisites;
- a changed outer-update/first-caller/batch/owner anchor;
- loss of the explicit `param_5 != 0` gate;
- missing, duplicate, indirect, malformed, or retargeted batch callgraph edges;
- source call-count drift;
- malformed nested call arguments.

A non-constant sixth source argument is retained as `unknown`; it is never
converted into an inferred boolean value.
