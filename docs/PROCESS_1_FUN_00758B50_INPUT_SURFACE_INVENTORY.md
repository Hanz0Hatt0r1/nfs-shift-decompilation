# Process 1 — `FUN_00758b50` input-surface inventory

## BLOCKER

P1.3 now needs exact PC-retail writers/producers for the vehicle/wheel state consumed by `FUN_00758b50`. The recovered four-wheel arithmetic is not enough to identify player-control provenance.

## TOOL

`tools/ghidra/inventory_fun_00758b50_input_surface.py` is a source-hash-locked navigation probe for the authoritative retail `SHIFT.exe.c`.

It extracts only the `FUN_00758b50` definition and inventories:

- assignment sites;
- every source-visible `+0x...` reference and its line;
- whether an offset appears on an assignment LHS;
- direct `FUN_xxxxxxxx` calls;
- global references.

The report format is `SHIFT.Fun00758b50InputSurfaceInventory/1`.

## WHY THIS IS NOT A CONTROL PROOF

A numeric offset reference is not evidence that the field is throttle, brake, steering, clutch, gear, or another control value. Local aliases can also hide reads/writes, and a callee may produce state that is not visible as a direct assignment in the target body.

The probe therefore reports:

```text
retail_control_value_producer_identified = false
complete_alias_aware_writer_surface_proven = false
manual_pointer_and_alias_review_required = true
```

It also keeps the already-proven structural anchors visible for review:

```text
wheel-state base   0x848
wheel-runtime base 0x400
wheel stride       0xa80
wheel count        4
```

## CONSUMER

Process 1 should use the emitted offset/call inventory to choose exact consumed fields and then trace their value provenance upstream to concrete PC-retail writers. Process 2 must not replace the external wheel-update/control-state boundary from this raw inventory alone.

## GATES

- P1.3 control producer complete: **false**;
- native `VehicleControlIntent` accepted as retail evidence: **false**;
- provider count remains **7**;
- this probe changes no runtime/provider gate.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Run the probe against the pinned `SHIFT.exe.c`, classify target-body reads/writes and aliases, then trace the smallest control-relevant consumed field to its exact upstream writer. Do not infer semantics from offset names or native test fixtures.
