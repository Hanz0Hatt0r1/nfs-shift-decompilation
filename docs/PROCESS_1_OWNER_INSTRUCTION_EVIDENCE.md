# Process 1 — owner/lifecycle instruction evidence join

`SHIFT.VehicleOwnershipLifecycleFrontier/1` selects the exact direct callers of
`FUN_007155e9` plus the heuristic lifecycle/dispatch functions that deserve a
targeted instruction pass.  This block consumes that target list and joins it to
`SHIFT.GhidraFunctionInstructions/2`.

The new analyzer is:

```text
tools/ghidra/analyze_vehicle_ownership_instruction_evidence.py
```

Output format:

```text
SHIFT.VehicleOwnershipInstructionEvidence/1
```

## Purpose

Move from function-level candidate relationships to exact machine-instruction
and p-code evidence while keeping pointer/object meaning fail-closed.

For each exact direct caller of `FUN_007155e9`, the analyzer now requires and
records:

- exact direct call instruction(s) whose Ghidra `flows` include
  `0x007155e9`;
- structured p-code `CALL` at those same instructions;
- exact cross-check against the call count already frozen by the ownership
  frontier;
- simple x86 register-relative memory operands;
- Ghidra `LOAD`/`STORE` presence for those instructions;
- base register plus displacement;
- same-instruction references to relevant heuristic vtable addresses;
- vtable-address `STORE` candidates;
- syntactic same-base overlap between a vtable-address store and other
  register-relative accesses.

The same instruction inventory is retained for the auxiliary lifecycle and
alternate-dispatch targets.

## Run

First produce the ownership/lifecycle frontier and its target list:

```bash
python3 tools/ghidra/build_vehicle_ownership_lifecycle_frontier.py \
  out/shift_ghidra_database \
  out/vehicle_upper_direct_contract.json \
  out/vehicle_indirect_dispatch_frontier.json \
  --json-out out/vehicle_ownership_lifecycle_frontier.json \
  --targets-out out/vehicle_ownership_lifecycle_targets.txt
```

Export exact instructions and p-code for those targets:

```bash
mapfile -t TARGETS < out/vehicle_ownership_lifecycle_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  "${TARGETS[@]}"
```

Then join the instruction evidence:

```bash
python3 tools/ghidra/analyze_vehicle_ownership_instruction_evidence.py \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_ownership_lifecycle_frontier.json \
  --json-out out/vehicle_ownership_instruction_evidence.json
```

For a strict audit that rejects complex/unparsed x86 memory operands:

```bash
python3 tools/ghidra/analyze_vehicle_ownership_instruction_evidence.py \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_ownership_lifecycle_frontier.json \
  --json-out out/vehicle_ownership_instruction_evidence.json \
  --fail-on-unparsed-memory
```

## Exact callsite gate

The analyzer does not accept a textual `CALL` alone.  A callsite into
`FUN_007155e9` must satisfy both:

```text
instruction.flows contains 0x007155e9
AND
structured p-code contains CALL
```

The resulting count must equal `direct_call_count_to_upper` from the previous
frontier.  Any drift aborts the analysis.

This prevents a stale or partial instruction slice from silently changing the
static update topology.

## Register-relative LOAD/STORE evidence

Only simple 32-bit x86 shapes are grouped automatically:

```text
[ECX]
[ECX + 0x20]
[ESI - 0x10]
```

Each row records:

```text
base_register
+ displacement
+ LOAD / STORE / read-write classification
+ exact instruction address
+ exact instruction text
+ p-code opcodes
```

Complex addressing such as:

```text
[ESI + EDX*4 + 0x20]
```

is preserved as an explicit blocker instead of being simplified heuristically.

## Vtable-address STORE candidates

A stronger but still non-semantic shape is recorded when one instruction:

1. has an exact Ghidra reference to a vtable address already present in the
   ownership frontier; and
2. contains p-code `STORE`.

That is reported as a vtable-address STORE candidate.  It does **not** by itself
prove:

- a vptr field;
- a constructor;
- a destructor;
- class identity;
- subobject offset;
- object ownership.

The destination register+displacement remains syntactic until the pointer is
proven.

## Same-base overlap

When the same function contains both:

- a vtable-address STORE through base register `R`; and
- other p-code-backed memory accesses through the same textual base register
  `R`;

the analyzer emits:

```text
syntactic-same-base-vtable-store-and-memory-access-overlap
```

This is intentionally `ambiguous` evidence.  Register-name reuse does not prove
pointer aliasing across instructions, blocks, or calls.

The overlap only narrows the next pointer-provenance task: prove whether that
base register carries one stable object identity and whether the value reaching
the direct call to `FUN_007155e9` aliases it.

## Remaining blockers

The generated report keeps these blockers explicit:

1. **receiver-pointer-provenance** — identify and trace the receiver/value at
   each direct call into `FUN_007155e9`;
2. **vptr-object-alias** — prove that a vtable-address STORE destination aliases
   that same object;
3. **field-base-object-identity** — prove that repeated textual base registers
   carry the same pointer where required;
4. **complex-memory-operands** — handle any indexed/complex addressing without
   inventing a simplified field offset.

Only after those are independently closed can read/write offsets become object
layout fields or lifecycle roles become semantic contracts.

## Evidence boundary

Promoted by this layer:

- exact direct call flows plus `CALL` p-code;
- exact simple register-relative operand syntax;
- exact `LOAD`/`STORE` presence from structured p-code;
- exact same-instruction references to already selected heuristic vtable
  addresses.

Not promoted:

- `ECX == this`;
- any base register == vehicle/BODY/manager object;
- pointer aliasing from equal register names;
- vtable STORE == vptr initialization;
- constructor/destructor identity;
- owner identity;
- field semantic names;
- physical units;
- frame scheduling or cadence.
