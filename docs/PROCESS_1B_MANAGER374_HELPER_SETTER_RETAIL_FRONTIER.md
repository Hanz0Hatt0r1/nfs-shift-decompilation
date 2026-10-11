# Process 1B — manager+0x374 helper-setter retail frontier

## Purpose

Three bounded Process 1B probes now cover distinct decoded-image helper-mediated setter transports around `manager+0x374`:

1. `SHIFT.P1B.Manager374MaterializedDirectCallSetterProbe/1`
   - caller materializes `receiver+0x374` and passes the exact target address to a direct helper;
   - helper writes through the recovered argument alias.
2. `SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1`
   - direct local helper returns `entry argument + 0x374` in `EAX`;
   - caller immediately writes through `EAX` or an exact GPR copy.
3. `SHIFT.P1B.Manager374HelperReturnedTargetStackPersistenceProbe/1`
   - the qualified helper return is spilled to caller stack memory, reloaded, and then written through.

Running these independently would decode the retail executable three times and could make later evidence handling unnecessarily fragmented. This runner executes the three probes over one shared disassembly and composes their machine frontier.

## Tool and contract

```text
tools/ghidra/run_p1b_manager374_helper_setter_retail_frontier.py
SHIFT.P1B.Manager374HelperSetterRetailFrontier/1
```

Authority is pinned to PC retail 1.02 `SHIFT.exe`:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

The runner validates the SHA lock and output format of every component analyzer before composing results.

## Single instruction stream

The retail executable is disassembled once. The same decoded row list is passed to all three `scan_rows` implementations.

The aggregate records:

```text
single_shared_instruction_stream = true
decoded_instruction_count = <rows>
```

This makes a later local retail run reproducible as one acquisition event rather than three loosely synchronized scans.

## Resolved write frontier

Every positive component candidate is tagged with both its source probe and transport class:

```text
materialized-target-direct-helper-argument
helper-returned-target-immediate-gpr
helper-returned-target-stack-reload
```

The aggregate exposes:

```text
write_candidate_count_by_probe
write_candidate_record_count
write_candidate_records
resolved_write_candidate_union_empty
```

`resolved_write_candidate_union_empty=true` is only a fact about these three bounded classes. It is not a global setter or manager-root closure.

## Explicit open boundaries

The runner also carries four still-open boundary counts that are directly exposed by the component probes:

```text
materialized_target_indirect_call_argument_boundaries
materialized_target_unresolved_direct_targets
helper_return_unresolved_direct_targets
helper_return_non_stack_persistence_escapes
```

Their sum is `open_boundary_count`.

The convenience field:

```text
bounded_frontier_empty
```

is true only when both the resolved write-candidate union and those four explicit boundary counts are zero. Even then, global semantic gates remain fail-closed because unrelated opaque synthesis, generated/runtime code and external process mutation are outside the bundle.

## Output layout

Without `--out-dir`, the runner prints the aggregate JSON.

With:

```bash
python3 tools/ghidra/run_p1b_manager374_helper_setter_retail_frontier.py \
  /path/to/SHIFT.exe \
  --out-dir /tmp/p1b-helper-setter-frontier
```

it writes:

```text
frontier.json
direct_call_argument.json
helper_return_immediate.json
helper_return_stack.json
```

Each component output is annotated with the same retail SHA authority.

## Gate policy

A successful retail bundle run may establish only the acquisition/composition facts:

```text
retail_helper_setter_probe_bundle_execution_complete = true
retail_helper_setter_candidate_frontier_composed = true
```

The runner intentionally keeps these false:

```text
helper_setter_write_candidates_classified
materialized_helper_mediated_setter_surface_complete
helper_returned_materialized_address_surface_complete
helper_returned_target_non_stack_persistence_complete
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Limits

This bundle does not claim coverage of:

- indirect helper calls beyond the explicitly inventoried materialized-target boundary;
- external/imported direct helpers whose bodies are absent from the retail image;
- non-stack persistence after a helper-returned target escapes;
- helper-returned target forwarding into additional helper chains;
- unrelated opaque runtime synthesis;
- CFG-carried target aliases outside component bounds;
- runtime patching/generated/self-modifying code;
- arbitrary external process mutation.

No identity is inferred from equal numeric offsets or ABI argument channels.

## Tests

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_helper_setter_retail_frontier.py
```

The synthetic integration fixture exercises all three write transport classes in one shared instruction stream. Additional regressions cover indirect-call open boundaries, non-stack returned-target persistence, empty-frontier fail-closed semantics, candidate count drift and component contract pinning.

## Next step

Run this bundle on the authoritative PC retail image. For a non-empty result, classify every write candidate and each nonzero open-boundary class. For an empty bounded frontier, add a separate closure contract that promotes only the three component transport classes; do not promote the global helper/non-vtable setter or manager-root origin gates until their remaining external/opaque/runtime classes are independently resolved.
