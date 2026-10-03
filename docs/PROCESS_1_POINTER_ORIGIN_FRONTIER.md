# Process 1 — pointer-origin frontier

`SHIFT.VehicleReceiverProvenance/1` narrows an exact callsite to a local receiver
source such as:

```text
ECX <- [ESI + 0x40]
```

That still does not identify `ESI`.  This block extends only those already
verified syntactic receiver sources toward the origin of their base register.

Tool:

```text
tools/ghidra/analyze_vehicle_pointer_origin_frontier.py
```

Output:

```text
SHIFT.VehiclePointerOriginFrontier/1
```

## Inputs

The analyzer joins four existing evidence layers:

```text
SHIFT.GhidraFunctionInstructions/2
SHIFT.VehicleReceiverProvenance/1
SHIFT.VehicleOwnershipLifecycleFrontier/1
SHIFT.VehicleOwnershipInstructionEvidence/1
```

Example:

```bash
python3 tools/ghidra/analyze_vehicle_pointer_origin_frontier.py \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_receiver_provenance.json \
  out/vehicle_ownership_lifecycle_frontier.json \
  out/vehicle_ownership_instruction_evidence.json \
  --json-out out/vehicle_pointer_origin_frontier.json \
  --targets-out out/vehicle_pointer_origin_targets.txt
```

## Trace policy

The base register is traced only inside the same targeted function and before
the exact instruction that produced the verified receiver source.

Supported definitions remain intentionally narrow:

```text
MOV reg,reg
MOV reg,[base+disp]
LEA reg,[base+disp]
```

A register-relative `MOV` requires `LOAD` p-code.  `LEA` is retained as address
formation and must not contain a `LOAD`.

The trace stops at:

- `CALL` / `CALLIND`;
- conditional or unconditional branch p-code;
- returns;
- unsupported instructions whose first operand is the tracked register;
- complex/indexed memory origins;
- malformed operands/p-code;
- copy cycles or excessive copy depth.

Unlike a permissive def-use heuristic, an unknown first-operand writer is never
crossed.

## Function-entry boundary

When no earlier local definition exists, the result records a function-entry
register state.

For entry `ECX` in a Ghidra `__thiscall` function, the state is only:

```text
inferred: function-entry ABI receiver candidate
```

It is not proof of a concrete `this` object or class.

Other entry registers remain `unknown`.

Register-copy chains propagate the terminal entry source.  For example:

```text
function entry ECX
MOV ESI,ECX
...
MOV ECX,[ESI+0x40]
CALL FUN_007155e9
```

can establish that the local base-origin chain terminates at entry ECX, while
still leaving object identity unresolved.

## Automatic frontier extension

If the base-origin terminal is a function-entry register, the analyzer reads the
exact `direct_incoming_calls` already preserved by
`SHIFT.VehicleOwnershipLifecycleFrontier/1` and emits those parent functions as
the next instruction-export worklist.

This is target selection only:

```text
child entry register provenance unresolved
→ inspect exact parent callsite
```

A direct incoming caller is not promoted to owner, manager, scheduler, or class
identity.

## Vtable overlap

The tool also cross-checks `vtable_store_candidates` from
`SHIFT.VehicleOwnershipInstructionEvidence/1`.

If the same function contains a heuristic vtable-address STORE using the same
textual base register as the receiver source, the overlap is preserved as:

```text
ambiguous
pointer_alias_proven = false
vptr_store_proven = false
```

Equal register spelling in two instructions is not pointer alias proof.

## Evidence states

`verified` means the local base-register origin was resolved to another simple,
p-code-backed register-relative source without crossing a prohibited boundary.

`inferred` is reserved for the narrow ABI entry-ECX candidate in a function
annotated `__thiscall`.

`ambiguous` means a barrier, unsupported write, immediate/complex source, or
other unsupported transformation blocks safe propagation.

`unknown` means the base register reaches function entry without a proven ABI
role or the previous receiver source itself was unresolved.

## Next handoff

When the output reaches a function-entry register, run the existing targeted
instruction exporter on `next_instruction_export_addresses` and analyze those
exact parent callsites.  The next useful proof is:

```text
parent callsite value
→ child entry register
→ local base register
→ receiver field/address source
→ FUN_007155e9
```

Only after that value chain is established should it be joined to allocation,
vtable, reset/destructor, or class-registration evidence.

## Not proven

This layer does not prove:

- object or owner identity;
- class identity;
- vptr identity;
- constructor/destructor role;
- field semantics or units;
- input/control ownership;
- rendered-frame cadence;
- cross-basic-block SSA equivalence.

No original-game execution or runtime capture is used.
