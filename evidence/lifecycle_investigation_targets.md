# SHIFT lifecycle investigation targets

`tools/ghidra/build_lifecycle_investigation_targets.py` turns the
`lifecycle-investigation-ready` rows from `SHIFT-CLASS-EVIDENCE-SCORECARD/1`
into compact one-hop Ghidra slices.

## Purpose

The scorecard identifies classes whose structure, registration identity,
initializer candidate and factory-to-initializer edge are independently backed.
The next task is no longer broad class discovery: it is function-level lifetime
analysis around those known anchors.

The target builder extracts, for both the initializer candidate and the class
registration function:

- Ghidra function metadata and mnemonic fingerprint;
- defined strings referenced by the function;
- all immediate incoming direct calls;
- all immediate outgoing direct calls.

Only direct callgraph edges are included. Computed/indirect calls remain outside
this first slice.

## Run

```bash
python3 tools/ghidra/build_lifecycle_investigation_targets.py \
  out/class_evidence/class_evidence_scorecard.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/lifecycle_targets.json
```

Use repeated `--prefix` filters or `--top` to reduce the generated workset.
The tool exits non-zero when a scorecard target cannot be resolved back to both
functions in the supplied Ghidra export.

## Interpretation

A complete target slice means only that the two already-proven anchors can be
resolved in the Ghidra database and their immediate static context was captured.
It does not prove that:

- the initializer candidate is a C++ constructor;
- an incoming caller is an allocator or factory owner;
- any outgoing call is a base constructor;
- a neighboring function is a destructor;
- virtual method meanings are known.

Those identities require the next pass over assignments, vtable transitions,
allocation/deallocation sites and call ordering. The target artifact exists to
make that pass small and reproducible instead of manually searching the full
41k-function / 200k-edge export.
