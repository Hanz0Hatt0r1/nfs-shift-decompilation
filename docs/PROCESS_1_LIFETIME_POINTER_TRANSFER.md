# Process 1 — lifetime pointer transfer

The static vehicle-state chain now has two independently closed regions:

```text
vehicle update pointer provenance
→ exact candidate-table STORE through the same local pointer value
→ unique PE-backed class/lifecycle row
→ descriptor + exact vtable lifetime-pair frontier
```

and, below it:

```text
wheel/contact
→ constraint assembly
→ solver/post-solve
→ persistent BODY writer
→ next BODY state
```

`SHIFT.VehicleLifetimePairFrontier/1` narrows a verified vehicle pointer candidate
to a finite set of create-side and delete-side functions, but it intentionally
stops before claiming that a concrete pointer value crosses those lifecycle
calls.

This block adds:

```text
tools/ghidra/analyze_vehicle_lifetime_pointer_transfer.py
```

Output:

```text
SHIFT.VehicleLifetimePointerTransfer/1
```

## Inputs

The analyzer consumes:

1. `SHIFT.VehicleLifetimePairFrontier/1`;
2. `SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1`;
3. one targeted `SHIFT.GhidraFunctionInstructions/2` export containing the
   selected factory/initializer/deleting-wrapper/teardown functions.

Example:

```bash
python3 tools/ghidra/analyze_vehicle_lifetime_pointer_transfer.py \
  out/vehicle_lifetime_pair_frontier.json \
  out/class_evidence/class_lifetime_pair_evidence.json \
  out/vehicle_lifetime_functions.jsonl \
  --json-out out/vehicle_lifetime_pointer_transfer.json \
  --targets-out out/vehicle_lifetime_next_targets.txt
```

Use `--require-create-delete-machine-transfer` when a downstream stage requires
at least one machine-verified create-side and delete-side value transfer.

## Identity cross-check

A verified lifetime-frontier row is rejoined to the class lifetime-pair evidence
by the same two identity keys used by the previous stage:

```text
recovered class descriptor
+ exact numeric own-vtable address
```

The match must be unique.  The factory/initializer/deleting-wrapper/teardown
function sets carried by the frontier must also exactly equal the underlying
lifetime-pair sets.  Any drift aborts the analysis.

Class-name strings remain descriptive metadata and are not used as identity
keys.

## Create-side machine transfer

The create-side source evidence already records a shape of the form:

```text
factory
→ immediate preinitializer helper
→ initializer candidate
```

and states that the helper result flows to the initializer at recovered-source
level.

This block asks a narrower machine question:

```text
Does the exact helper CALL result value reach the exact initializer CALL
receiver-register candidate without an intervening unsupported write/call/branch?
```

For 32-bit x86 the machine trace accepts only:

```text
CALL exact_helper
...
MOV reg, EAX
MOV ECX, reg
CALL exact_initializer
```

with arbitrary explicit register-copy depth up to the conservative limit.

The exact helper call and exact initializer call must each be unique in the
factory function and must carry p-code `CALL` plus direct flow to the expected
callee.

A call other than the selected helper encountered while tracing the candidate
value is a barrier.  Branches, returns, unsupported register writers, complex
sources and copy cycles are also fail-closed.

When the trace terminates at the exact selected helper call result in `EAX`, the
report may state:

```text
machine_value_transfer_state = verified
exact_helper_result_reaches_initializer_receiver_candidate = true
```

This is a register/value-flow fact.  It does not prove that the helper allocates
memory or that the returned value is semantically an object pointer.

## Delete-side machine transfer

For a deleting-wrapper/teardown pair the analyzer checks the complementary
boundary:

```text
wrapper function-entry ECX candidate
→ explicit local register copies
→ teardown callsite ECX candidate
→ exact teardown CALL
```

A verified machine transfer means the same entry register value reaches the
teardown receiver-register candidate along the accepted linear instruction
slice.

Calls, branches, returns or unsupported clobbers before the teardown call keep
the transfer ambiguous/unknown.

The release helper is deliberately not folded into this proof yet.  It may use a
different calling convention or argument transport, and therefore requires a
separate targeted argument/pointer-transfer pass.

## ABI evidence state

The report separates machine value-flow from semantic receiver interpretation.

`__thiscall` metadata nominates `ECX` as the receiver-register candidate, but that
ABI role remains `inferred` rather than `verified` object identity.

Therefore a row can legitimately contain:

```text
machine_value_transfer_state = verified
lifetime_transfer_evidence_state = inferred
```

This is intentional.  The first field says the same machine value reaches the
selected register at the selected callsite.  The second says interpreting that
register as the receiver depends on calling-convention evidence.

## What remains unproven

Even when create and delete machine transfers are both verified, the following
remain false:

```text
allocator_semantics_proven
constructor_semantics_proven
destructor_semantics_proven
release_semantics_proven
owner_identity_proven
same_runtime_object_across_create_update_delete_proven
```

The create-side helper result and the deleting-wrapper entry receiver have not
yet been connected to the same persistent vehicle-update pointer node across the
whole lifetime.

## Next targeted frontier

The report emits the lifetime helpers that remain semantically unresolved:

```text
preinitializer helpers
release helpers
```

The next static block should inspect those helpers and their exact callers to
answer two independent questions:

1. what value/source produces the create-side helper result and where that value
   is stored before the proven vehicle-update pointer chain begins;
2. how the deleting wrapper passes the same candidate pointer to the release
   helper after teardown.

Only after those pointer identities are tied to the existing
`VehiclePointerValueClosure` should same-runtime-object lifetime continuity be
considered for promotion.

## Evidence policy

This stage stays fail-closed:

- multiple exact calls are not resolved by order;
- missing exact calls remain unknown;
- an unrelated intervening call is a barrier;
- unsupported register writes are barriers;
- `__thiscall` does not prove class/object identity;
- `EAX` after a helper call does not prove allocation semantics;
- create/delete shape adjacency does not prove the same runtime object;
- no physical units, frame cadence, ownership or scheduler semantics are
  introduced.

No original game execution or new runtime capture is used.
