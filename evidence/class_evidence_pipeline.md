# SHIFT class evidence pipeline

`tools/shift_live_dump/build_class_evidence_pipeline.py` runs the current
class-centric static evidence workflow in one command. It does not collapse the
individual layers into one opaque result; every intermediate artifact remains
available for audit.

## Run

```bash
python3 tools/shift_live_dump/build_class_evidence_pipeline.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --ghidra-export out/shift_ghidra_database \
  --out out/class_evidence
```

Optional `--fail-on-ghidra-mismatch` makes the command return non-zero when the
Ghidra registration cross-check or a factory-to-initializer call cross-check
contains a mismatch, or when a lifecycle-ready scorecard row cannot be resolved
back to both expected functions in the same Ghidra export. The default is
report-only because a mismatch is evidence to inspect, not something the
pipeline should silently repair.

## Artifacts

The output directory contains:

- `class_manifest.json` — `SHIFT-CLASS-MANIFEST/1`, including independent
  Ghidra registration checks;
- `factory_initializer_links.json` —
  `SHIFT-FACTORY-INITIALIZER-LINKS/1`;
- `create_wrapper_evidence.json` —
  `SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1`, preserving the immediate
  preinitializer helper, its raw/literal arguments and local-value flow into the
  initializer, plus recurring-helper aggregates;
- `class_audit.json` — `SHIFT-CLASS-DECOMPILATION-CANDIDATES/1`, with
  initializer annotations;
- `class_evidence_scorecard.json` — `SHIFT-CLASS-EVIDENCE-SCORECARD/1`;
- `class_lifecycle_source_evidence.json` —
  `SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1`, containing literal source vtable
  writes, ancestor-vtable transition calls, initializer callers and simple
  `this + constant_offset` assignments for lifecycle-ready classes;
- `deleting_wrapper_evidence.json` —
  `SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1`, narrowing teardown candidates to
  wrappers that also call the configured release helper and recording whether
  source order plus a bit-0 guard match the deleting-wrapper shape;
- `lifecycle_investigation_targets.json` —
  `SHIFT.LifecycleInvestigationTargets/1`, containing one-hop Ghidra context
  around lifecycle-ready registration and initializer anchors;
- `pipeline_manifest.json` — `SHIFT-CLASS-EVIDENCE-PIPELINE/1`, a compact
  inventory and count summary for the whole run.

The pipeline manifest records registered/reflected/unique-vtable counts,
registration verification and mismatch counts, factory/initializer link counts,
create-wrapper/value-flow counts and distinct predecessor helpers,
structural-ready count, lifecycle-investigation-ready count, source lifecycle
completion/base-transition/teardown-candidate counts, deleting-wrapper candidate
and confirmed-shape counts, lifecycle target slice completeness, scorecard tiers
and next-evidence blocker totals.

## Evidence boundary

The pipeline is orchestration only. It preserves the same boundaries as the
underlying tools:

- a unique PE vtable remains class-identity/layout evidence;
- a registration string/callgraph match remains registration evidence;
- a factory call to a unique-vtable writer remains an initializer link;
- an immediate helper whose returned local flows into the initializer is a
  create-wrapper observation, not automatic proof that the helper allocates
  memory or that a literal argument is object size;
- a literal initializer vtable write and call to an ancestor-vtable writer are
  source lifecycle observations, not automatic constructor semantics;
- a non-initializer function which writes the class vtable and calls an
  ancestor-vtable writer remains a teardown-transition candidate, not an
  automatically named destructor;
- a teardown call followed by the configured release helper under a bit-0 flag
  is recorded as a deleting-wrapper shape, not automatically renamed as a C++
  deleting destructor;
- `lifecycle-investigation-ready` selects good targets for the next reverse-
  engineering pass but does not prove C++ constructor semantics, ownership,
  destructor order or gameplay behavior;
- a complete lifecycle target slice only proves that the already-selected
  registration and initializer anchors resolve in the same Ghidra export and
  that their immediate direct-call/string context was captured.

This separation is intentional: the pipeline is allowed to make evidence easier
to consume, but not stronger than the observations it joins.
