# SHIFT cross-checked method aliases

`tools/ghidra/build_crosschecked_method_aliases.py` promotes a deliberately small
set of exact Ghidra method-name candidates only when an independent reconstructed
runtime contract already identifies the same `FUN_*` boundary.

The output format is `SHIFT.CrosscheckedMethodAliases/1`.

## Why a second layer is required

`SHIFT.GhidraMethodNameAnchors/1` keeps exact strings such as
`MWL::Core::cPhysicsManager::GetAssetDatabase` as semantic-name candidates rather
than automatic renames. A debug/assert string can describe a nearby operation or
an inlined source method, so uniqueness inside one Ghidra function is valuable
but not sufficient by itself.

This layer requires two independent observations:

1. the Ghidra function has exactly one accepted fully-qualified method-name
   anchor and it exactly matches the curated alias;
2. an existing reconstructed runtime contract contains explicit function-identity
   markers for the same `FUN_*` boundary.

## Current promoted set

### `FUN_00710870`

Ghidra candidate:

```text
MWL::Core::cPhysicsManager::GetAssetDatabase
```

Independent contract:

```text
src/physics/physics_system_runtime.py
```

That runtime contract already records `FUN_00710870` as the physics asset
`database_getter` and uses it in the recovered PhysicsTweaker load boundary.
The exact method-name anchor therefore corroborates the full semantic alias
without changing the already reconstructed behavior.

### `FUN_00714560`

Ghidra candidate:

```text
MWL::Core::PhysicsParticipantManager::ChangeRaceMode
```

Independent contract:

```text
src/physics/physics_participant_manager_event_runtime.py
```

The runtime contract already proves that opcode `0x20` is dispatched to
`FUN_00714560(&DAT_00c109e0, event)` in `PhysicsParticipantManager.cpp` and that
the consumer updates the recovered manager state. The method-name anchor now
corroborates the source method identity `ChangeRaceMode`.

## Candidates deliberately not promoted here

The structured Ghidra export also contains exact candidates such as:

```text
MWL::Core::PhysicsAllocator::malloc
MWL::Core::PhysicsAllocator::free
```

Those names remain method-anchor candidates in this layer because the repository
does not yet contain an independent reconstructed runtime contract that identifies
`FUN_0079cd90` / `FUN_0079ce30` as complete method boundaries. The exact strings
are strong leads, but this cross-check tool does not weaken its promotion rule to
include them.

## Run

First discover exact method-name anchors from the structured Ghidra export:

```bash
python3 tools/ghidra/discover_method_name_anchors.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_method_name_anchors.json
```

Then cross-check the curated candidates against the current repository contracts:

```bash
python3 tools/ghidra/build_crosschecked_method_aliases.py \
  out/ghidra_method_name_anchors.json \
  --json-out out/crosschecked_method_aliases.json \
  --fail-on-mismatch
```

The report includes SHA-256 identities for every runtime contract file used in
promotion so the alias evidence can be audited against the exact repository
state that supplied the independent cross-check.

## Evidence boundary

A promoted row establishes a corroborated semantic function alias: exact unique
retail method-name text and an independently reconstructed contract agree on the
same function boundary.

It does **not** prove:

- parameter names or parameter meanings;
- return-value semantics;
- ownership/lifetime policy;
- that every branch in the function implements only the named source method;
- runtime execution on a particular frame/event/path.

Ambiguous method anchors, wrong exact names, missing runtime files or missing
contract identity markers fail closed and remain unpromoted.
