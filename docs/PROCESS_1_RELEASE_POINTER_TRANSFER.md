# Process 1 — release-pointer transfer

`SHIFT.VehicleLifetimeCallsiteTransfer/1` proves a narrow machine register path
from deleting-wrapper entry toward the teardown receiver, but deliberately leaves
the later release-helper argument unresolved.

The project already has an independent memory-wrapper semantic contract:

```text
SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1
```

For the recurring retail release helper `FUN_00886930`, that contract proves one
parameter role:

```text
source argument index 2
→ helper entry storage Stack[0x4]:4
→ semantic role released-pointer
```

This block joins those two evidence families at the exact wrapper callsite.

Tool:

```text
tools/ghidra/analyze_vehicle_release_pointer_transfer.py
```

Output:

```text
SHIFT.VehicleReleasePointerTransfer/1
```

## Inputs

```bash
python3 tools/ghidra/analyze_vehicle_release_pointer_transfer.py \
  out/vehicle_lifetime_callsite_transfer.json \
  out/memory_wrapper_runtime_manifest.json \
  out/vehicle_lifetime_transfer_instructions.jsonl \
  --json-out out/vehicle_release_pointer_transfer.json
```

Inputs must be:

1. `SHIFT.VehicleLifetimeCallsiteTransfer/1`;
2. `SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1`;
3. targeted `SHIFT.GhidraFunctionInstructions/2` containing the deleting wrapper
   and any teardown callee whose ABI preservation must be crossed.

## Memory-wrapper semantic gate

The release helper is accepted only when its manifest row has:

- `forwarding_confirmed=true`;
- exactly one parameter with `semantic_role=released-pointer`;
- `semantic_role_proven=true`;
- entry storage exactly `Stack[0x4]:4`.

The last restriction is deliberate.  This version implements only the physical
stack shape for which the caller-side mapping can be proved locally.  A future
helper with another storage shape remains `unknown` rather than being coerced
into this contract.

## Caller stack mapping

For the supported release parameter, the analyzer walks backward from the exact
direct release CALL and accepts one caller-side shape:

```text
PUSH full_32_bit_GPR
...
CALL release_helper
```

Between the PUSH and CALL, `ESP` must remain unchanged.  Another call, branch,
return, stack-pointer write or unsupported stack manipulation is a barrier.

On 32-bit x86, the PUSH places the value at caller stack top and CALL then pushes
the return address.  Therefore that value appears at callee entry
`Stack[0x4]`.  This specific stack mapping is recorded as `verified`.

Memory PUSH operands and immediate PUSH operands are not accepted as pointer
identity in this stage; only a full GPR can be traced back through the existing
register model.

## Crossing teardown

A normal deleting-wrapper shape often saves the wrapper entry receiver in a
nonvolatile register, calls teardown, then later pushes the saved value for the
release helper:

```text
MOV ESI,ECX
...
CALL teardown
...
PUSH ESI
...
CALL release_helper
```

To recover that path, this analyzer allows a tracked register to cross an exact
direct CALL only when all of the following hold:

- tracked register is one of `EBX`, `ESI`, `EDI`, `EBP`;
- the exact CALL target is present in the same instruction export;
- the target calling convention is one of the standard recovered 32-bit x86
  conventions (`__cdecl`, `__stdcall`, `__thiscall`, `__fastcall`).

Such preservation is **ABI-inferred**, not machine-verified from the callee body.
Volatile registers such as `EAX`, `ECX` and `EDX` cannot cross the teardown call
through this gate.

Branches, indirect calls, partial-register writes, implicit clobbers and
unsupported definitions terminate the trace.

## Same wrapper-entry value on both delete paths

The prior lifetime-callsite artifact already records whether teardown receives a
machine-verified value originating at wrapper entry `ECX`.

This stage separately traces the release stack argument to wrapper entry.  When
both paths end at the same syntactic entry source:

```text
wrapper entry ECX
  → teardown receiver

wrapper entry ECX
  → saved nonvolatile GPR
  → release helper Stack[0x4]
```

it records:

```text
same_wrapper_entry_value_to_teardown_and_release_state
```

The state is normally `inferred` when nonvolatile preservation across teardown
was needed.

## What becomes proven

The independent memory contract can make this statement true:

```text
released_pointer_parameter_semantics_proven = true
```

That means the selected helper parameter is independently proven to carry the
released-pointer semantic role.

The local stack mapping may also be `verified`.

However, the overall lifetime statement remains capped by the weakest evidence.
In the common saved-ESI case:

```text
released-pointer parameter semantics       proven
PUSH → Stack[0x4] mapping                  verified
ESI preserved across teardown CALL         inferred
wrapper-entry ECX receiver role            inferred
---------------------------------------------------
release_pointer_lifetime_transfer_state     inferred
```

This prevents ABI conventions from being promoted to whole-object lifetime
identity.

## Unsupported shapes

The analyzer remains fail-closed for:

- release helpers absent from the memory manifest;
- unconfirmed wrapper forwarding;
- non-unique or differently stored released-pointer parameters;
- multiple exact release callsites;
- memory/immediate PUSH arguments;
- explicit or implicit `ESP` changes between argument preparation and CALL;
- volatile-register values that would need to survive teardown;
- unknown/indirect teardown calls;
- nonstandard/unknown teardown calling conventions.

## Evidence boundary

Even after a successful transfer, all of these remain false:

```text
operator_delete_identity_proven
destructor_semantics_proven
same_runtime_object_as_vehicle_update_proven
owner_identity_proven
```

The stage proves that one wrapper-entry ABI value reaches a parameter whose
released-pointer semantic role is independently established.  It does not prove
that wrapper entry is the same runtime object instance observed on the persistent
vehicle update path, nor that the helper is language-level `operator delete`.

The next useful Process 1 step is therefore either:

- join create-side helper return provenance to existing memory-allocation static
  evidence, if an allocated-pointer return role can be established; or
- connect lifetime entry values back into `SHIFT.VehiclePointerValueClosure/1`
  through exact factory/initializer and teardown caller chains.
