# Process 1 — returned-pointer instruction export runner

`SHIFT.VehicleReturnedAllocationPointerBoundary/1` leaves one precise unresolved
semantic requirement:

```text
returned allocation-pointer role
```

and carries the exact finite local-function worklist needed to investigate it:

```text
required_instruction_targets
```

This stage removes the remaining manual address-copy step between that boundary
and the existing targeted Ghidra exporter.

Tool:

```text
tools/ghidra/run_vehicle_returned_allocation_pointer_instruction_export.py
```

Output manifest:

```text
SHIFT.VehicleReturnedAllocationPointerInstructionExportRun/1
```

## Usage

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_vehicle_returned_allocation_pointer_instruction_export.py \
  out/vehicle_returned_allocation_pointer_boundary.json \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_returned_allocation_pointer_target_instructions.jsonl \
  --manifest-out out/vehicle_returned_allocation_pointer_instruction_export.json
```

To inspect the command without opening the Ghidra project:

```bash
python3 tools/ghidra/run_vehicle_returned_allocation_pointer_instruction_export.py \
  out/vehicle_returned_allocation_pointer_boundary.json \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_returned_allocation_pointer_target_instructions.jsonl \
  --dry-run \
  --manifest-out out/vehicle_returned_allocation_pointer_instruction_export.json
```

## Boundary validation

The runner accepts only:

```text
SHIFT.VehicleReturnedAllocationPointerBoundary/1
```

whose return role is still explicitly unresolved:

```text
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
```

and whose blockers still include:

```text
returned_allocation_pointer_semantic_role_not_proven
```

This matters because the instruction export is intended to investigate that
specific unresolved role.  If an upstream artifact already claims the role is
proven, this runner refuses to normalize or preserve that claim without a new
contract designed for the stronger evidence state.

## Exact target policy

`required_instruction_targets` must be:

- non-empty;
- valid exact addresses;
- unique;
- sorted;
- a subset of the boundary's exact `return_origin_targets`.

No target can be added because it has a similar name, a nearby address, a common
caller, an allocation diagnostic string or a plausible allocator role.

The exact target sequence is passed to:

```text
tools/ghidra/run_shift_function_instructions.sh
```

which in turn uses the existing read-only
`ShiftFunctionInstructionExporter.java` and validates the produced JSONL.

## Execution policy

The generated command is equivalent to:

```bash
bash tools/ghidra/run_shift_function_instructions.sh \
  <project-dir> \
  <project-name> \
  <program-name> \
  <output-jsonl> \
  <exact-target-1> ...
```

The underlying runner:

- opens the existing Ghidra project read-only;
- disables new analysis;
- exports only the explicitly supplied functions;
- validates that every requested target was emitted;
- never launches `SHIFT.exe`.

This is static program inspection, not runtime capture.

## Fail-closed behavior

The orchestration fails when:

- the boundary format is wrong;
- the semantic role is no longer `unknown`;
- the expected semantic blocker is missing;
- the target list is empty, duplicated, unsorted or outside the return-origin
  frontier;
- the underlying Ghidra runner is missing;
- Ghidra returns non-zero;
- Ghidra reports success but produces no output JSONL.

A failed export does not produce a successful manifest.

## Dry-run mode

`--dry-run` validates the full boundary and target list and emits the exact
command without invoking Ghidra.

The manifest uses:

```text
status = dry-run
return_code = null
```

Normal successful execution uses:

```text
status = completed
return_code = 0
```

## Evidence boundary

A successful instruction export still leaves:

```text
returned_allocation_pointer_role_proven = false
```

The export provides machine instructions and p-code for the finite target set.
It does not itself prove what their returned EAX values mean.

The next analyzer must inspect the resulting target bodies and require a
source/static-backed allocation-producing operation plus exact value continuity
to every relevant return path before promoting the returned pointer role.

Until that analysis succeeds, these remain false:

```text
allocator_abi_proven
operator_new_identity_proven
object_size_proven
constructor_semantics_proven
ownership_semantics_proven
same_runtime_object_as_vehicle_update_proven
```
