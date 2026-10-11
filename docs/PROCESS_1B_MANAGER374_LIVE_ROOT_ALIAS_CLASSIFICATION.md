# Process 1B: live exact-root alias candidate classification

## Blocker

`SHIFT.P1B.Manager374RuntimeRootFrontier/2` reduces P1.3B manager-root provenance to three surviving classes after canonical program-internal creation/copy/call/return paths are closed:

- externally or unknown-origin initialized writable memory containing the exact live outer-root pointer;
- an unidentified opaque helper return synthesizing the exact root from unrelated input;
- an unrecognized runtime transform outside the bounded reconstruction classes.

`SHIFT.P1B.Manager374RuntimeExactRootAliasCapture/1` already turns the first class into exact runtime addresses for a supplied set of live snapshots. It intentionally stops before producer/owner classification. This change adds that missing normalization layer.

## Tool

`tools/shift_live_dump/classify_manager374_root_alias_candidates.py` consumes:

1. `analysis.json` from `analyze_manager374_root_aliases.py`;
2. Ghidra `binary.json` for the pinned retail PE memory map;
3. Ghidra `globals.jsonl` for exact-address navigation labels.

Output format:

```text
SHIFT.P1B.Manager374RuntimeRootAliasCandidateClassification/1
```

The tool pins the Ghidra program to:

```text
program      SHIFT.exe
MD5          705af8b420e5eb1e3834ac43d5533c6b
language     x86:LE:32:default
image base   0x00400000
pointer size 4
```

The semantic authority remains PC retail 1.02 SHA-256:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Classification

Each noncanonical exact-root hit is classified along two independent axes.

### Storage

- `retail-image-writable` — address falls inside a writable PE memory block from `binary.json`;
- `retail-image-nonwritable` — address falls inside another PE block;
- `heap` — live mapping classified as `[heap]`;
- `anonymous` — anonymous/bracketed writable mapping;
- `other-module` — module-backed mapping outside the retail PE blocks;
- `other` — everything else.

If `globals.jsonl` contains one or more exact labels at the candidate address, they are attached as navigation metadata with name, data type and xref count.

### Supplied-capture lifetime

The classifier validates candidate hit/root counts against the active snapshot set and emits:

- `intermittent-over-supplied-capture`;
- `persistent-over-supplied-capture`;
- `persistent-tracks-root-changes` when the same candidate address appears in every active snapshot and tracks every distinct root value while the root changes across the capture set.

`persistent-tracks-root-changes` is intentionally a prioritization class, not ownership proof. It identifies the strongest observed alias candidates for writer/owner recovery.

## Run

First produce live equality candidates:

```bash
python3 tools/shift_live_dump/analyze_manager374_root_aliases.py \
  out/shift-live-dump-watch \
  --out out/manager374_root_alias_analysis
```

Then classify them against the analyzed retail image:

```bash
python3 tools/shift_live_dump/classify_manager374_root_alias_candidates.py \
  out/manager374_root_alias_analysis/analysis.json \
  out/shift_ghidra_database/binary.json \
  out/shift_ghidra_database/globals.jsonl \
  --output out/manager374_root_alias_classification.json
```

## Gate effect

For any supplied capture set the classifier may establish only:

```text
supplied_capture_alias_candidates_classified = true
```

It may also report that persistent root-change trackers or exact retail-image globals were observed. Those are worklist facts, not semantic closures.

These remain fail-closed even when the candidate list is empty:

```text
external_or_unknown_origin_outer_alias_surface_complete = false
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete = false
unrecognized_runtime_transform_root_origin_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
global_manager_root_origin_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
external_provider_count = 7
```

A finite snapshot set cannot prove that a transient alias never existed before, after or between captures.

## Next

For every `persistent-tracks-root-changes` candidate and every `retail-image-writable` exact-global candidate:

1. recover the concrete writer/owner;
2. determine whether the storage is populated by canonical program lineage, an opaque helper, or an external/runtime source;
3. repeat captures around construction, steady-state and teardown;
4. preserve intermittent heap/anonymous hits as explicit unresolved runtime candidates until their producers are classified.

Only after this observed writable-memory class is exhausted should P1B spend another proof cycle on helper-returned root synthesis or unrecognized transforms. The final manager/HDVehicle identity and `0x004b86cf` slot2 adjudication remain fail-closed until all surviving origin/setter classes close.
