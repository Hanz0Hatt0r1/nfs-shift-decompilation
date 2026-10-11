# Process 1B — materialized `manager+0x374` retail frontier runner

## Playable-slice blocker

P1.3B still cannot decide the exact `manager+0x374 -> HDVehicle+0x4330` identity join. The literal-destination `+0x374` writer surface is now closed 25/25 by `SHIFT.P1B.Manager374LiteralWriterClosure/1`, but the already-merged materialized-address probes have not yet been composed from one authoritative retail execution into a single candidate worklist.

This runner removes that acquisition/composition gap. It does **not** classify a receiver as Participants Manager and does not promote the final identity gate.

## Inputs

`tools/ghidra/run_p1b_manager374_materialized_retail_frontier.py` runs three existing SHA-locked analyzers against the same PC retail 1.02 executable:

1. `SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1`
   - exact `lea addr,[receiver+0x374]`;
   - GPR copies;
   - same-region zero-displacement write/RMW through `[addr]`.
2. `SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1`
   - exact materialized address persisted through the bounded EBP-relative spill/reload class;
   - only reload-derived writes are contributed as new candidates.
3. `SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1`
   - exact materialized address persisted through the bounded normalized ESP-relative spill/reload class;
   - only reload-derived writes are contributed as new candidates.

Every analyzer and the executable itself must match retail SHA-256:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

Format or SHA drift fails closed.

## Output contract

The runner emits:

```text
SHIFT.P1B.Manager374MaterializedRetailFrontier/1
```

The output records:

- candidate count per source probe;
- every original positive candidate row, tagged with `source_probe` and `transport_class`;
- a deduplicated physical-site union;
- all source probes contributing to each physical site;
- the complete unadjudicated physical-site worklist for the next receiver-identity pass.

Duplicate physical sites are deliberately retained in the raw candidate-record list so transport provenance is not lost.

## Fail-closed boundary

A candidate means only that machine dataflow in one bounded class reached a write through an address proven syntactically equivalent to `receiver+0x374`. It does **not** prove that `receiver` is the Participants Manager singleton/root/subobject.

Even if the composed candidate union is empty, the following remain false:

```text
all_materialized_candidate_receivers_classified
computed_address_manager_374_writer_surface_complete
unknown_or_unrelated_manager_root_alias_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains **7**.

Still outside this bundle:

- indexed or arithmetic address reconstruction;
- cross-control-flow materialized-address carry;
- non-stack memory aliases;
- helper-returned target addresses;
- runtime/external mutation;
- generated/self-modifying code;
- arbitrary process memory.

## Reproduction

Run on authoritative raw PC retail 1.02 `SHIFT.exe`:

```bash
python3 tools/ghidra/run_p1b_manager374_materialized_retail_frontier.py \
  /path/to/SHIFT.exe \
  --output /tmp/p1b_manager374_materialized_retail_frontier.json
```

The runner independently checks the executable SHA before invoking the three analyzers; each analyzer also verifies the same SHA.

Focused synthetic composition regressions:

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_materialized_retail_frontier.py
```

## Next step

Run the bundle on authoritative retail, then machine-adjudicate **only** the unique positive candidate receivers. Extend transport coverage only for a concrete surviving candidate class. Do not revisit the final `manager+0x374 -> HDVehicle+0x4330` join or `0x004b86cf`/slot2 adjudication until the materialized/computed receiver frontier is actually classified.
