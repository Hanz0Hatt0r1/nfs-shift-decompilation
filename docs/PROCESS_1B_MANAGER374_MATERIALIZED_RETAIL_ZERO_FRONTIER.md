# Process 1B — materialized `manager+0x374` retail zero frontier

## Playable-slice blocker

The final P1.3B `manager+0x374 -> HDVehicle+0x4330` join remained blocked in part because the three already-merged materialized-address probes had never been executed against the authoritative raw PC retail executable and committed as one candidate frontier.

The authoritative `SHIFT.exe` is now available and SHA-locks to:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

The same local evidence set also retains the pinned Ghidra authorities used by earlier P1B contracts:

```text
SHIFT.exe.c        512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
shift_ghidra.sqlite ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
```

## Retail execution surface

The retail machine disassembly contains **2,847,850** decoded instructions and **19** exact `LEA` materializers of the bounded form:

```text
lea addr,[receiver+0x374]
```

A direct independent machine pass over those exact seeds observes:

- exact materialized seeds: **19**;
- same-region GPR copies before a control boundary: **1**;
- same-region zero-displacement write/RMW candidates: **0**;
- exact EBP/ESP pointer spills from a live materialized address before an allowed control boundary: **0**.

Those observations collapse all three merged candidate producers to zero:

| Probe | Retail write candidates |
| --- | ---: |
| `SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1` | 0 |
| `SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1` | 0 |
| `SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1` | 0 |

The committed `SHIFT.P1B.Manager374MaterializedRetailFrontier/1` therefore contains:

```text
candidate_record_count = 0
unique_candidate_site_count = 0
unadjudicated_candidate_site_count = 0
```

There is no receiver identity to adjudicate inside these three bounded transport classes.

## Scoped closure

`SHIFT.P1B.Manager374MaterializedRetailClosure/1` promotes only:

```text
materialized_plus_374_same_region_retail_frontier_empty = true
materialized_plus_374_ebp_spill_reload_retail_frontier_empty = true
materialized_plus_374_esp_spill_reload_retail_frontier_empty = true
materialized_plus_374_bounded_transport_surface_complete = true
all_materialized_candidate_receivers_classified = true
materialized_plus_374_bounded_transport_can_write_manager_374 = false
```

This closes the exact same-region, EBP spill/reload and normalized ESP spill/reload transport classes that #1975/#1977/#1979/#1981/#1988 introduced.

## Fail-closed boundary

This does **not** prove a global absence of all possible computed or runtime routes. In particular, separate evidence is still required for any surviving:

- indexed or other arithmetic address construction not already covered by the merged reconstruction/computed-runtime contracts;
- cross-control-flow materialized-address carry;
- non-stack memory aliases;
- helper-returned addresses from an unrelated opaque origin;
- external/runtime memory mutation;
- unrecognized runtime transforms.

Therefore the following remain false here:

```text
computed_address_manager_374_writer_surface_complete
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

## Reproduction / validation

The merged acquisition runner remains:

```bash
python3 tools/ghidra/run_p1b_manager374_materialized_retail_frontier.py \
  /path/to/SHIFT.exe \
  --output /tmp/p1b_manager374_materialized_retail_frontier.json
```

The committed frontier is the zero-candidate authoritative retail result. The scoped closure is reproduced by:

```bash
python3 tools/ghidra/build_p1b_manager374_materialized_retail_closure.py \
  > /tmp/p1b_manager374_materialized_retail_closure.json

diff -u \
  evidence/p1b_manager374_materialized_retail_closure.json \
  /tmp/p1b_manager374_materialized_retail_closure.json

python3 -m pytest -q \
  tests/test_process1b_manager374_materialized_retail_closure.py
```

## Next step

Compose this zero materialized frontier with the already-closed computed-runtime and reconstruction classes. The next useful P1B evidence should target only the surviving external/unknown-memory, unnamed opaque-helper and unrecognized-transform root-origin classes. Do not reopen these three materialized transport classes before the final identity join and `0x004b86cf` / slot2 adjudication.
