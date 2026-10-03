# Process 1 — create-backend return-origin frontier

This stage continues the create-side lifetime chain after
`SHIFT.VehicleCreateHelperReturnProvenance/1`.

The preceding artifact proves that every reachable exit of `FUN_00886900` is
machine-backed by one of the two known retail create backends:

```text
FUN_00886900
  -> FUN_00638020
  -> FUN_006382b0
```

That fact does **not** prove what those backend return values mean.  In
particular, an allocation diagnostic inside `FUN_00638020` is not sufficient to
claim that EAX is an allocated object pointer.

This block therefore reopens the two backend instruction bodies and asks a
narrower question:

```text
for every reachable backend exit,
what is the immediate machine origin of the returned value/control transfer?
```

Tool:

```text
tools/ghidra/analyze_vehicle_create_backend_return_frontier.py
```

Output:

```text
SHIFT.VehicleCreateBackendReturnOriginFrontier/1
```

## Inputs

```bash
python3 tools/ghidra/analyze_vehicle_create_backend_return_frontier.py \
  out/vehicle_create_helper_return_provenance.json \
  out/memory_backend_evidence.json \
  out/memory_backend_instructions_v2.jsonl \
  --json-out out/vehicle_create_backend_return_frontier.json
```

The inputs must be:

1. `SHIFT.VehicleCreateHelperReturnProvenance/1`;
2. `SHIFT-MEMORY-BACKEND-EVIDENCE/1`;
3. targeted `SHIFT.GhidraFunctionInstructions/2` rows containing both
   `FUN_00638020` and `FUN_006382b0`.

The upstream helper report must already prove verified exits through both
backends.  The backend evidence must retain the established roles:

```text
FUN_00638020 -> allocation-diagnostic-backend
FUN_006382b0 -> create-fallback-backend
```

Role drift, missing targets, duplicate instruction rows and instruction-format
drift are fail-closed errors.

## Machine origin model

The analysis explores the complete reachable CFG of each backend.  EAX is
tracked as an immediate syntactic origin, not as an allocator semantic value.

Exact origin classes include:

```text
function-entry-eax
constant
register-source
memory-source
address-source
direct-call-result
```

Those classes can be machine-verified because the local instruction explicitly
identifies their immediate source.

The following remain ambiguous:

```text
partial-eax-write
stack-source
derived-eax
implicit-eax-write
ambiguous-call-result
ambiguous-eax-write
```

Examples that deliberately stop the proof include a write to `AL` after a
backend call, arithmetic that transforms EAX, an indirect/non-p-code-confirmed
CALL, or multiple CFG paths delivering different EAX origins to one RET.

## Direct CALL result

For a direct call:

```text
CALL inner_target
...
RET
```

EAX becomes an exact `direct-call-result` only when:

- the instruction is a machine `CALL`;
- its `flows` identify exactly one target;
- structured p-code contains `CALL`;
- no later instruction replaces or partially modifies EAX before the RET.

When these conditions hold, the inner target is emitted in
`next_backend_return_targets` for the next static pass.

This proves only:

```text
backend return EAX == immediate result of this exact CALL
```

It does not prove:

```text
inner target is an allocator
returned EAX is a pointer
returned pointer owns storage
returned storage belongs to the vehicle object
```

## External tail transfer

A backend may terminate with a direct external jump:

```text
JMP inner_target
```

That exit becomes verified only when:

- one exact external flow target exists;
- p-code contains `BRANCH`.

The target is then also exported in `next_backend_return_targets`.

The report calls this an `external-tail-transfer`; it does not assign a C/C++
function semantic role to the target.

## CFG merge policy

All reachable paths are explored.  A RET is verified only when exactly one
resolved EAX origin reaches it.

For example:

```text
branch A -> CALL X -> RET
branch B -> CALL Y -> RET
```

produces two exact machine origins, but the merged RET remains `ambiguous`.  No
address ordering, branch frequency or preferred path is used to select one.

Similarly, missing `CBRANCH`, `BRANCH`, `CALL` or `RETURN` p-code at the
relevant control-flow boundary is a blocker rather than an invitation to infer
compiler intent.

## Relationship to existing memory evidence

The project already proves useful but separate facts:

- `FUN_00638020` contains the retail allocation diagnostic;
- a physical entry storage supplies the diagnostic `%d` byte count;
- `FUN_00886900` forwards its create arguments into the two backends;
- every reachable `FUN_00886900` exit is sourced from one of those backends.

This stage adds backend **return-origin** information only.  It intentionally
does not collapse those facts into an allocator ABI.

In particular, the allocation diagnostic proves a byte-count role on an input.
It does not prove the semantic role of EAX at every backend exit.

## Output frontier

For each backend the report records:

```text
address
role
calling_convention
reachable_state_count
exit_count
exits[]
machine_return_origins_resolved
next_return_origin_targets[]
blockers[]
return_value_semantics_state
allocated_pointer_return_proven
```

At the top level it emits the union:

```text
next_backend_return_targets[]
```

These are the exact internal CALL-result or external-tail targets that can be
reopened next.  They are not ranked and are not assigned allocation semantics.

The report also carries forward the existing vehicle create context, including
the persistent vehicle pointer source node and the source-backed allocation
request value, while adding:

```text
create_backend_return_frontier_state
create_backend_return_targets
backend_return_value_semantics_state
```

## Evidence boundary

Even when every backend machine exit is verified, all of the following remain
false:

```text
allocated_pointer_return_proven
allocator_abi_proven
operator_new_identity_proven
object_size_proven
constructor_semantics_proven
ownership_semantics_proven
same_runtime_object_as_vehicle_update_proven
```

The distinction is intentional.  Machine provenance answers *where a value came
from*.  It does not by itself answer *what the value means*.

The next useful Process 1 pass is to reopen the finite
`next_backend_return_targets` set and determine whether static instruction,
string/callgraph or source evidence can independently establish a returned
allocation-pointer role.  If it cannot, the semantic boundary remains unknown
rather than being inferred from naming or call position.
