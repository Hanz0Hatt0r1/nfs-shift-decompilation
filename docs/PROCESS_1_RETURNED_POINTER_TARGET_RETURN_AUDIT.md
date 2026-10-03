# Process 1 — returned-pointer target return audit

The returned allocation-pointer semantic boundary emits a finite instruction
worklist.  After those exact functions have been exported with
`ShiftFunctionInstructionExporter`, this stage opens their bodies and continues
the machine-provenance chain one level deeper.

Tool:

```text
tools/ghidra/analyze_vehicle_returned_allocation_pointer_target_returns.py
```

Output:

```text
SHIFT.VehicleReturnedAllocationPointerTargetReturnAudit/1
```

## Usage

```bash
python3 tools/ghidra/analyze_vehicle_returned_allocation_pointer_target_returns.py \
  out/vehicle_returned_allocation_pointer_boundary.json \
  out/vehicle_returned_allocation_pointer_target_instructions.jsonl \
  --json-out out/vehicle_returned_allocation_pointer_target_return_audit.json \
  --targets-out out/vehicle_returned_allocation_pointer_next_targets.txt
```

## Exact input boundary

The semantic input must still be:

```text
SHIFT.VehicleReturnedAllocationPointerBoundary/1
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
```

and must retain:

```text
returned_allocation_pointer_semantic_role_not_proven
```

The targeted instruction export must be:

```text
SHIFT.GhidraFunctionInstructions/2
```

and contain exactly one resolved function row for every
`required_instruction_targets` address and no extra functions.

This exact-set rule prevents a broader export from becoming an implicit ranking
or semantic candidate pool.

## Return-origin model

Each target is explored through every reachable basic control-flow path.
The analyzer tracks the immediate syntactic origin of EAX.

Machine-resolved origin classes include:

```text
function-entry-eax
direct-call-result
constant
register-source
memory-source
address-source
```

Ambiguous or transformed classes include:

```text
partial-eax-write
stack-source
derived-eax
implicit-eax-write
ambiguous-call-result
ambiguous-eax-write
```

A `RET` is machine-resolved only when exactly one resolved EAX origin reaches it.
If different paths deliver different exact CALL results, the merge remains
ambiguous; no target is selected by address order.

## Direct CALL result

For:

```text
CALL target
...
RET
```

EAX becomes `direct-call-result` only when the CALL has:

- one exact direct flow target;
- p-code `CALL`;
- no later EAX replacement, partial write or transformation before the RET.

The exact target is emitted in:

```text
next_instruction_targets
```

for another bounded static pass.

## External tail transfer

A terminal direct jump:

```text
JMP target
```

becomes a verified external tail origin only when it has one exact external flow
and p-code `BRANCH`.

That target is also emitted into the next finite worklist.

## Local terminal origins

Some target may return a constant, input register, memory load or address without
another function call.

Those origins can be machine-resolved and are recorded under:

```text
terminal_machine_origins
```

but they are not semantic proof.

For example:

```text
XOR EAX,EAX
RET
```

proves an exact zero machine return, not an allocated pointer.

If every target ends in such local origins and there is no deeper function
frontier, the report records:

```text
no-further-call-or-tail-targets
```

while leaving the returned allocation-pointer role unknown.

## Cycle handling

If a discovered next return-origin target points back into the current exact
target set, the report records:

```text
return-origin-cycle-to-current-target
```

and does not report the overall target return-origin frontier as fully resolved.
This avoids repeatedly expanding a recursive/mutually-recursive component as if
it were forward semantic progress.

## P-code gates

Relevant control-flow boundaries require structured p-code:

```text
CALL       -> CALL
RET        -> RETURN
JMP        -> BRANCH
conditional jump -> CBRANCH
```

Missing p-code is treated as evidence drift, not inferred from mnemonic text
alone.

## Output

For each exact input target the report stores:

```text
address
name
calling_convention
reachable_state_count
exit_count
exits[]
machine_return_origins_resolved
next_return_targets[]
terminal_machine_origins[]
blockers[]
```

The top-level union is:

```text
next_instruction_targets
```

and can be written directly with `--targets-out` for another targeted static
instruction export.

## Evidence boundary

This stage deliberately keeps:

```text
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
allocator_abi_proven = false
operator_new_identity_proven = false
object_size_proven = false
constructor_semantics_proven = false
ownership_semantics_proven = false
same_runtime_object_as_vehicle_update_proven = false
```

Recursive machine provenance narrows *where* the return value comes from.  It
cannot assign `allocated-pointer` meaning until an independently established
allocation-producing primitive is joined to an exact value path that survives
to every relevant successful return.
