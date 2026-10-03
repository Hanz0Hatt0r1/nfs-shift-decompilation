# SHIFT Ghidra evidence exporter

This directory contains a headless Ghidra exporter for producing a compact,
machine-readable evidence database directly from an analyzed `SHIFT.exe`
program. It complements, rather than replaces, the recovered `SHIFT.exe.c`
source export.

## Why this exists

Decompiler C loses or obscures some information that remains available in the
Ghidra program database: exact cross-references, defined raw data, function
metadata, computed control flow, function-pointer tables and the relationship
between code and strings. This exporter preserves those relationships for later
automated decompilation work.

The output deliberately distinguishes direct observations from heuristics.
`vtables.json`, `constructors.jsonl`, `switches.jsonl` and `factories.jsonl`
contain candidates, not assertions that a C++ class/factory/switch has been
fully proven.

## Requirements

- an installed Ghidra distribution;
- an existing Ghidra project containing an analyzed retail `SHIFT.exe`;
- Python 3 for post-export validation.

The current project evidence is based on the retail 1.02 executable. Keep the
binary identity from `binary.json` with every exported bundle.

## Run

```bash
GHIDRA_HOME="$HOME/ghidra_11.4_PUBLIC" \
  ./tools/ghidra/run_shift_export.sh \
  "$HOME/ghidra-projects" \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database
```

`run_shift_export.sh` uses `-process` and `-noanalysis`, so it reads the current
analysis database without starting another full auto-analysis pass.

If your program has a different Ghidra name, replace `SHIFT.exe` with the name
shown in the project tree.

The Java script can also be launched manually:

```bash
"$GHIDRA_HOME/support/analyzeHeadless" \
  "$HOME/ghidra-projects" shift \
  -process SHIFT.exe \
  -noanalysis \
  -scriptPath "$PWD/tools/ghidra" \
  -postScript ShiftEvidenceExporter.java "$PWD/out/shift_ghidra_database"
```

## Output

| File | Contents |
|---|---|
| `binary.json` | executable/program identity, architecture and memory blocks |
| `functions.jsonl` | function boundaries, signatures, parameters and mnemonic fingerprint |
| `callgraph.jsonl` | direct call edges plus unresolved computed calls |
| `vtables.json` | non-executable memory runs of 3+ pointers to functions; heuristic candidates |
| `constructors.jsonl` | functions referencing candidate vtables with instruction previews |
| `strings_xrefs.jsonl` | defined strings, code/data xrefs and containing functions |
| `globals.jsonl` | non-function labels in memory with data type and xref count |
| `static_tables.jsonl` | defined non-code table-like data plus raw bytes, capped at 4096 bytes per item |
| `switches.jsonl` | computed jump instructions and known flow destinations |
| `factories.jsonl` | functions combining string references with direct calls; heuristic candidates |
| `manifest.json` | format identifier, output inventory and record counts |

JSONL is used for large collections so downstream tools can stream the output
without loading the full database into memory.

## Validation

The runner automatically executes:

```bash
python3 tools/ghidra/validate_shift_export.py out/shift_ghidra_database
```

It checks that every expected file exists and that every JSON/JSONL record can
be parsed. It does not attempt to prove semantic correctness of heuristic
candidates.

## Semantic cross-check

After an export, run the direct-observation cross-check:

```bash
python3 tools/ghidra/analyze_shift_export.py \
  out/shift_ghidra_database \
  out/ghidra_crosscheck.json
```

The output format is `SHIFT.GhidraCrosscheckEvidence/1`. The analyzer currently
checks high-value renderer/physics anchors against exact function, callgraph and
string-xref data, and discovers the repeated RTTI registration-stub fingerprint.
It deliberately excludes `vtables.json` and `constructors.jsonl` from semantic
proof because those exporter layers are heuristic candidate sets.

The first retail result is summarized in
`evidence/ghidra_database_crosscheck.md`.

## Subsystem manifests

The next stage turns proven anchors into small machine-readable subsystem
slices:

```bash
python3 tools/ghidra/build_subsystem_manifests.py \
  out/shift_ghidra_database \
  out/shift_ghidra_subsystems
```

The builder writes `renderer.json`, `physics.json`, `vehicle.json`,
`scene_graph.json`, `ai.json` and an `index.json` containing promoted aliases.
Promotion requires exact retail string xrefs and, for renderer boundaries where
an independent call contract is already known, the expected direct call shape.

