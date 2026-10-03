# Process 1 — lifetime callsite value transfer

`SHIFT.VehicleLifetimePairFrontier/1` narrows the persistent vehicle class
candidate to a finite recovered create/delete function set.  This stage checks
those exact functions at machine-instruction level instead of promoting the
source lifetime shapes directly to constructor/destructor semantics.

Tool:

```text
tools/ghidra/analyze_vehicle_lifetime_callsite_transfer.py
```

Output:

```text
SHIFT.VehicleLifetimeCallsiteTransfer/1
```

## Inputs

The analyzer consumes:

1. `SHIFT.VehicleLifetimePairFrontier/1`;
2. `SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1`;
3. `SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1`;
4. targeted `SHIFT.GhidraFunctionInstructions/2` for the exact factory,
   initializer, deleting-wrapper and teardown functions emitted by the lifetime
   frontier.

Example:

```bash
python3 tools/ghidra/analyze_vehicle_lifetime_callsite_transfer.py \
  out/vehicle_lifetime_pair_frontier.json \
  out/class_evidence/class_create_wrapper_evidence.json \
  out/class_evidence/class_deleting_wrapper_evidence.json \
  out/vehicle_lifetime_transfer_instructions.jsonl \
  --json-out out/vehicle_lifetime_callsite_transfer.json \
  --targets-out out/vehicle_lifetime_helper_targets.txt
```

## Create-side source boundary

The existing create-wrapper artifact already requires a source relationship of
the form:

```text
factory
  → immediate preinitializer helper result assigned to a local
  → the same source local passed to initializer candidate
```

When a Ghidra export was available to that extractor, it also records the direct
factory→helper and factory→initializer edges.

This stage does not trust the source-local name as machine pointer identity. It
re-opens the targeted factory instruction stream and requires exact direct CALL
instructions with:

- flow to the expected helper/initializer address;
- structured p-code `CALL`;
- unique helper and initializer callsites for the candidate;
- helper CALL before initializer CALL.

Multiple matching machine callsites remain `ambiguous`; no branch is selected by
address order.

## Create-side register path

For a target initializer whose Ghidra calling convention is `__thiscall`, `ECX`
is treated as the receiver-register candidate.  The analyzer traces that exact
register backwards from the initializer call through only full-register
`MOV reg, reg` copies.

The path is machine-`verified` only when it reaches `EAX` at the exact helper
CALL without crossing:

- another CALL;
- direct/conditional/indirect branch or return;
- implicit GPR clobbers;
- partial-register writes such as `CL`, `AX`, etc.;
- unsupported register definitions;
- a non-register value source.

A typical accepted shape is:

```text
CALL helper
MOV  ESI,EAX
MOV  ECX,ESI
CALL initializer
```

The statement proven at this level is only:

```text
the value in EAX immediately after the exact helper call is preserved through
explicit register copies into ECX immediately before the exact initializer call
```

### Why the final create transfer remains inferred

A near x86 CALL does not itself encode the callee's return-value semantics.
Recovered source proves that the helper call has a returned value assigned to a
local and that this source local flows to the initializer.  Interpreting the
machine `EAX` value as that helper return therefore combines machine continuity
with source/ABI convention.

Accordingly:

```text
machine_receiver_value_path_state = verified
helper_return_value_semantics_state = inferred
create_value_transfer_state = inferred
```

This is intentional.  It prevents an ABI convention from being mislabeled as a
fully proven allocation/object identity fact.

## Delete-side source boundary

The deleting-wrapper evidence already records a source shape containing:

```text
wrapper
  → teardown transition
  → release helper
```

with teardown-before-release ordering and a narrow bit-0 guard.  When Ghidra
callgraph evidence is available, both wrapper call edges are cross-checked.

This stage re-opens the wrapper machine instructions and requires exact direct
CALL+p-code sites for teardown and release.

## Wrapper entry → teardown receiver

When both wrapper and teardown candidate are annotated `__thiscall`, the
analyzer traces `ECX` backwards from the exact teardown CALL.

Only full-register `MOV` copies are crossed. Calls, branches, partial writes,
implicit clobbers and unsupported definitions terminate the proof.

If the chain reaches wrapper entry `ECX`, the machine register path is
`verified`.  The semantic role of that entry value is still ABI-inferred rather
than an independently proven object identity.

A typical accepted shape is:

```text
MOV ESI,ECX
...
MOV ECX,ESI
CALL teardown
```

The overall teardown lifetime transfer therefore remains capped at `inferred`.

## Release boundary deliberately remains open

The deleting-wrapper source artifact proves the wrapper calls a configured
release helper; it does not prove which machine stack/register operand is the
object pointer at that call.

This stage intentionally reports:

```text
release_argument_value_transfer_state = unknown
release_argument_value_transfer_proven = false
```

and emits the exact release helper as a next targeted instruction function.

The next static block should inspect the release call argument preparation and
helper entry ABI directly rather than assuming that the nearest PUSH or register
contains the same object pointer.

## Next targeted functions

The report emits:

- create-side immediate preinitializer helpers;
- delete-side release helpers.

Those functions are the next boundary for return-value and argument provenance.
They can later be joined to the existing persistent vehicle pointer closure, but
only after exact callsite value flow is established.

## Fail-closed behavior

The analyzer rejects/weakens evidence when:

- a required targeted initializer/teardown function is absent;
- the instruction export format is not v2;
- helper/initializer or teardown/release callsite cardinality is not one;
- expected call order changes;
- initializer/wrapper/teardown calling convention does not support the narrow
  ECX receiver analysis;
- another CALL or a control-flow boundary intervenes;
- a tracked register is partially or implicitly overwritten;
- a register chain originates from unsupported/non-register state;
- the source create/delete row does not uniquely match the descriptor/function
  set from the vehicle lifetime frontier.

## Evidence boundary

Even when both machine paths are verified, the report keeps all of these false:

```text
allocation_semantics_proven
constructor_semantics_proven
delete_flag_semantics_proven
destructor_semantics_proven
release_semantics_proven
release_argument_value_transfer_proven
same_runtime_object_across_lifetime_proven
same_runtime_object_as_vehicle_update_proven
owner_identity_proven
```

The purpose is to close exact local ABI/value-transfer facts while keeping
runtime object identity and language-level lifetime semantics behind independent
proof gates.
