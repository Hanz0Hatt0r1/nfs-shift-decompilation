# Ghidra construction / vtable frontier

`tools/ghidra/build_construction_frontier.py` joins the existing heuristic
vtable/function-xref evidence to already proven subsystem callgraph slices. The
output format is `SHIFT.GhidraConstructionFrontier/1`.

This is a target-selection layer for PhysicsParticipant / vehicle construction
work. It deliberately does **not** rename any function as a constructor or
destructor and does not promote a heuristic table into a proven class vtable.

## Inputs and trust levels

The tool combines:

- proven subsystem slices from `SHIFT.GhidraSubsystemManifestIndex/1`;
- direct non-indirect edges from `callgraph.jsonl`;
- `SHIFT.GhidraVtableCandidates/1`, whose top-level status must remain
  `heuristic-candidates`;
- `constructors.jsonl`, whose rows must remain `vtable-xref-candidate`;
- `functions.jsonl` for exact function metadata.

It also cross-checks the two heuristic files: every
`constructors.jsonl` function -> table relation must be present in the matching
`vtables.json` `function_xrefs` list. A mismatch fails closed.

## Frontier admission

A vtable-xref function is admitted for targeted review when at least one of the
following static relationships exists:

1. it lies within the configured direct-callgraph depth of a proven selected
   subsystem slice; or
2. one of its referenced heuristic table candidates contains a static slot whose
   target address is itself already in a proven selected subsystem slice.

The default selected subsystems are `physics` and `vehicle`, with a maximum
callgraph depth of two.

The second rule is useful when a construction/lifetime function is not itself a
close callgraph neighbour of the runtime physics path but references a table
whose slots already touch proven physics/vehicle functions. The table remains
heuristic; only the literal slot target address is preserved as static evidence.

## Run

```bash
python3 tools/ghidra/build_construction_frontier.py \
  out/shift_ghidra_database \
  --subsystem physics \
  --subsystem vehicle \
  --max-depth 2 \
  --json-out out/physics_vehicle_construction_frontier.json \
  --targets-out out/physics_vehicle_construction_targets.txt
```

Feed the selected addresses into the targeted instruction/p-code exporter:

```bash
mapfile -t TARGETS < out/physics_vehicle_construction_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/physics_vehicle_construction_instructions.jsonl \
  "${TARGETS[@]}"
```

The resulting `SHIFT.GhidraFunctionInstructions/2` data is the next evidence
needed to determine whether the vtable reference is actually used by a `STORE`
through a proven object pointer, merely read/compared, or participates in some
other operation.

## What the report records

For every selected function the report keeps:

- exact function metadata;
- referenced heuristic table addresses and slot counts;
- the original `vtable-xref-candidate` source status;
- direct edges to/from proven slice functions;
- shortest target-selection distance from each selected subsystem;
- heuristic table slots whose static target address equals a proven slice
  function;
- ordered instruction-export targets for p-code review.

Candidates lacking both callgraph proximity and a proven-slice slot target stay
visible under `unlinked_candidates` but are not exported automatically.

## Evidence boundary

This layer does not prove:

- that a heuristic table is a real class vtable;
- class identity or inheritance;
- that a function is a constructor or destructor;
- that a table reference is a vptr write;
- the object pointer receiving such a write;
- object layout, base offsets or subobject boundaries;
- any indirect-call target or virtual dispatch slot at a call site;
- ownership/lifetime semantics.

Those require targeted instruction/p-code plus independent pointer/layout or
call-site evidence. Unknown relationships remain blockers rather than aliases.
