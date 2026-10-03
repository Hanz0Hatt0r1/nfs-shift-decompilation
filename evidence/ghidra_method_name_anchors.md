# Ghidra exact method-name string anchors

`tools/ghidra/discover_method_name_anchors.py` extracts a conservative semantic
naming layer from the direct `functions.jsonl` + `strings_xrefs.jsonl` datasets.

The output format is `SHIFT.GhidraMethodNameAnchors/1`.

## Motivation

Retail SHIFT contains diagnostic/assert strings that spell fully-qualified
methods. Examples already observed in the structured Ghidra export include:

- `MWL::Core::cPhysicsManager::GetAssetDatabase` in `FUN_00710870`;
- `MWL::Core::PhysicsAllocator::malloc` in `FUN_0079cd90`;
- `MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers`
  in `FUN_00854e70`.

These strings are much stronger semantic anchors than generic prose such as
`Physics Manager`, but they still need careful treatment because assert/debug
text can name a logical operation inside a larger function.

## Conservative filter

A string is considered only when it has an exact compact C++-style shape:

```text
MWL::<scope>::<member>
```

with at least two `::` separators. Paths, format strings, whitespace-bearing
prose and decorated RTTI names are excluded.

The string must also resolve through `strings_xrefs.jsonl` to a function present
in the same `functions.jsonl` inventory.

## Unique versus ambiguous

A function gets `unique-method-name-anchor-candidate` only when all of the
following hold:

1. the method string resolves to exactly one known function;
2. that function contains exactly one distinct accepted method-name string.

If one function contains multiple accepted method names, the tool emits
`ambiguous-method-name-anchors` instead.

This distinction is important for functions such as a physics-event routine that
contains several strings like `SetObjectType`, `SetObjectID`, `SetObjectMatID`,
etc. Such a function clearly participates in that API surface, but selecting one
of those strings as its function name would be arbitrary.

Strings shared by multiple functions, and strings whose containing-function
reference is absent from the function inventory, also never create a unique
candidate.

## Run

```bash
python3 tools/ghidra/discover_method_name_anchors.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_method_name_anchors.json
```

The report retains original function address/name, calling convention, size,
mnemonic fingerprint, exact anchor values and string addresses so every
candidate can be audited back to the original Ghidra export.

## Evidence boundary

A unique method-name anchor is a high-value **semantic-name candidate**, not an
automatic function rename. It proves that the exact fully-qualified method text
is referenced inside that known function boundary. It does not by itself prove:

- that the entire recovered function corresponds exactly to the named source
  method;
- that an inlined helper or neighboring operation is absent;
- parameter or return-value semantics;
- ownership/lifetime behavior;
- runtime execution on any particular path.

Promotion to a stable semantic alias should use another independent observation
where possible: call shape, source/decompiler body, vtable slot, factory usage,
known object layout, or runtime evidence.
