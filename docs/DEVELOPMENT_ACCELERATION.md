# Development acceleration workflow

This layer reduces repeated research/PR mechanics without weakening any semantic gate.

## 1. One-time Ghidra export on the workstation

The repository already contains the authoritative headless exporter. From the repository root on Manjaro:

```bash
export GHIDRA_HOME="$HOME/ghidra_11.4_PUBLIC"
mkdir -p out/shift_ghidra_database
./tools/ghidra/run_shift_export.sh \
  "$HOME/ghidra-projects" \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database
```

If your project path/name differs, substitute those two arguments. The command uses the analyzed project with `-noanalysis`; it does not redo the whole analysis pass.

Validate and build the existing semantic index:

```bash
python3 tools/ghidra/validate_shift_export.py out/shift_ghidra_database
python3 tools/ghidra/build_static_semantic_index.py \
  out/shift_ghidra_database \
  out/ghidra_static_semantic_index \
  --fail-on-mismatch
```

## 2. Build the fast SQLite query index

```bash
python3 tools/ghidra/build_shift_sqlite_index.py \
  out/shift_ghidra_database \
  out/shift_ghidra.sqlite
```

The current format is `SHIFT.GhidraSQLiteIndex/2`. Rebuild an older database after pulling this version: v2 fixes exporter-native callgraph indexing and stores both symbolic names and exact addresses.

Examples:

```bash
sqlite3 out/shift_ghidra.sqlite \
  "select callsite,caller,caller_address from calls where callee='FUN_00755950';"

sqlite3 out/shift_ghidra.sqlite \
  "select caller,callee,callee_address,callsite from calls where caller='FUN_0076b280';"

sqlite3 out/shift_ghidra.sqlite \
  "select caller,callee,callsite from calls where callee_address='0x0057f620';"

sqlite3 out/shift_ghidra.sqlite \
  "select value,address,containing_function from strings where value like '%Wedge%';"
```

`caller` / `callee` are the exported symbolic names when available. `caller_address` / `callee_address` preserve the exact function addresses, and `indirect` records the exporter's indirect-call flag.

The SQLite database is an operational index only. A matching row is not semantic proof.

## 3. Start a new evidence slice without hand-writing boilerplate

```bash
python3 tools/research/scaffold_proof.py \
  --contract SHIFT.ExampleProof/1 \
  --title "Process 1 — example proof" \
  --blocker "Need exact selected-root writer provenance." \
  --next-step "Trace the exact writer and preserve fail-closed gates." \
  --slug process1_example_proof
```

This creates an evidence JSON, document, and regression test. The scaffold deliberately starts with `ready=false`, `proof_complete=false`, retail control provenance false, and provider count 7. Promote those only after exact proof exists.

## 4. Blocker ownership

`coordination/decomp_blockers.json` is the machine-readable ownership queue. Before starting a parallel research process:

```bash
python3 -m json.tool coordination/decomp_blockers.json >/dev/null
```

Choose a different `owner`/child blocker instead of launching multiple processes at the same target. Update the graph when a blocker is closed or transferred.

Recommended stable split:

```text
Process 1A -> P1.1 contact_response/provider closure
Process 1B -> P1.3 vehicle/control producer provenance
Process 1D -> P1.4 camera provenance
Process 2  -> native physics/runtime consumers
Process 3  -> resources/scene/render/bootstrap
```

## 5. Fast evidence CI

`.github/workflows/evidence-fast.yml` runs JSON validation plus focused evidence/tool regressions immediately on evidence-oriented PRs. It is additional fast feedback only; it does not replace the repository's existing full CI/live-dump/Vulkan merge gates.

## 6. Useful local loop

After pulling a new branch:

```bash
python3 -m pytest -q tests/test_development_acceleration_tools.py
python3 -m json.tool coordination/decomp_blockers.json >/dev/null
```

For a new Process 1 proof, run its focused test directly before pushing:

```bash
python3 -m pytest -q tests/test_process1_<proof>.py
```

## Evidence rules retained

- PC retail remains the semantic authority.
- Matching numeric offsets do not prove object identity.
- Xbox evidence is navigation/corroboration only.
- Do not invent class or physical/control semantics.
- Provider count changes only when an actual runtime boundary is removed.
- The SQLite index, blocker graph, and scaffold generator are workflow accelerators, not proof sources.
