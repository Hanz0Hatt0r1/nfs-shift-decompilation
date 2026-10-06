# Process 1 — scheduler accumulator value provenance

This S5 layer answers the next exact question left by
`SHIFT.SchedulerAccumulatorProducerFrontier/1` without expanding the targeted
Ghidra slice.

The first playable Linux vertical slice needs continuous persistent physics, but
retail cadence cannot be admitted while the scheduler-side accumulator is only a
field-access shape.  The immediate blocker is narrower:

```text
FUN_00715380 explicit float param_1 (Stack[0x4]:4)
                 |
                 ?
                 v
          this + 0x348 STORE
                 |
                 v
FUN_00713050 this + 0x348 reads
```

The analyzer is:

```text
tools/ghidra/analyze_s5_scheduler_accumulator_value_provenance.py
```

Output format:

```text
SHIFT.SchedulerAccumulatorValueProvenance/1
```

## Inputs

The analyzer consumes:

1. the same exact `SHIFT.GhidraFunctionInstructions/2` export already used by
   `analyze_s5_scheduler_accumulator_slice.py`;
2. the positive `SHIFT.SchedulerAccumulatorProducerFrontier/1` report from that
   first-stage analyzer.

The instruction export remains exactly three functions:

```text
FUN_007155e9
FUN_00715380
FUN_00713050
```

No runtime capture or original-game execution is introduced.

## Positive proof condition

The parent frontier must still prove:

- `FUN_00715380` is `__thiscall`;
- its explicit float parameter is physically `Stack[0x4]:4`;
- there is exactly one proven `this+0x348` writer surface in
  `FUN_00715380`;
- the parent report has not already promoted the value-provenance claim;
- retail cadence is still closed.

For the unique writer instruction, this layer then requires one structured
p-code `STORE` and builds a backward dependency slice for the STORE value using
the repository's existing structured-p-code helpers.

A positive parameter dependency requires a dependency-node `LOAD` whose address
can be reduced conservatively to:

```text
entry ESP + 4
```

with a 4-byte load width and RAM address space.  Simple frame setup is handled
symbolically, so a conventional sequence such as:

```text
PUSH EBP
MOV  EBP, ESP
...
LOAD [EBP + 8]
```

reduces to entry `ESP+4` after accounting for the pushed frame pointer.

`COPY`, integer pointer arithmetic and explicit float conversion operations may
remain in the dependency DAG.  They are recorded rather than assigned source
semantics.

## Fail-closed barriers

A matching stack-slot load is not enough if the local provenance segment crosses
an unresolved control boundary.  The proof stays closed on CALL/CALLIND,
branch/conditional-branch/indirect-branch, return or equivalent textual control
barriers between the definitions needed to establish the stack address and the
writer STORE.

The regression tests also reject:

- a neighboring but wrong stack slot;
- a nearby parameter load that does not actually feed the STORE value;
- a constant STORE value;
- a stale parent report that preclaims the result.

## What becomes proven

A positive report may set:

```text
stored_value_depends_on_FUN_00715380_param1_proven = true
FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven = true
```

This means the machine value written to the verified accumulator field has a
structured local data dependency on the function's explicit float parameter.

It deliberately does **not** mean:

```text
stored_value == param_1
param_1 == elapsed seconds
+0x348 has seconds as physical units
FUN_007155e9's pushed value producer is known
one invocation == one rendered frame
retail cadence is ready for native substitution
```

Those remain separate joins.

## Next exact blocker

After a positive local dependency proof, the next static question is only:

```text
FUN_007155e9
  exact PUSH feeding call 0x00715602
      <- what local machine producer?
```

That pushed-value producer must then be joined to the already-proven
BManager/Physics Manager scheduler path.  Physical time units and dynamic
multiplicity remain closed until independently proven.

## Run

The existing targeted runner now emits both stages from one instruction export:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_s5_scheduler_accumulator_slice.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/s5_scheduler_accumulator
```

Outputs:

```text
s5_scheduler_accumulator_instructions.jsonl
s5_scheduler_accumulator_frontier.json
s5_scheduler_accumulator_value_provenance.json
```

This remains static proof infrastructure only.  It does not execute the original
game and does not use the D3D9 runtime capture.
