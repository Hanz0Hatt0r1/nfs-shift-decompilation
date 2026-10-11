# Process 1B — manager+0x374 runtime-root frontier v2

## Playable-slice blocker

P1.3B still cannot perform the final `manager+0x374 -> HDVehicle+0x4330` identity join while unrelated runtime roots can, in principle, bypass the already-audited canonical lineage.

The v1 frontier mixed two different concerns:

1. program-internal aliases derived from the canonical outer root stored at `DAT_00bc185c`;
2. roots synthesized from unrelated external/unknown inputs.

The first class is now closed by already-merged retail machine evidence. This contract makes that closure explicit and leaves only the genuinely external/unknown classes open.

## Inputs

`SHIFT.P1B.Manager374RuntimeRootFrontier/2` composes:

- `SHIFT.P1B.Manager374RuntimeRootFrontier/1`;
- `SHIFT.HDVehicle64e8RenderManagerConstructorExactThisEscapeClosure/1`;
- `SHIFT.P1B.RenderManagerCanonicalAccessClosure/1`;
- `SHIFT.P1B.RenderManagerCopyReturnClosure/1`;
- `SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1`;
- `SHIFT.P1B.RenderManagerLiveCallBoundaryClosure/1`;
- `SHIFT.P1B.Manager374NamedOpaqueCandidateClosure/1`.

All retail-SHA-bearing inputs must match PC retail 1.02 SHA-256:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Closed program-internal surface

Before the canonical global store, constructor `FUN_0045ef50` has:

- exact-`this` memory stores as a value: **0**;
- exact-`this` helper argument transfers: **0**.

After construction, the canonical machine surface contains:

- **112** direct loads from `DAT_00bc185c`;
- exact-root memory stores: **0**;
- exact-root pushes: **0**;
- unmodelled exact-alias transfers: **0**;
- **3** LEA-derived subobject transitions, all proven unable to reconstruct the exact outer root;
- **7** functions with conditional exact-root EAX return residue and **6** direct callsites, with no consumer that persists or dispatches the exact root;
- **303** live exact-root call-boundary observations across **302** unique callsites;
- **17/17** bounded direct callee targets closed;
- exactly **3** indirect exact-root calls, all known vtable `+0x1c/+0x20` dispatches;
- non-vtable indirect exact-root calls: **0**.

Therefore the canonical program-internal lineage has no surviving post-construction mechanism that creates another persistent exact-root alias.

The two already-named opaque candidates are also closed for export: **2 candidates / 0 exportable**.

## Promoted scoped gate

This contract promotes:

```text
program_internal_canonical_lineage_runtime_alias_surface_complete = true
program_internal_canonical_lineage_runtime_alias_found = false
```

and the five component canonical-lineage closure gates for constructor escape, post-construction copies, returned-root consumers, derived subobjects and live call boundaries.

## Remaining frontier

Only three root-origin classes remain open:

1. externally or unknown-origin initialized memory containing the exact runtime outer pointer without a canonical program-internal producer;
2. a previously unidentified opaque helper that synthesizes the exact runtime pointer from unrelated unknown input;
3. an unrecognized runtime transform outside the merged bounded reconstruction classes.

These remain false:

```text
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
memory_load_or_opaque_runtime_reconstruction_complete
global_manager_root_origin_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains **7**.

This contract does not treat arbitrary external process mutation as absent, and it does not infer object identity from numeric offset equality.

## Reproduction

```bash
python3 tools/ghidra/build_p1b_manager374_runtime_root_frontier_v2.py \
  > /tmp/p1b_manager374_runtime_root_frontier_v2.json

diff -u \
  evidence/p1b_manager374_runtime_root_frontier_v2.json \
  /tmp/p1b_manager374_runtime_root_frontier_v2.json

python3 -m pytest -q \
  tests/test_process1b_manager374_runtime_root_frontier_v2.py
```

## Next step

Do not reopen canonical post-construction copies. Reduce only the remaining external/unknown-memory, unnamed opaque-helper, and unrecognized-transform origin classes. Only after those classes are bounded may Process 1B perform the final `manager+0x374 -> HDVehicle+0x4330` join and `0x004b86cf` / P1.3.slot2 adjudication.
