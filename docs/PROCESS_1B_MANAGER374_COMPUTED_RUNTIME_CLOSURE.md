# Process 1B — manager+0x374 computed runtime closure

`SHIFT.P1B.Manager374ComputedRuntimeClosure/1` closes the finite computed `+0x374` use partition that remained after the direct writer blocker contract.

## Composition

The original computed runtime frontier had 18 paths:

- 1 direct write-through candidate: rejected as DSP descriptor state, not Participants Manager;
- 1 returned-pointer path from `FUN_00529020`: its only consumer reads the pointee value and does not store, forward, or write through the returned pointer;
- 17 callee-forwarding paths:
  - 11 source-only forwards are proven read-only at the callee ABI/machine level;
  - 6 receiver/destination forwards are closed-negative by exact receiver provenance across P1.3A/P1.3B/P1.3D.

The six receiver/destination sites are:

- `0x005292db`
- `0x005f4ffa`
- `0x005f6eda`
- `0x0070f62d`
- `0x0070fb45`
- `0x0070fdeb`

All six are proven to operate on receiver domains distinct from Participants Manager. Numeric `+0x374` equality is never used as identity evidence.

## Result

The computed runtime path count is now `0`, so the bounded computed-address writer surface is complete and no path in this partition can establish `manager+0x374 -> HDVehicle+0x4330`.

This does **not** complete the global identity join. Stored manager-root escapes, stack-argument aliases, unrelated reconstructed roots, and other non-computed paths remain open. Therefore these gates remain fail-closed:

- `escaped_storage_paths_complete=false`
- `stack_argument_alias_paths_complete=false`
- `manager_374_join_to_hdvehicle_4330_complete=false`
- `last_literal_0x004b86cf_rejected=false`
- `p1_3_control_producer_complete=false`

External provider count remains `7`.

## Next step

Close escaped-storage and stack-argument manager-root aliases. Only after those surfaces are exhausted should Process 1B perform the final `manager+0x374 -> HDVehicle+0x4330` identity join and adjudicate `0x004b86cf` / slot2.
