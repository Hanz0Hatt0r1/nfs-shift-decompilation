# Process 1D — slot3 direct-callee alias subset closure

This pass closes the bounded direct-callee surface already reachable from merged exact-wheel machine contracts. It does not infer selected-wheel identity from offsets alone and does not promote the global callee-created/stored-alias gates.

## Exact-root callees

Two direct callees are already proven to receive the exact wheel root.

### `FUN_00758b50 -> FUN_00755950`

The primary wheel-loop proof materializes the exact receiver and calls `FUN_00755950`. Inside that consumer, `+0x538` is read as a qword and is not written. Its only direct callee receives `wheel+0x80`, not the exact wheel root, so the exact-root chain ends there for this bounded path.

### `FUN_00755a60 -> FUN_00752fc0`

The exact-wheel direct-carrier proof forwards the exact wheel root to `FUN_00752fc0`. That leaf writes only `+0x5b8` and `+0x7d8`, neither overlapping selected target `+0x538`, and it has no direct callees.

## Direct callees that do not receive the exact root

The following paths are deliberately kept distinct from exact-root forwarding:

```text
FUN_00755950 -> FUN_007555b0   receiver = wheel+0x80
FUN_00760b50 -> FUN_007ba860   receiver = [wheel+0x420]
FUN_00755f80 -> FUN_007af0a0   receiver = [wheel+0x420]
FUN_00755f80 -> FUN_007af010   receiver = [wheel+0x420]
```

`wheel+0x80` is an interior pointer. `[wheel+0x420]` is a dereferenced child pointer. Neither is reclassified as the exact selected-wheel root merely because it originates from a wheel object.

## Indirect-call cross-check

All relevant known carrier functions are present in the fingerprinted exact-carrier set. The pinned SQLite inventory records zero CALLIND edges originating in that set. This is only a bounded cross-check; it does not rule out indirect entry, callbacks registered elsewhere, or aliases created after the listed calls.

## Gate status

This pass establishes:

```text
known_direct_callee_exact_root_receiver_count = 2
known_direct_callee_created_alias_subset_complete = true
known_direct_callee_selected_target_writer_found = false
known_direct_callee_exact_root_escape_found = false
known_direct_callee_callind_found = false
```

The broader gates remain fail-closed:

```text
other_callee_created_aliases_ruled_out = false
callee_created_aliases_ruled_out = false
machine_register_alias_storage_ruled_out = false
aggregate_or_bulk_alias_stores_ruled_out = false
callbacks_registered_outside_carriers_ruled_out = false
stored_or_escaped_aliases_ruled_out = false
slot3_writer_provenance_proven = false
p1_3d_complete = false
```

Provider count remains 7.

Reproduce from merged evidence:

```bash
python3 tools/ghidra/build_p1d_slot3_direct_callee_alias_subset.py \
  evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json \
  evidence/p1d_slot3_primary_alias_escape.json \
  evidence/p1d_slot3_fun00755f80_wheel_child_closure.json \
  evidence/p1d_slot3_exact_carrier_indirect_call_surface.json \
  --output out/p1d_slot3_direct_callee_alias_subset_closure.json
```

## Next step

Search outside these known direct-callee paths for exact wheel-root persistence or callback registration. Any positive store must be joined to its later consumer and independently proven to preserve selected slot3 identity before a global alias gate can change.
