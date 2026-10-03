# Process 1 — upper direct vehicle-update contract

After the persistent BODY writer was closed, the first outer-update branch was
known statically as:

```text
FUN_00715380 -> FUN_00713050 -> FUN_00794a30 -> FUN_00770e80
```

The saved Ghidra caller-frontier evidence also records the next direct edge:

```text
0x00715602  FUN_007155e9 -> FUN_00715380
```

This block turns that textual observation into a fail-closed machine contract:

```text
tools/ghidra/build_vehicle_upper_direct_contract.py
```

Output format:

```text
SHIFT.VehicleUpperDirectContract/1
```

## Input requirement

Generate the existing caller frontier with enough depth to include the next
caller:

```bash
python3 tools/ghidra/build_vehicle_outer_update_caller_frontier.py \
  out/shift_ghidra_database \
  --upstream-depth 3 \
  --json-out out/vehicle_outer_update_caller_frontier_depth3.json
```

Then build the upper contract:

```bash
python3 tools/ghidra/build_vehicle_upper_direct_contract.py \
  out/vehicle_outer_update_caller_frontier_depth3.json \
  --json-out out/vehicle_upper_direct_contract.json \
  --targets-out out/vehicle_upper_direct_targets.txt
```

## Verified direct chain

The contract requires all of the following exact relationships:

```text
FUN_007155e9 -> FUN_00715380       exactly 1 direct call
FUN_00715380 -> FUN_00713050       exactly 1 direct call
FUN_00713050 -> FUN_00794a30       exactly 3 direct calls
FUN_00794a30 -> FUN_00770e80       established by the input caller frontier
```

The resulting path is:

```text
0x007155e9
  -> 0x00715380
      -> 0x00713050
          -> 0x00794a30
              -> 0x00770e80
```

The contract also requires that the alternate outer-update caller
`FUN_0079b2d0` still has zero direct incoming calls in the saved callgraph.  If
that changes, the split direct/indirect ownership frontier must be re-audited
instead of preserving a stale conclusion.

## What is actually promoted

Only direct execution edges and their exact call instructions/counts are
promoted to `verified` evidence.

This layer does **not** infer that:

- `FUN_007155e9` owns the vehicle/update object;
- `FUN_007155e9` is a frame scheduler;
- any of the functions are recovered retail class methods;
- callgraph depth is an object-ownership relation;
- the branch executes once per rendered frame;
- input/controller state originates at `FUN_007155e9`;
- unknown fields have physical units or semantic names.

The candidate record for `FUN_007155e9` therefore remains semantically
`inferred`: its participation immediately above the verified chain is known,
but its higher-level role is not.

## Next static target

The instruction export worklist emitted by this contract is deliberately narrow:

```text
0x007155e9
```

The next pass should join exact instruction/p-code/reference evidence for this
function and answer:

1. which object/register is passed into `FUN_00715380`;
2. which offsets of that object are read or written before/after the call;
3. where the function's own receiver originates;
4. whether any constructor/vtable/destructor or registration evidence refers to
   the same object flow;
5. whether arguments can be traced to a concrete input/control owner;
6. whether a static scheduler path proves invocation cadence.

Those questions remain blockers until instruction/reference evidence exists.
The companion `build_indirect_dispatch_frontier.py` handles the separate
ownerless `FUN_0079b2d0` branch without conflating its heuristic vtable/static
pointer evidence with this verified direct-call chain.

## Fail-closed conditions

The tool aborts if:

- the caller-frontier format changes;
- upstream depth is less than 3;
- the two direct callers of `FUN_00770e80` change;
- `FUN_0079b2d0` acquires a direct incoming caller;
- any required upper function loses metadata;
- an expected upstream depth changes;
- any of the exact direct-call counts in the chain changes.

That behavior is intentional: a newer static export that changes the graph must
be investigated, not silently coerced into the old contract.
