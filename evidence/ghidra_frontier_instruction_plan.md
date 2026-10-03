# Ghidra frontier instruction plan

`tools/ghidra/plan_subsystem_frontier_instructions.py` converts the conservative
one-hop subsystem method frontier into a deterministic work queue for the
existing targeted Ghidra instruction exporter.

The output format is `SHIFT.GhidraSubsystemFrontierInstructionPlan/1`.

## Purpose

The frontier can contain several exact method-name candidates which are useful
next reverse-engineering targets but are not yet semantic promotions. Rather
than manually copying their addresses into
`run_shift_function_instructions.sh`, this planner emits both a structured JSON
plan and an optional newline-delimited address file.

## Selection

Only rows satisfying all of these conditions are eligible:

- `frontier_candidate=true`;
- `promoted` is not true;
- the row has a concrete function address and subsystem;
- when subsystem filters are requested, the row belongs to one of them.

Ordering is deterministic:

1. subsystem name;
2. number of distinct established slice functions directly connected to the
   candidate, descending;
3. number of qualifying direct call edges, descending;
4. function address.

This ordering is an operational work queue, **not** a confidence score.

`--max-targets` caps the selected batch. Remaining eligible targets stay counted
as omitted so a later batch can continue without silently losing them.

## Run

Build a default batch of at most 32 functions:

```bash
python3 tools/ghidra/plan_subsystem_frontier_instructions.py \
  out/shift_ghidra_database \
  --json-out out/frontier_instruction_plan.json \
  --targets-out out/frontier_instruction_targets.txt
```

Limit the plan to physics and take the first 16 targets:

```bash
python3 tools/ghidra/plan_subsystem_frontier_instructions.py \
  out/shift_ghidra_database \
  --subsystem physics \
  --max-targets 16 \
  --json-out out/physics_frontier_instruction_plan.json \
  --targets-out out/physics_frontier_instruction_targets.txt
```

The emitted addresses are directly accepted by
`tools/ghidra/run_shift_function_instructions.sh`.

## Evidence boundary

Planning or exporting a function does not promote it into a subsystem. The plan
keeps `promoted=false` and does not claim:

- complete method behavior;
- argument or return-value semantics;
- calling-convention correctness beyond already recorded Ghidra metadata;
- class ownership or lifetime roles;
- virtual-slot identity.

Instruction-level evidence produced from the plan must still be interpreted and
cross-checked before any semantic promotion.
