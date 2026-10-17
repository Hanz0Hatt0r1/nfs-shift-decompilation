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

## Bulk function recovery index

`tools/ghidra/build_function_recovery_index.py` preserves the full unique-name
candidate set and joins direct callers of the Participants Manager getter into
one portable evidence artifact:

```bash
python tools/ghidra/build_function_recovery_index.py \
  /path/to/SHIFT.exe out/shift_ghidra_database \
  --output evidence/ghidra_function_recovery_index.json
```

For the hash-locked PC retail 1.02 export, the index contains 338 unique method
name candidates and 2 ambiguous functions. It also inventories 241 functions
with 393 direct callgraph edges to `FUN_00489ad0`; 22 callers have a unique
method-name candidate. These names remain candidates and are not applied as
Ghidra renames. The output records hashes for the executable and every source
export used to build it.

## P1.3B direct-callee body recovery

`tools/ghidra/build_p1b_helper_return_ghidra_recovery.py` cross-checks direct
`objdump` calls whose target bytes were absent from the linear instruction
index against the exact Ghidra callgraph. Its hash-locked batch report is
[`evidence/p1b_helper_return_ghidra_target_recovery.json`](p1b_helper_return_ghidra_target_recovery.json).

For this retail build, Ghidra confirms 575 of 669 unresolved direct callsites,
covering 170 exact callee function entries. Their Ghidra instruction/P-code
bodies contain 13,261 instructions; P-code is present for each. This adds 166
functions to the earlier 559-function targeted export. A separate inventory
pass also exports 20 exact Ghidra function entries among the unmatched targets;
their 1,225 instruction/P-code records remain callsite-unconfirmed, and 19 are
new to the earlier batch. Together the batches cover 744 unique function
bodies and 110,624 unique instructions (P-code is present for 110,440). The raw
instruction bodies stay outside Git; the evidence records their hashes and
function-level fingerprints.

The bounded helper-return scan found no `entry argument + 0x374` returns among
the 170 callgraph-confirmed functions or the 20 inventory-only candidates. It
stopped at 111 control-flow boundaries, 45 nested calls, 6 unsupported stack
adjustments, and 8 returns in the confirmed set; the inventory-only set stopped
at 11 control-flow boundaries, 8 nested calls, and 1 unsupported stack
adjustment. The 94 unmatched callsites and 52 target addresses still lack exact
callgraph confirmation; 32 of those targets are not Ghidra function entries.
This batch does not establish receiver identity or close P1.3B.

## P1.3B orphan wrapper function recovery

The follow-up
[`docs/PROCESS_1B_ORPHAN_WRAPPER_FUNCTION_RECOVERY.md`](../docs/PROCESS_1B_ORPHAN_WRAPPER_FUNCTION_RECOVERY.md)
reconciles the 94 remaining sites against exact Ghidra instructions and
references: 60 are real direct calls without caller-function ownership, and
34 are not instruction starts. Fifteen caller functions met the strict
contiguous call/return plus entry-reference screen and were restored in an
isolated project copy. Their 137 instruction/P-code rows bring this targeted
body corpus to 759 unique functions, 110,761 instructions, and 110,577 P-code
rows. The original Ghidra project and semantic names are unchanged.

## P1.3B address-taken orphan function recovery

The follow-up
[`docs/PROCESS_1B_ADDRESS_TAKEN_ORPHAN_FUNCTION_RECOVERY.md`](../docs/PROCESS_1B_ADDRESS_TAKEN_ORPHAN_FUNCTION_RECOVERY.md)
uses exact data references and bounded Ghidra control-flow evidence to restore
three more unowned bodies in the isolated project copy. One 703-instruction
body assigns two orphan caller sites; a six-instruction address-taken body
assigns one more. A separate two-instruction body ends in an unresolved direct
tail transfer and receives no semantic claim. This brings the combined body
corpus to 762 functions, 111,472 instructions and 111,288 P-code rows, with
42 of the 60 exact orphan callsites still awaiting caller boundaries. The
hash-pinned report is
[`evidence/p1b_address_taken_orphan_function_recovery.json`](p1b_address_taken_orphan_function_recovery.json).

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
