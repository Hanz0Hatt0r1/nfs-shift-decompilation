# Ghidra subsystem method frontier

`tools/ghidra/build_subsystem_method_frontier.py` identifies the next exact
method-name functions worth investigating around already proven subsystem
slices. The output format is `SHIFT.GhidraSubsystemMethodFrontier/1`.

This is a target-selection artifact, not a semantic promotion layer.

## Inputs

The builder composes only direct static evidence:

- the existing `SHIFT.GhidraSubsystemManifestIndex/1` subsystem slices;
- `SHIFT.GhidraSubsystemMethodAnchors/1` unique exact method-name candidates;
- direct, non-indirect edges from `callgraph.jsonl`.

A candidate is considered only when it already has a narrow namespace/class
assignment from the method-anchor join but is **not** already promoted into that
subsystem.

## One-hop frontier rule

A namespace-only candidate becomes a
`one-hop-subsystem-frontier-candidate` when either of these direct edges exists:

```text
candidate -> established subsystem slice
```

or

```text
established subsystem slice -> candidate
```

The report preserves every qualifying edge, its instruction address, direction
and the exact slice function at the other endpoint.

Indirect/computed calls are intentionally ignored at this stage.

## What frontier membership means

Frontier membership means only that the function is a useful next static target:

1. its exact unique `MWL::...::Method` string points at the same narrow
   subsystem namespace; and
2. it is directly adjacent in the retail call graph to a function already
   admitted to that subsystem evidence slice.

The candidate remains `promoted=false`. The subsystem slice is not enlarged by
this tool.

This is useful for prioritizing targeted instruction export, decompiler review
and call-site reconstruction without turning call-graph proximity into a method
identity claim.

## Ambiguous functions

Functions carrying multiple distinct method-name anchors remain excluded from
the frontier even when they directly touch a proven subsystem slice. They are
reported separately as `ambiguous-method-anchor-near-subsystem-slice` so they
can be investigated as dispatch/validation/shared-helper candidates without
selecting one arbitrary method name.

## Run

```bash
python3 tools/ghidra/build_subsystem_method_frontier.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_subsystem_method_frontier.json
```

Useful output groups are:

- `frontier_candidates` — unique namespace-compatible methods with a direct
  one-hop slice link;
- `namespace_only_without_one_hop_link` — exact names still lacking independent
  subsystem adjacency;
- `ambiguous_near_slice` — multi-name functions kept audit-only;
- `subsystems` — per-subsystem counts and candidate lists.

## Retail example

The existing retail evidence already illustrates why this layer is useful.
`FUN_00750080` (`MWL::Core::LoadCollisionStream`) is a promoted physics anchor
and directly calls `FUN_00710860`. Therefore `FUN_00710860` belongs to the
current one-hop physics slice. The exact
`MWL::Core::PhysicsAllocator::malloc` function `FUN_0079cd90` also directly
calls `FUN_00710860`, making it a natural one-hop physics frontier target.

This adjacency does not replace the stronger, separate
`SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1` proof and does not establish allocator
argument or ownership semantics.

## Evidence boundary

This layer does **not** prove:

- subsystem membership of a frontier candidate;
- complete method behavior;
- ABI or parameter roles;
- virtual dispatch identity;
- constructor/destructor roles;
- ownership/lifetime semantics.

Those require an explicit later promotion step backed by additional independent
evidence.
