# Process 1 — create-helper return provenance

The vehicle lifetime path now reaches the retail memory-helper boundary from both
sides:

```text
create wrapper
→ FUN_00886900
→ initializer receiver candidate
→ exact persistent vehicle pointer frontier
```

and:

```text
deleting wrapper
→ teardown receiver candidate
→ FUN_00886930 released-pointer parameter
```

The delete-side local transport is covered by
`SHIFT.VehicleReleasePointerTransfer/1`.  On the create side, the lifetime-memory
bridge already joins the source-backed allocation-request argument to
`FUN_00886900`, but deliberately leaves the helper return semantics open.

This block adds:

```text
tools/ghidra/analyze_vehicle_create_helper_return_provenance.py
```

Output format:

```text
SHIFT.VehicleCreateHelperReturnProvenance/1
```

## Inputs

The analyzer consumes four independent evidence layers:

1. `SHIFT.VehicleLifetimeMemoryBridge/1`;
2. retail `SHIFT-MEMORY-WRAPPER-FORWARDING/1` with tail-call annotations;
3. `SHIFT-MEMORY-BACKEND-EVIDENCE/1`;
4. targeted `SHIFT.GhidraFunctionInstructions/2` containing `FUN_00886900`.

Example:

```bash
python3 tools/ghidra/analyze_vehicle_create_helper_return_provenance.py \
  out/vehicle_lifetime_memory_bridge.json \
  out/memory_wrapper_forwarding.json \
  out/memory_backend_evidence.json \
  out/fun_00886900_instructions.jsonl \
  --json-out out/vehicle_create_helper_return_provenance.json \
  --targets-out out/vehicle_create_backend_targets.txt
```

`--require-all-exits-backend-sourced` is a strict gate for downstream work.

## Retail control-flow shape

The existing retail forwarding evidence recovers two backend paths from
`FUN_00886900`:

```text
nonzero branch:
    ...
    CALL FUN_00638020
    ...
    RET

fallback branch:
    ...
    JMP FUN_006382b0
```

The first backend is independently classified as the allocation-diagnostic
backend.  The second is independently classified as the create fallback backend.
Those role labels describe static evidence domains; neither label proves the
semantic meaning of the value returned in `EAX`.

## All-exit machine analysis

The new analyzer reopens the raw v2 instruction slice and explores every
reachable local control-flow state from function entry.

For a normal `RET` exit it tracks the current `EAX` origin.  A return is marked
machine-verified only when the unique incoming `EAX` origin is the result of an
exact direct CALL to one of the two expected create backends and the call itself
has structured p-code `CALL` plus exact direct flow.

For the retail tail path, the terminal external `JMP` must:

- target exactly `FUN_006382b0` or `FUN_00638020`;
- carry branch p-code;
- exactly match a `transfer_kind=tail-call` site in the independent forwarding
  report.

The analyzer does **not** pick one successful exit and ignore the rest.  The
helper-level gate becomes ready only when every reachable `RET` or external tail
exit is backend-sourced.

## EAX clobber policy

After a backend CALL, writes to `EAX`/`AX`/`AL`/`AH` break value identity before
`RET`.  Supported explicit writes and unsupported first-operand writes both
terminate the backend-result provenance for that path.

An unrelated CALL also changes the EAX origin to that other call result.  Thus a
shape such as:

```text
CALL create_backend
XOR EAX,EAX
RET
```

cannot be promoted even though the earlier backend call was correct.

Control-flow states are kept separately.  If distinct EAX origins converge on
the same `RET`, the exit remains ambiguous rather than selecting one by address
or traversal order.

## What becomes verified

For the retail wrapper shape the report may prove:

```text
all_reachable_helper_exits_backend_sourced = true
```

with two independent machine observations:

```text
CALL FUN_00638020 result EAX survives to RET
external tail JMP transfers control to FUN_006382b0
```

The vehicle join keeps the existing descriptor, class metadata, factory,
initializer, allocation-request value and exact persistent vehicle pointer node
alongside this machine provenance.

## What remains open

This stage deliberately keeps the strongest semantic claim below pointer
identity:

```text
helper_return_value_semantics_state = inferred
helper_return_is_allocated_pointer_proven = false
```

Why: an allocation diagnostic proves that `FUN_00638020` participates in the
allocation backend path and identifies a physical allocation-size value.  It
does not independently prove that the value left in `EAX` on every successful
backend exit is the allocated pointer.

Similarly, the name `create-fallback-backend` does not prove the semantic role of
its returned value.

The following all remain false:

```text
backend_return_register_semantics_proven
helper_return_is_allocated_pointer_proven
object_size_proven
operator_new_identity_proven
constructor_semantics_proven
same_runtime_object_as_vehicle_update_proven
owner_identity_proven
```

The allocation request value retained from the previous bridge is also not
renamed as object size.

## Next targeted frontier

The report emits exactly the two create backends:

```text
FUN_00638020
FUN_006382b0
```

The next useful static block is therefore backend return-value provenance:

```text
backend machine exits
→ EAX value origin
→ diagnostic/source allocation result semantics
→ FUN_00886900 exit EAX
→ initializer receiver candidate
```

Only after the returned value itself is independently tied to the allocated
pointer should Process 1 attempt to connect create-time pointer identity to the
already-proven persistent vehicle-update pointer node.

## Evidence boundary

The analyzer remains fail-closed:

- wrapper forwarding must already be confirmed;
- expected backend set must exactly match the forwarding report;
- exact CALL/JMP instructions are rechecked from raw v2 instructions;
- transfer-kind drift between raw instructions and forwarding evidence weakens
  the exit;
- RET without RETURN p-code is a blocker;
- EAX clobbers prevent backend-result promotion;
- external tail targets outside the create backend pair remain unknown;
- backend diagnostic labels never become return-pointer semantics automatically;
- no constructor, owner, scheduler, frame cadence, field meaning or physical unit
  is introduced.

No original game execution or new runtime capture is used.
