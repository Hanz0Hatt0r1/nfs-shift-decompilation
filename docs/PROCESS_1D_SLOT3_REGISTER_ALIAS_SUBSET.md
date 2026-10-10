# Process 1D — slot3 register-alias subset closure

This pass composes three already-merged P1D contracts to close a bounded set of register-resident selected-wheel aliases without promoting the global stored/escaped-alias gates.

The semantic authority remains the hash-locked PC retail machine proofs. The SQLite CALLIND inventory is used only as a navigation/cross-check surface for the already-proven carrier set.

## `FUN_00758b50 -> FUN_00755950`

The primary alias contract proves the per-wheel machine materialization:

```text
0x00758ccf  ECX = ESI-0x448 = HDVehicle+0x400+slot*0xa80
0x00758d6b  call FUN_00755950
```

No other direct callee in that per-wheel body receives the exact wheel root. Inside `FUN_00755950`, the entry root is copied only into `EDX`:

```text
0x00755956  EDX = ECX
0x00755958  fld qword [EDX+0x538]
```

The target `+0x538` field is read-only in this bounded consumer, and the exact wheel root is not forwarded to its sole direct callee.

## `FUN_00763570 -> FUN_00755f80`

The merged four-wheel contract proves:

```text
wheel seed = HDVehicle+0x400
stride     = 0xa80
iterations = 4
slot3      = HDVehicle+0x2380
```

`FUN_00755f80` captures the exact wheel root as `ESI=ECX`. The machine contract proves zero wheel-root writes, no store/push of the captured wheel root, no exact-root forwarding to a direct callee, and zero indirect calls.

## Indirect-call cross-check

All three functions (`FUN_00758b50`, `FUN_00755950`, `FUN_00755f80`) are members of the previously fingerprinted 15-function exact-carrier set. The pinned SQLite surface contains 19,500 indirect call edges globally but zero whose caller is any function in that carrier set. This rules out only CALLIND edges originating inside these known carriers; it does not rule out later callback use, indirect entry, or aliases created elsewhere.

## Gate status

This pass sets only:

```text
machine_proven_register_alias_subset_complete = true
machine_proven_register_alias_subset_persistent_store_found = false
machine_proven_register_alias_subset_new_forward_found = false
machine_proven_register_alias_subset_callind_found = false
```

The broader gates remain fail-closed:

```text
machine_register_alias_storage_ruled_out = false
other_register_aliases_ruled_out = false
callee_created_aliases_ruled_out = false
aggregate_or_bulk_alias_stores_ruled_out = false
callbacks_registered_outside_carriers_ruled_out = false
stored_or_escaped_aliases_ruled_out = false
slot3_writer_provenance_proven = false
p1_3d_complete = false
```

Provider count remains 7.

Reproduce the handoff from merged evidence:

```bash
python3 tools/ghidra/build_p1d_slot3_register_alias_subset.py \
  evidence/p1d_slot3_primary_alias_escape.json \
  evidence/p1d_slot3_fun00755f80_wheel_child_closure.json \
  evidence/p1d_slot3_exact_carrier_indirect_call_surface.json \
  --output out/p1d_slot3_register_alias_subset_closure.json
```

## Next step

Inventory callee-created selected-wheel aliases and register aliases outside these three bounded paths. Any positive persistence, callback registration, or later indirect consumer must be joined back to exact selected-wheel provenance before changing the global stored/escaped-alias gates.
