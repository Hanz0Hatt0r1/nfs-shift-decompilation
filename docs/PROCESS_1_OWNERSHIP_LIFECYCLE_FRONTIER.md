# Process 1 — ownership/lifecycle frontier

The persistent BODY path and the first upper direct execution chain are now
separate machine-checked contracts.  The next unresolved boundary is not BODY
integration arithmetic; it is object ownership and lifecycle provenance above
that chain.

The current verified direct path is:

```text
FUN_007155e9
  -> FUN_00715380
      -> FUN_00713050
          -> FUN_00794a30
              -> FUN_00770e80
```

The alternate branch remains separate:

```text
FUN_0079b2d0 -> FUN_00770e80
```

with no direct incoming caller in the saved Ghidra callgraph.

This block adds:

```text
tools/ghidra/build_vehicle_ownership_lifecycle_frontier.py
```

Output format:

```text
SHIFT.VehicleOwnershipLifecycleFrontier/1
```

## Goal

Advance the frontier above `FUN_007155e9` while keeping direct observations and
heuristic lifecycle evidence separate.

The builder answers four narrow questions automatically:

1. which exact direct callgraph edges enter `FUN_007155e9`;
2. which of those caller functions also appear as xrefs to heuristic vtable
   candidates containing `FUN_007155e9` or `FUN_0079b2d0`;
3. which exporter `constructors.jsonl` candidates reference those same heuristic
   vtables;
4. which exact functions should receive the next instruction/p-code export.

It does **not** answer class identity or ownership by inference.

## Inputs

Generate or retain the depth-3 upper contract:

```bash
python3 tools/ghidra/build_vehicle_outer_update_caller_frontier.py \
  out/shift_ghidra_database \
  --upstream-depth 3 \
  --json-out out/vehicle_outer_update_caller_frontier_depth3.json

python3 tools/ghidra/build_vehicle_upper_direct_contract.py \
  out/vehicle_outer_update_caller_frontier_depth3.json \
  --json-out out/vehicle_upper_direct_contract.json
```

Build the independent indirect-dispatch inventory for the alternate branch:

```bash
python3 tools/ghidra/build_indirect_dispatch_frontier.py \
  out/shift_ghidra_database \
  0x0079b2d0 \
  --json-out out/vehicle_indirect_dispatch_frontier.json
```

Then join both boundaries to the raw static export:

```bash
python3 tools/ghidra/build_vehicle_ownership_lifecycle_frontier.py \
  out/shift_ghidra_database \
  out/vehicle_upper_direct_contract.json \
  out/vehicle_indirect_dispatch_frontier.json \
  --json-out out/vehicle_ownership_lifecycle_frontier.json \
  --targets-out out/vehicle_ownership_lifecycle_targets.txt
```

## Evidence policy

### Verified observations

The builder may mark these facts as `verified`:

- exact direct incoming call edges to `FUN_007155e9`;
- exact call instruction addresses for those edges;
- exact direct incoming/outgoing callgraph records for the discovered callers;
- exact absence of direct incoming edges to `FUN_0079b2d0`, cross-checked against
  both the raw callgraph and the existing indirect-dispatch report;
- exact strings associated by the Ghidra string-xref export with a candidate
  function.

### Ambiguous lifecycle evidence

The following remain `ambiguous` even when several layers overlap:

- a function appears in `function_xrefs` for a heuristic vtable candidate;
- a function appears in `constructors.jsonl` for that candidate;
- a direct caller of `FUN_007155e9` also has one or both of those heuristic
  relationships;
- a candidate vtable contains `FUN_007155e9` or `FUN_0079b2d0` in one slot.

Those observations justify a targeted instruction/reference audit.  They do not
prove that the function is a constructor, destructor, vehicle owner, manager,
scheduler, or virtual dispatcher.

## Candidate records

Every exact caller of `FUN_007155e9` records:

- address and current Ghidra name;
- direct calls to `FUN_007155e9` and their exact instruction addresses;
- direct incoming and outgoing calls;
- unresolved indirect calls originating in that function;
- string-xref observations;
- overlap with relevant heuristic vtable/constructor candidates;
- execution-edge state;
- owner/lifecycle/scheduler proof flags.

Owner and lifecycle semantics remain fail-closed.

## Targeted next export

The emitted instruction target list contains the union of:

- `FUN_007155e9`;
- every exact direct caller of `FUN_007155e9`;
- `FUN_0079b2d0`;
- functions that xref relevant heuristic vtable candidates;
- exporter constructor candidates for those same vtables;
- candidate owners already emitted by the indirect-dispatch frontier.

Run the existing targeted instruction exporter on that list:

```bash
mapfile -t TARGETS < out/vehicle_ownership_lifecycle_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  "${TARGETS[@]}"
```

The next semantic promotion requires exact evidence such as:

- the receiver register/object passed from an upper caller into `FUN_007155e9`;
- an exact vtable store to that same pointer flow;
- a destructor/reset path operating on the same object identity;
- source/p-code offset reads and writes tied to that same base pointer;
- argument/dataflow from an independently identified input/control source;
- a static scheduler path proving cadence.

## Fail-closed conditions

The builder aborts when:

- the upper-contract or indirect-frontier format drifts;
- the verified upper path no longer starts at `FUN_007155e9` and ends at
  `FUN_00770e80`;
- the alternate branch acquires a direct incoming call;
- the raw callgraph and indirect-dispatch report disagree;
- `FUN_007155e9` has no direct caller in the current export;
- a required function disappears from `functions.jsonl`;
- `vtables.json` is no longer explicitly marked as heuristic candidates.

These failures require re-auditing the new static export instead of coercing it
into the previous topology.
