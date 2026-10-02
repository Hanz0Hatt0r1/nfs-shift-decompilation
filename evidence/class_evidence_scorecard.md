# SHIFT class evidence scorecard

`tools/shift_live_dump/build_class_evidence_scorecard.py` joins the existing
structural class audit with the optional Ghidra-crosschecked class manifest. It
is a workflow/prioritization artifact, not a confidence percentage.

## Inputs

The primary input is `SHIFT-CLASS-DECOMPILATION-CANDIDATES/1`, normally built
with optional factory/initializer links. An optional `SHIFT-CLASS-MANIFEST/1`
produced with `--ghidra-export` supplies the independent registration check.
The join is by RTTI descriptor, not by class-name similarity.

When both inputs carry source/executable hashes, mismatched identities are
rejected rather than merged.

Example:

```bash
python3 tools/shift_live_dump/build_shift_class_manifest.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/shift_class_manifest.json

python3 tools/shift_live_dump/extract_factory_initializer_links.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/factory_initializer_links.json

python3 tools/shift_live_dump/audit_shift_class_candidates.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --initializer-links out/factory_initializer_links.json \
  --json-out out/class_audit.json

python3 tools/shift_live_dump/build_class_evidence_scorecard.py \
  out/class_audit.json \
  --class-manifest out/shift_class_manifest.json \
  --json-out out/class_evidence_scorecard.json \
  --csv-out out/class_evidence_scorecard.csv
```

## Tiers

The scorecard deliberately uses named evidence tiers instead of a weighted
numeric score:

- `structural-blocked` — one or more original structural audit gates fail;
- `structural-ready` — source/PE layout evidence is ready, but Ghidra
  registration is absent or mismatched;
- `registration-crosschecked` — structural evidence plus independent Ghidra
  registration identity are both verified;
- `initializer-linked` — the above plus one unambiguous source/PE initializer
  candidate, but its factory call has not yet been independently confirmed by
  Ghidra;
- `lifecycle-investigation-ready` — structure and registration are verified,
  exactly one initializer candidate remains, and the factory-to-initializer
  call edge is independently present in the Ghidra call graph.

`lifecycle-investigation-ready` is the preferred pool for constructor/default
state/destructor/factory-lifetime analysis. It does **not** mean the initializer
is already proven to be a C++ constructor.

## Blockers

Each row keeps `next_evidence_blockers` so the missing next proof is explicit:

- `structural_not_ready`;
- `registration_not_checked` / `registration_mismatch`;
- `no_initializer_link` / `ambiguous_initializer`;
- `initializer_call_not_checked` / `initializer_call_mismatch`.

This keeps evidence axes independent. A large reflected layout cannot make up
for a registration mismatch, and a confirmed factory call cannot make a class
with unresolved offsets structurally ready.

## Scope

The scorecard does not prove object allocation, ownership, complete object
size, constructor semantics, destructor order, virtual method identities or
gameplay behavior. Its purpose is to select the next functions where those
questions can be investigated with the least remaining ambiguity.
