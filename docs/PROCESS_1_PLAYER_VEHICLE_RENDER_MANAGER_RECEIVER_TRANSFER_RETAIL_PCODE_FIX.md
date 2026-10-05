# Process 1 — retail render-manager receiver p-code seed fix

## Blocker

`SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/1` consumed the real exhaustive 80-function retail instruction export but produced zero seeds from 95 exact READ xrefs of `DAT_00bc185c`. Every read was rejected before receiver taint propagation, so the result could not be interpreted as a negative manager-transfer proof.

## Root cause

`ShiftFunctionInstructionExporter` serializes p-code outputs from Ghidra `Varnode.toString()` plus structured `space`, `offset`, `size`, `register`, and `unique` fields. The first receiver-transfer implementation incorrectly assumed `output.text` was the canonical register name such as `EAX` or `ESI`. Synthetic tests used that simplified shape, while retail exports use register-space varnode text.

## Fix

`build_player_vehicle_render_manager_receiver_transfer_frontier.py` now:

- resolves IA-32 tracked register varnodes from structured register-space offset/size, while retaining canonical-name compatibility for older fixtures;
- accepts both direct `LOAD -> register` and bounded `LOAD -> unique -> COPY -> register` forms inside one instruction;
- still requires exact ranked `DAT_00bc185c` READ provenance and a unique register-engine global origin before a seed is admitted;
- locally invalidates a tracked pointer on structured p-code writes not modeled by the machine transfer engine, preserving the fail-closed all-path policy.

No call target, `+0xca4` field, render owner, VHF root, frame identity, or BODY0 proof is promoted by this fix.

## Next evidence

Re-run the frontier against the existing exhaustive retail artifacts. A positive result may emit only direct call targets reached with the proven manager pointer in ECX/EDX or unresolved indirect dispatch sites. If no call transfer remains after retail-compatible seeding, that negative result can then close this first-hop branch.
