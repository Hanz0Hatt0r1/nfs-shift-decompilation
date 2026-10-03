# Process 1 — receiver provenance frontier

The upper vehicle-update execution path is now machine-checked through exact
callgraph edges and exact targeted call instructions.  The next unresolved
question is narrower: what value is presented as the receiver candidate at each
direct call into `FUN_007155e9`?

This block adds:

```text
tools/ghidra/analyze_vehicle_receiver_provenance.py
```

Output format:

```text
SHIFT.VehicleReceiverProvenance/1
```

## Inputs

The analyzer consumes:

1. the same targeted `SHIFT.GhidraFunctionInstructions/2` export used by
   `SHIFT.VehicleOwnershipInstructionEvidence/1`;
2. `SHIFT.VehicleOwnershipInstructionEvidence/1`, which freezes the exact caller
   functions and exact call instruction addresses entering `FUN_007155e9`.

Example:

```bash
python3 tools/ghidra/analyze_vehicle_receiver_provenance.py \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_ownership_instruction_evidence.json \
  --json-out out/vehicle_receiver_provenance.json
```

Use `--fail-on-ambiguous` when a downstream step requires every local receiver
trace to be closed before proceeding.

## ABI boundary

If the targeted export reports `FUN_007155e9` as `__thiscall`, the analyzer
records:

```text
ABI receiver-register candidate = ECX
state = inferred
```

This is an ABI convention hint only.  It explicitly does **not** prove:

```text
ECX == this
ECX == vehicle
ECX == vehicle manager
ECX == owner
ECX == persistent state object
```

If the Ghidra calling-convention annotation is not `__thiscall`, the analyzer
leaves the receiver register unknown instead of inventing one.

## Exact callsite gate

Every callsite imported from the prior ownership-instruction contract is
revalidated against the raw instruction export:

```text
instruction.flows contains 0x007155e9
AND
p-code contains CALL
```

A stale/missing callsite or format drift aborts the analysis.

## Conservative backward trace

Tracing starts immediately before each exact call instruction and remains inside
one linear instruction stream.

Supported explicit definitions are deliberately narrow:

```text
MOV ECX, EAX
MOV ECX, dword ptr [ESI + 0x40]
LEA ECX, [EDI + 0x20]
```

For `MOV register, register`, the source register is traced recursively with a
small hop limit.  A simple register-relative `MOV` source additionally requires
Ghidra `LOAD` p-code.  `LEA` is retained as an address-forming source and must
not contain `LOAD` p-code.

A resolved source records only syntax/proven instruction facts:

```text
kind
base_register
displacement
exact definition instruction
```

It does not rename the base register as an object or the displacement as a
field.

## Hard trace barriers

The analyzer refuses to trace through:

- `CALL` / `CALLIND`;
- conditional or unconditional branches;
- indirect branches;
- returns;
- known unsupported writes/clobbers of the tracked register;
- complex/indexed memory sources;
- malformed p-code or operands;
- copy cycles or excessive copy depth.

Examples such as:

```text
MOV ECX,[ESI+0x40]
CALL other_function
CALL FUN_007155e9
```

remain `ambiguous` because the intervening call can invalidate the register
value.

Likewise:

```text
MOV ECX,[ESI+0x40]
JNZ somewhere
CALL FUN_007155e9
```

is not treated as one proven linear definition chain.

When no local definition is found before the call, the result is `unknown`; the
tool does not assume the function-entry ECX value persists.

## Evidence states

`verified` means only that a local syntactic definition chain was recovered
without crossing the prohibited boundaries and, for memory loads, that p-code
supports the load.

`ambiguous` means a source shape exists but a barrier/clobber/complex operand or
other unsupported transformation prevents a safe local proof.

`unknown` means the local slice does not determine the receiver candidate.

The ABI register nomination itself is `inferred`, because calling-convention
metadata is not pointer provenance.

## Handoff to the next static block

A useful resolved record can look like:

```text
callsite 0x........
ABI candidate ECX
ECX <- [ESI + 0x40]
```

The next proof problem is then specific rather than open-ended:

```text
What is ESI at this point?
Does ESI+0x40 produce the same pointer that receives a proven vtable store or
comes from a proven owner/allocation path?
```

Only that independent pointer provenance can promote the result toward object
identity or ownership.

## Not proven

This layer does not prove:

- concrete receiver object identity;
- owner/class/manager identity;
- constructor or destructor role;
- vptr identity;
- persistent field semantics;
- physical units;
- input/control provenance;
- rendered-frame cadence;
- cross-basic-block SSA equivalence.

No original-game execution or runtime capture is used.
