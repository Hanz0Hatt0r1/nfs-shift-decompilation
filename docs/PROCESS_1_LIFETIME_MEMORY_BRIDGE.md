# Process 1 — lifetime memory bridge

The persistent vehicle-state investigation now has an exact class/lifetime
frontier and machine-local create/delete value-transfer evidence.  Separately,
the repository already has a canonical memory-helper runtime manifest for the
retail helper family containing `FUN_00886900` and `FUN_00886930`.

This block joins those evidence domains without turning a memory helper into a
C++ language-level allocator/deallocator or turning an allocation request into a
proven object layout.

Tool:

```text
tools/ghidra/build_vehicle_lifetime_memory_bridge.py
```

Output:

```text
SHIFT.VehicleLifetimeMemoryBridge/1
```

## Inputs

The bridge consumes:

1. `SHIFT.VehicleLifetimePairFrontier/1`;
2. `SHIFT.VehicleLifetimeCallsiteTransfer/1`;
3. `SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1`;
4. `SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1`.

Example:

```bash
python3 tools/ghidra/build_vehicle_lifetime_memory_bridge.py \
  out/vehicle_lifetime_pair_frontier.json \
  out/vehicle_lifetime_callsite_transfer.json \
  out/class_evidence/class_create_wrapper_evidence.json \
  out/memory_wrapper_runtime_manifest.json \
  --json-out out/vehicle_lifetime_memory_bridge.json \
  --targets-out out/vehicle_lifetime_memory_next_targets.txt
```

## Fail-closed identity join

The vehicle side is selected only from rows already marked
`verified_vehicle_lifetime_pair_frontier=true`.

Each create/delete callsite row must map to exactly one such frontier row using:

```text
descriptor
+ exact factory/initializer set membership
```

or:

```text
descriptor
+ exact deleting-wrapper/teardown set membership
```

The bridge preserves the already-proven:

```text
vehicle_pointer_function
vehicle_pointer_source_node
stored_table_address
```

so the memory evidence remains attached to the same persistent vehicle pointer
frontier instead of becoming a disconnected class observation.

## Create side: allocation-size role

The memory runtime manifest is accepted for semantic promotion only when its
status is:

```text
source-joined-semantic-roles
```

and the exact helper row has confirmed forwarding plus exactly one proven
`allocation-size` parameter.

The parameter supplies a source argument index.  The bridge independently
reopens the class create-wrapper source row and splits the recorded helper
argument expression at top-level commas.  It records an integer only when the
selected argument is itself an exact decimal/hex integer literal.

For example, a source call shaped as:

```text
FUN_00886900(56, 4, 0)
```

with proven allocation-size source index `0` yields:

```text
allocation_size_argument_literal_value = 56
allocation_size_argument_literal_state = verified
```

Expressions such as `size + 4`, casts, symbolic constants or malformed/nested
syntax are not folded or guessed.

The bridge then combines this with the already-established machine path from the
helper call result to the initializer receiver candidate.  Because that machine
path still uses ABI/source evidence to interpret the helper return, the combined
`initializer_backing_allocation_request_state` may remain `inferred` even when
the literal and parameter role are each verified.

The value is deliberately **not** renamed as object size.  These remain false:

```text
helper_return_is_allocated_pointer_proven
object_size_proven
constructor_semantics_proven
same_runtime_object_as_vehicle_update_proven
```

The bridge also does not assign a physical unit merely from the parameter name;
`allocation_value_unit_proven` remains false.

## Delete side: released-pointer parameter target

For the exact release helper, the memory runtime manifest may prove one source
argument role:

```text
released-pointer
```

The bridge records both:

```text
source_argument_index
entry_storage
```

from that already-gated manifest.  For the retail helper family this can expose
a physical target such as:

```text
Stack[0x4]:4
```

without guessing which caller instruction supplied the value.

This closes an important boundary: Process 1 now knows exactly which helper
parameter/storage must receive the candidate released pointer.  It still does
not prove caller-to-helper transport.  The upstream field
`release_argument_value_transfer_state` is preserved unchanged; if it remains
`unknown`, the bridge emits a dedicated blocker and selects the deleting wrapper
for the next call-argument pass.

## Next frontier

The report emits two classes of exact targets:

- the create helper, to prove its return-value semantics beyond the existing
  pool-allocation-path participation;
- the deleting wrapper, to trace the exact value placed into the proven
  released-pointer entry storage of the release helper.

Those are the remaining local boundaries before attempting a whole-lifetime
identity chain:

```text
create helper result
→ initializer receiver
→ persistent vehicle pointer node
→ ... update lifetime ...
→ deleting-wrapper candidate pointer
→ release helper released-pointer parameter
```

No equality across those distant stages is inferred merely because the same
class descriptor or vtable is present.

## Evidence boundary

The bridge is intentionally fail-closed:

- duplicate memory-helper identities abort;
- duplicate create source rows abort;
- descriptor/function-set drift aborts;
- a weaker memory runtime status cannot promote semantic parameter roles;
- nonliteral allocation expressions remain unknown;
- allocation request value is not object-size proof;
- released-pointer parameter role is not caller argument-transport proof;
- helper names do not prove compiler `operator new` / `operator delete` identity;
- no constructor/destructor/owner identity is promoted;
- no frame cadence, physical units or runtime object equality are invented.

No original game execution or new runtime capture is used.