AI class registration functions are deliberately emitted as
`class-registration-stub` records rather than semantic function aliases. A class
string plus the common RTTI registration call pattern proves the registration
role, not a constructor or runtime method identity.

See `evidence/ghidra_subsystem_manifests.md` for the initial retail identities.

## Method-name anchors

Exact retail assert/debug strings sometimes spell a fully-qualified method name.
Inventory them without renaming functions:

```bash
python3 tools/ghidra/discover_method_name_anchors.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_method_name_anchors.json
```

`SHIFT.GhidraMethodNameAnchors/1` keeps unique and ambiguous functions separate.
A function containing exactly one conservative `MWL::...::Method` anchor is a
semantic-name candidate only; functions containing multiple distinct method
anchors stay ambiguous.

Cross-check those names against the already established subsystem slices:

```bash
python3 tools/ghidra/join_method_anchors_to_subsystems.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_subsystem_method_anchors.json
```

`SHIFT.GhidraSubsystemMethodAnchors/1` promotes a subsystem-specific candidate
only when a narrow namespace/class rule and independent one-hop subsystem slice
membership agree. Broad `MWL::Core::*` names are intentionally not classified.
See `evidence/ghidra_method_name_anchors.md` and
`evidence/ghidra_subsystem_method_anchors.md`.

## One-command static semantic index

Build all direct-observation static semantic layers together:

```bash
python3 tools/ghidra/build_static_semantic_index.py \
  out/shift_ghidra_database \
  out/ghidra_static_semantic_index \
  --fail-on-mismatch
```

The output directory contains:

```text
crosscheck.json
method_name_anchors.json
subsystem_method_anchors.json
subsystems/
    ai.json
    physics.json
    renderer.json
    scene_graph.json
    vehicle.json
    index.json
manifest.json
```

`manifest.json` uses `SHIFT.GhidraStaticSemanticIndex/1` and aggregates direct
anchor mismatches, promoted subsystem aliases/registrations, RTTI fingerprint
counts, unique/ambiguous method anchors and subsystem-crosschecked method-name
candidates. Program/MD5 identity is checked across the composed layers.

The orchestration still excludes heuristic `vtables.json`, `constructors.jsonl`
and `factories.jsonl` from semantic promotion. `--fail-on-mismatch` applies to
failed direct anchor/alias/registration checks; namespace-only and ambiguous
method-name observations remain explicit research targets rather than CI errors.

## Class-registration discovery

Discover the registry from the Ghidra side without the heuristic constructor or
factory candidate sets:

```bash
python3 tools/ghidra/discover_class_registrations.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_class_registrations.json
```

A candidate must directly call `FUN_00631740`, `FUN_00630fe0`,
`FUN_006310c0` and `_atexit`. Exact string xrefs and mnemonic fingerprints are
then attached to that call-shape candidate; fingerprint equality alone never
creates a class identity.

The discovery can be checked in the reverse direction against a generated
`SHIFT-CLASS-MANIFEST/1` report:

```bash
python3 tools/ghidra/discover_class_registrations.py \
  out/shift_ghidra_database \
  --class-manifest out/shift_class_manifest.json \
  --json-out out/ghidra_class_registration_crosscheck.json
```

The comparison keeps verified rows, missing Ghidra candidates, exact-name
mismatches and extra Ghidra candidates separate. It does not replace a source
class name when Ghidra disagrees. See
`evidence/ghidra_registration_discovery.md`.

## Evidence interpretation

The strongest datasets are `functions.jsonl`, `callgraph.jsonl`,
`strings_xrefs.jsonl`, `globals.jsonl` and `static_tables.jsonl`: they are direct
views of the analyzed Ghidra database.

The following are intentionally weaker:

- a vtable candidate is a contiguous run of at least three pointers to known
  functions in initialized, non-executable memory;
- a constructor candidate is currently a function that references one of those
  candidate tables;
- a switch candidate is a computed jump recognized in the listing;
- a factory candidate is a function that both references one or more defined
  strings and makes at least one direct call.

These datasets are intended to narrow the next reverse-engineering target. They
must be joined with disassembly, constructors/call sites, PE bytes or runtime
evidence before promoting a candidate to a recovered contract.
