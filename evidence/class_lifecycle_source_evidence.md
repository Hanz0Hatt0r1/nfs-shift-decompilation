# SHIFT class lifecycle source evidence

`tools/shift_live_dump/extract_class_lifecycle_source_evidence.py` adds a
source-level lifecycle investigation layer after the class evidence scorecard.
It is intentionally narrower than constructor/destructor recovery: the output
contains direct observations and named candidates, not automatic C++ semantic
renames.

## Inputs

The extractor consumes:

- recovered `SHIFT.exe.c`;
- `SHIFT-CLASS-MANIFEST/1`, normally produced with the retail PE and Ghidra
  registration cross-check;
- `SHIFT-CLASS-EVIDENCE-SCORECARD/1`;
- optionally the Ghidra export for independent direct-call confirmation.

Only scorecard rows in `lifecycle-investigation-ready` are inspected. Source and
executable identities in the manifest and scorecard must agree when both are
present.

## Observations

For each selected class the extractor records:

- the class's unique PE-backed vtable and its `PTR_FUN_*` source symbol;
- the nearest ancestor in the recovered ancestry chain that also has a unique
  vtable;
- whether the scorecard's unambiguous initializer candidate literally writes
  the class vtable;
- direct calls from that initializer to functions which literally write the
  nearest ancestor vtable;
- simple literal assignments to `this + constant_offset` in the initializer
  body, preserving the raw right-hand-side expression and statement;
- direct source callers of the initializer;
- every function that literally writes the class vtable;
- non-initializer functions which write the class vtable and directly call an
  ancestor-vtable writer. These are emitted as `teardown_transition_candidates`.

When `--ghidra-export` is supplied, every reported source call edge receives a
tri-state `ghidra_direct_call` cross-check.

## Calibration

The existing track/path evidence provides a known positive shape. The recovered
`AIPolylinePath` initializer `FUN_006cc900` writes `PTR_FUN_00afc678`. The
existing teardown source anchor `FUN_006cc390` writes the same concrete vtable
and then calls `FUN_006d0ef0`, the source-backed `AIPathObj` base transition.
`AISegmentPath` has the analogous established chain through `FUN_006ce660`.

Those anchors are useful calibration examples, but the generic extractor does
not hard-code them. It derives the same shape from class ancestry, unique
vtables and parsed source calls.

## Evidence boundary

The following are deliberately **not** claimed by this layer:

- an initializer candidate is not automatically renamed as a C++ constructor;
- a teardown-transition candidate is not automatically renamed as a destructor;
- initializer callers are not automatically allocation sites;
- a literal assignment does not establish the semantic meaning of the field;
- a call to an ancestor-vtable writer does not by itself prove full base-class
  construction/destruction ordering.

Promotion requires stronger lifetime evidence such as allocation/deallocation
sites, deleting-destructor shapes, virtual dispatch context, or corroborating
runtime observations. The purpose of this artifact is to reduce the next
investigation from tens of thousands of functions to a class-specific set of
direct source observations.

## Run

```bash
python3 tools/shift_live_dump/extract_class_lifecycle_source_evidence.py \
  /path/to/SHIFT.exe.c \
  --manifest out/class_evidence/class_manifest.json \
  --scorecard out/class_evidence/class_evidence_scorecard.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/class_lifecycle_source_evidence.json
```

The output format is `SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1`.
