# Process 1 — outer-update machine gate frontier

`SHIFT.OuterUpdateSchedulingGate/1` narrows the source-visible scheduling path to
one `FUN_00713050 -> FUN_00794a30` call whose sixth source argument is non-zero.
It intentionally does not equate source lexical order with the three exact Ghidra
CALL addresses:

```text
0x00713112
0x00713135
0x007131b5
```

The next blocker is therefore machine-local:

```text
three exact CALL sites
→ recover the explicit stack argument setup at each site
→ identify the unique non-zero machine argument site
→ keep source param_5 semantics separate until independently proven in callee code
```

Tool:

```text
tools/ghidra/analyze_outer_update_machine_gate.py
```

Output:

```text
SHIFT.OuterUpdateMachineGate/1
```

No original game execution or new runtime capture is used.

## Targeted instruction input

Use the existing read-only instruction exporter; no new Ghidra exporter is
introduced:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/outer_update_machine_gate_instructions.jsonl \
  0x00713050 \
  0x00794a30
```

Then run:

```bash
python3 tools/ghidra/analyze_outer_update_machine_gate.py \
  out/outer_update_scheduling_gate.json \
  out/outer_update_machine_gate_instructions.jsonl \
  --json-out out/outer_update_machine_gate.json
```

`FUN_00794a30` is included in the targeted export only to freeze its current
Ghidra calling-convention annotation at the same evidence boundary. The analyzer
does not use function names or source order to select one of the three machine
CALL instructions.

## Supported machine shape

The current Ghidra metadata identifies `FUN_00794a30` as `__thiscall`. The
recovered source has five explicit arguments after the receiver. The analyzer
supports only the conservative x86 PUSH-form setup:

```text
PUSH explicit_arg_5
PUSH explicit_arg_4
PUSH explicit_arg_3
PUSH explicit_arg_2
PUSH explicit_arg_1
... receiver preparation that does not alter ESP ...
CALL FUN_00794a30
```

Walking backwards from the CALL therefore records:

```text
rank 1 from CALL -> first explicit stack argument
...
rank 5 from CALL -> fifth explicit stack argument
```

The rank-5 entry-storage candidate is recorded neutrally as:

```text
Stack[0x14]:4
```

The analyzer does **not** silently accept other compiler shapes. It stops when
five PUSHes cannot be recovered before any of:

- another direct or indirect CALL;
- branch/return p-code;
- explicit ESP write;
- implicit ESP clobber;
- a write through `[ESP + ...]` that can alter the relationship between earlier
  PUSHes and callee entry storage.

A register or symbolic rank-5 PUSH operand is retained as unknown rather than
constant-folded by naming or source similarity.

## Exact CALL validation

The instruction export is re-indexed independently. The analyzer requires that
its complete set of p-code-confirmed direct calls from `FUN_00713050` to
`FUN_00794a30` exactly equals the scheduling frontier's three candidate
addresses.

Each CALL must have:

```text
flows -> 0x00794a30
p-code contains CALL
```

A missing, extra, indirect, duplicated, or moved site aborts the join.

## Value-profile join, not ordinal join

The source frontier currently proves the source gate-value profile:

```text
0, 0, 1
```

The machine analyzer compares the **multiset** of recovered rank-5 immediate
values with that source profile. It never pairs source ordinal 0 with the lowest
machine address, source ordinal 1 with the next address, and so on.

The regression deliberately uses this synthetic machine profile:

```text
0x00713112 -> 0
0x00713135 -> 1
0x007131b5 -> 0
```

while the source profile remains `0,0,1`. The expected result selects
`0x00713135` as the unique non-zero machine CALL, proving that address selection
comes from the unique value profile rather than order.

When all three machine rank-5 values are exact immediates and their profile
matches source, the report can state:

```text
unique_nonzero_machine_callsite_state = verified
```

This means only:

```text
one exact machine CALL has the unique non-zero fifth explicit stack value
```

It does not yet mean that the machine value has independently proven source
`param_5` semantics.

## Why semantic param_5 mapping stays inferred

Two evidence layers currently nominate the rank-5 stack value as source
`param_5`:

1. recovered source has five explicit parameters after the receiver;
2. Ghidra identifies the target as `__thiscall`.

That is enough for a useful ABI join, but Process 1 already treats calling-
convention metadata as an ABI hint rather than pointer/value semantic proof.
Accordingly:

```text
source_unique_nonzero_to_machine_callsite_join_state = inferred
semantic_param5_machine_mapping_state = inferred
source_param5_to_stack_slot_semantics_proven = false
```

The next promotion must reopen `FUN_00794a30` and prove in machine/p-code that
the value tested by the gate leading to the exact `FUN_00770e80` CALL derives
from the same entry stack storage candidate.

That next blocker is published as:

```text
callee_gate_entry_storage_to_tested_value_not_machine_proven
```

## Cadence remains separate

Even after an exact non-zero machine CALL is selected, the following are still
unknown:

```text
how many times that machine statement executes per FUN_00713050 invocation
how often FUN_00713050 is invoked
whether its enclosing owner is a fixed-physics-step owner
relation to rendered frames
owner/dispatcher of the alternate FUN_0079b2d0 path
```

Therefore the contract preserves:

```text
dynamic_execution_count_state = unknown
cadence_owner_state = unknown
fixed_step_cadence_owner_proven = false
rendered_frame_cadence_proven = false
```

The source-visible accumulator, rate source, and reciprocal expression remain
useful scheduling evidence, but are not promoted to time units or a fixed-step
API without the remaining ownership proof.

## Process 2 handoff

A positive machine-value profile narrows Process 2's scheduling boundary to one
exact retail CALL candidate while preserving the evidence distinction:

```text
source gate selection        proven upstream
machine CALL value profile   verified here
source param_5 machine ABI   inferred
callee gate value provenance blocked
runtime multiplicity         blocked
cadence owner                blocked
```

Process 2 should therefore continue using the explicit outer-update boundary; it
must not automatically wire `NativeRuntimeState::fixed_step()` from this artifact
alone.

## Tests

`tests/test_ghidra_outer_update_machine_gate.py` covers:

- exact direct CALL-set validation;
- unique value-profile selection without source/machine order pairing;
- non-immediate rank-5 values;
- stack-memory overwrite barriers;
- intervening CALL barriers;
- target calling-convention drift;
- machine candidate address drift;
- rejection of an upstream preclaimed source-to-machine identity.
