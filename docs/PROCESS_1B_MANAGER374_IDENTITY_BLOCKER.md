# Process 1B — manager+0x374 identity blocker

`SHIFT.P1B.Manager374IdentityBlocker/1` composes the two manager-domain contracts that currently determine the P1.3B identity blocker.

## Closed direct surfaces

- Exact manager-root direct forwarding has 9 callees.
- Exactly one direct nonzero writer to `manager+0x374` exists: `FUN_00d60660` at machine write `0x00d606f3`.
- That writer stores a selected allocator-owned `manager+0x2a0` entry, not fixed `HDVehicle+0x4330`.
- The unique direct computed `+0x374` write-through candidate in `FUN_00985bc0` is rejected by its exact DSP descriptor/receiver chain and cannot write Participants Manager `+0x374`.

## Remaining finite blocker

The upstream computed-use partition still has 18 runtime paths open:

- 1 returned-pointer escape;
- 17 callee-forwarding paths.

Until those are adjudicated, Process 1B must keep these gates false:

- `manager_374_join_to_hdvehicle_4330_complete`;
- `last_literal_0x004b86cf_rejected`;
- `p1_3_control_producer_complete`.

External provider count remains 7.

## Next step

Adjudicate the returned pointer from the remaining computed path, then classify the 17 callee-forwarding paths by receiver identity and mutation semantics. Do not infer object identity from matching `+0x374` / `+0x4330` offsets.
