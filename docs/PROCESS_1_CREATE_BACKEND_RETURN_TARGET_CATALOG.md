# Process 1 — create-backend return target catalog

`SHIFT.VehicleCreateBackendReturnOriginFrontier/1` narrows the create-side memory
chain to a finite set of exact inner targets.  Those targets are machine origins
of backend return values or exact external tail transfers; they are not yet
semantic allocator functions.

This stage joins that finite address set to the saved full Ghidra corpus without
running the original game:

```text
backend return-origin frontier
→ functions.jsonl
→ direct callgraph context
→ exact string xrefs
→ instruction-export worklist
```

Tool:

```text
tools/ghidra/build_vehicle_create_backend_return_target_catalog.py
```

Output:

```text
SHIFT.VehicleCreateBackendReturnTargetCatalog/1
```

## Usage

```bash
python3 tools/ghidra/build_vehicle_create_backend_return_target_catalog.py \
  out/vehicle_create_backend_return_frontier.json \
  out/shift_ghidra_database \
  --json-out out/vehicle_create_backend_return_target_catalog.json \
  --targets-out out/vehicle_create_backend_return_targets.txt
```

The generated target file can be passed directly to the existing targeted
instruction exporter:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_create_backend_return_target_instructions.jsonl \
  $(cat out/vehicle_create_backend_return_targets.txt)
```

No target is selected by name similarity, address proximity, string frequency or
callgraph popularity.

## Frontier gate

The input must be:

```text
SHIFT.VehicleCreateBackendReturnOriginFrontier/1
```

and it must have:

```text
all_backend_machine_return_origins_resolved = true
```

`next_backend_return_targets` must be non-empty, unique, sorted and consistent
with `next_backend_return_target_count` when that count is present.

An unresolved frontier is rejected instead of being converted into a static
worklist.

## Function identity

Every target is looked up by exact numeric address in:

```text
functions.jsonl
```

The catalog records the existing Ghidra metadata without changing it:

```text
name
signature
calling_convention
parameters
external
size
mnemonic_sha256
```

A target absent from `functions.jsonl` remains cataloged with an explicit
blocker:

```text
target_absent_from_functions_jsonl
```

An external function remains cataloged but is not emitted to the local
instruction-export worklist:

```text
target_is_external_function
```

This distinction prevents the target-list materializer from inventing local
function bodies for imports or unresolved external symbols.

## Direct callgraph context

`callgraph.jsonl` contributes only edges with:

```text
indirect = false
```

For each target the report records:

```text
incoming_direct_calls
outgoing_direct_calls
```

Indirect edges are deliberately excluded.  A nearby indirect call is not treated
as a caller/callee identity for the target and is not used to infer return
semantics.

## Exact string xrefs

`strings_xrefs.jsonl` is joined through its exact `functions` identity.  Each
matching string record keeps:

```text
string_address
value
xrefs
```

The catalog also marks exact text matches for the already-known retail memory
diagnostics:

```text
Unable to allocate ... bytes of memory from the pool ...
Error freeing ... from pool ...
```

These booleans are discovery aids only:

```text
allocation_diagnostic_text_reference_present
free_diagnostic_text_reference_present
```

A target that references the allocation diagnostic is **not** promoted to a
function that returns an allocated pointer.  Diagnostic text proves a code path
is associated with an allocation failure/reporting context; it does not prove
the semantic role of the target's EAX return value.

## Instruction-export worklist

A target is emitted in:

```text
instruction_export_addresses
```

only when:

```text
present in functions.jsonl
and external != true
```

`--targets-out` writes exactly those addresses in frontier order.  No fallback,
renaming or substitution is applied.

This produces the next narrow input for `ShiftFunctionInstructionExporter`
without requiring a manually copied target list.

## Preserved vehicle context

The existing `vehicle_create_bridges` from the backend return-origin frontier are
carried forward unchanged.  This keeps the exact persistent vehicle pointer
source node and allocation-request context available to later joins without
claiming that the inner target return value is already the same object.

## Evidence boundary

Even a fully cataloged target with exact direct callers/callees and an allocation
diagnostic string reference leaves these statements false:

```text
returned_allocation_pointer_role_proven
allocator_abi_proven
operator_new_identity_proven
object_size_proven
constructor_semantics_proven
ownership_semantics_proven
same_runtime_object_as_vehicle_update_proven
```

The catalog answers only:

```text
which exact function should be inspected next,
what static function identity does it already have,
which exact direct callgraph edges touch it,
and which exact strings are already attributed to it.
```

The next semantic promotion requires instruction-level evidence from the emitted
worklist that connects a target's return value to a concrete allocation result,
or an independent source/static contract that proves the same physical return
role.  Until then the returned allocation-pointer role remains unknown.
