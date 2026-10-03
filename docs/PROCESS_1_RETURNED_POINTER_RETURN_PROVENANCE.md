# Process 1 — returned-pointer target return provenance

The create-side lifetime chain already reaches an exact finite target frontier:

```text
vehicle create wrapper
→ FUN_00886900
→ FUN_00638020 / FUN_006382b0
→ exact returned-pointer instruction targets
```

`SHIFT.VehicleReturnedAllocationPointerBoundary/1` deliberately leaves the
semantic role of those target returns unresolved.  The targeted instruction
export added immediately afterward provides the machine bodies but does not by
itself say what their returned EAX values mean.

This stage removes the next provenance layer without inventing allocator
semantics.

Tool:

```text
tools/ghidra/analyze_vehicle_returned_allocation_pointer_return_provenance.py
```

Output:

```text
SHIFT.VehicleReturnedAllocationPointerReturnProvenance/1
```

## Usage

```bash
python3 tools/ghidra/analyze_vehicle_returned_allocation_pointer_return_provenance.py \
  out/vehicle_returned_allocation_pointer_boundary.json \
  out/vehicle_returned_allocation_pointer_target_instructions.jsonl \
  --json-out out/vehicle_returned_allocation_pointer_return_provenance.json
```

No original-game execution or new runtime capture is used.

## Exact input gate

The boundary must still say:

```text
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
blockers contains returned_allocation_pointer_semantic_role_not_proven
```

The instruction JSONL must contain exactly the boundary's sorted, unique
`required_instruction_targets`: no missing target, no extra target and no
substitution by nearby/name-similar functions.

## Machine model

For every reachable target exit, the analyzer tracks the immediate EAX origin.
Verified local origin classes are:

```text
function-entry-eax
direct-call-result
constant
register-source
memory-source
address-source
```

Ambiguous classes include partial writes, transformed/derived EAX values,
implicit EAX writes and CALLs lacking one exact flow plus structured p-code
`CALL`.

A reachable `RET` also requires p-code `RETURN`.  An external terminal `JMP`
requires p-code `BRANCH`.  Conditional jumps require p-code `CBRANCH`.
Instruction-format or control-flow drift is fail-closed.

## Exact next frontier

When a verified `RET` receives EAX directly from one exact CALL result, that
callee becomes a `next_return_origin_target`.

When a target exits through one exact external tail `JMP`, that destination also
becomes a `next_return_origin_target`.

A CFG merge such as:

```text
path A -> CALL X -> RET
path B -> CALL Y -> RET
```

is not collapsed into one preferred target.  The RET is marked `ambiguous` and
the machine-origin proof remains open.

A verified constant, memory load, address or register return is recorded as such
but does not create a synthetic allocator target.

## Evidence boundary

Even when every target return origin is machine-resolved, the report keeps:

```text
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
```

The distinction is intentional:

```text
exact CALL result reaching EAX/RET
!=
independently proven allocation-producing return value
```

Callgraph adjacency, address proximity, allocation diagnostics, function names
and repeated use are not enough to promote the semantic role.

The next Process 1 step is therefore finite and explicit:

- if `next_return_origin_targets` is non-empty, inspect only those exact targets
  and look for an independently established allocation-producing primitive plus
  exact value continuity;
- if the resolved return origin is non-call state, interpret that exact
  load/address/register origin from independent static structure evidence;
- if machine origins remain ambiguous, repair only the specific CFG/EAX blocker
  reported for that target.

This directly serves the playable Linux slice by narrowing the create-side
object-identity blocker while preserving the existing persistent vehicle pointer
context for the eventual initializer/object-continuity join.
