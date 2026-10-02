# Ghidra class-registration discovery

The headless Ghidra database contains enough direct call/string evidence to
identify the repeated SHIFT class-registration stub shape without relying on the
exporter's heuristic `constructors.jsonl`, `vtables.json`, or `factories.jsonl`
layers.

## Direct registration shape

`tools/ghidra/discover_class_registrations.py` requires all four direct calls
from one function:

- `FUN_00631740`
- `FUN_00630fe0`
- `FUN_006310c0`
- `_atexit` at `0x00900fb3`

Exact string xrefs from the same function are then attached to the candidate.
A single string is reported as `single_string_name`, but the tool does not turn
that string into a constructor/runtime-method name.

The output format is `SHIFT.GhidraClassRegistrationDiscovery/1`.

## Why this is separate from constructor discovery

The current generic constructor heuristic is intentionally not used here. Two
already source-proven track/path constructors illustrate the problem:

- `FUN_006cfe70` (`AISegmentPath`)
- `FUN_006cc900` (`AIPolylinePath`)

Neither appears in `constructors.jsonl`, while the direct Ghidra call graph
shows `FUN_006d8490` calling both (`0x006d84b6 -> 0x006cfe70` and
`0x006d84db -> 0x006cc900`). The source verifier independently establishes the
corresponding RTTI-to-constructor links. Therefore absence from the heuristic
constructor set must not be interpreted as negative constructor evidence.

## Class-manifest reverse cross-check

Pass a `SHIFT-CLASS-MANIFEST/1` report with `--class-manifest` to compare the
source/PE-derived registry against Ghidra in the reverse direction. Each class
row is checked for:

1. a normalized registration-function address;
2. a Ghidra candidate at that address with the full registration call shape;
3. an exact class-name string xref from that function.

The report keeps separate counts for verified classes, missing Ghidra
candidates, exact-name mismatches, and extra Ghidra candidates absent from the
source manifest. A mismatch is preserved as a mismatch; the tool never replaces
the source class identity with a string inferred from Ghidra.

## Fingerprints

Every discovered stub keeps its `mnemonic_sha256`. This lets later passes group
structurally identical registration functions while retaining the stronger
operand-aware direct-call requirement. Fingerprint equality alone is not used
to discover or name a class.

## Scope

This artifact proves registration-shape agreement between independent source/PE
and Ghidra views. It does not prove constructors, allocation ownership, object
lifetime, factory semantics, or vtable identity. Those require separate
call-site, vtable-write, allocation, or runtime evidence.
