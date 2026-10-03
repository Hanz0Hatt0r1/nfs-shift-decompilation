# Proven-subsystem Ghidra callgraph frontier

`tools/ghidra/build_proven_callgraph_frontier.py` expands the already established
subsystem evidence slices into a review queue of anonymous direct-callgraph
neighbours. The output format is `SHIFT.GhidraProvenCallgraphFrontier/1`.

This closes a target-selection gap in the earlier method-name frontier. A useful
physics/BODY scheduler, state writer or construction helper may still be named
only `FUN_*` and therefore have no exact `MWL::...::Method` string to enter
`SHIFT.GhidraSubsystemMethodFrontier/1`.

## Evidence roots

The tool reuses only addresses already present in the proven subsystem slices
built by `build_subsystem_manifests.py` and `_subsystem_slice_addresses()`:

- promoted semantic aliases;
- promoted class registrations;
- endpoints of direct call edges already attached to those manifests.

The default roots are `physics` and `vehicle`. No new `BODY` subsystem is
invented: BODY identity remains a separate pointer/layout question.

## Direct-callgraph expansion

The structured `callgraph.jsonl` is treated as an undirected graph **only for
shortest-distance target selection**. The original directed edges are retained
on every candidate.

By default the report includes functions within two direct-call hops of the
selected proven slices. Each candidate preserves:

- shortest distance from each connected selected subsystem;
- exact candidate -> proven-slice calls, sorted by call instruction address;
- exact proven-slice -> candidate calls;
- adjacent proven slice addresses;
- direct incoming/outgoing counts;
- unresolved indirect-call sites in the candidate;
- function metadata from `functions.jsonl` when present.

A candidate that directly calls two or more distinct proven-slice functions is
marked `multi_anchor_caller_candidate=true`. This makes it a high-priority
orchestration/update-order target, but it does **not** prove that the function is
a physics update loop or even a member of that subsystem.

## Indirect-call blockers

Computed calls are never silently discarded. Any unresolved indirect call in an
observed root/frontier function is emitted in `indirect_blockers` with the exact
instruction address. The target remains unknown until a separate vtable,
pointer, switch or decompiler proof resolves it.

## Generate a physics/vehicle frontier

```bash
python3 tools/ghidra/build_proven_callgraph_frontier.py \
  out/shift_ghidra_database \
  --subsystem physics \
  --subsystem vehicle \
  --max-depth 2 \
  --json-out out/physics_vehicle_callgraph_frontier.json \
  --targets-out out/physics_vehicle_instruction_targets.txt
```

`instruction_export_addresses` and the optional targets file are ordered for
static follow-up. Depth-one functions come first, then direct callers touching
multiple proven slice members, then candidates with more proven adjacency.
External functions are retained in the audit frontier but excluded from the
instruction-export list.

The addresses can then be passed to the targeted Ghidra exporter. For example:

```bash
mapfile -t TARGETS < out/physics_vehicle_instruction_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/physics_vehicle_frontier_instructions.jsonl \
  "${TARGETS[@]}"
```

No game execution or runtime capture is involved.

## Evidence boundary

Frontier membership proves only direct static callgraph proximity to an already
established evidence slice. It does not prove:

- subsystem membership;
- update-loop identity;
- constructor/destructor identity;
- virtual-call targets;
- BODY/vehicle/wheel pointer provenance;
- object layout or field meaning;
- ownership or lifetime semantics;
- persistent state mutation.

Those remain explicit follow-up questions for instruction/p-code, xref, vtable,
layout and allocation evidence.
