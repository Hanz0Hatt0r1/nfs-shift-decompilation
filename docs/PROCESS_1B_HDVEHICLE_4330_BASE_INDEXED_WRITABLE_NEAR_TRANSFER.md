# Process 1B: HDVehicle+0x4330 base/indexed writable near-transfer subset

This contract reuses the target-agnostic machine scan from `SHIFT.P1A.P13AFun005ffc50BaseIndexedDataNearTransfer/1` for the 15 canonical P1B carrier addresses.

## Result

Across PC retail 1.02:

- decoded instructions: **2,847,850**;
- exact base/index-addressed writable `.data` loads: **63**;
- unique effective addresses: **51**;
- same-register indirect `CALL/JMP` within the bounded 16-instruction straight-line window: **0**;
- exact P1B carrier target hits in this subset: **0**.

Termination inventory is 58 unrelated control transfers and 5 destination-register clobbers.

## Gate effect

Promoted only:

- `base_indexed_writable_same_register_near_transfer_subset_complete=true`;
- `base_indexed_writable_same_register_can_target_exact_p1b_carrier=false`.

Still fail-closed:

- register copy/transform after the base/indexed load;
- stack spill/reload;
- inter-block carry;
- aliases and arbitrary runtime mutation;
- global indirect entry, runtime-generated/copied pointers and generic stores/copies;
- `manager+0x374 -> HDVehicle+0x4330`;
- `0x004b86cf`/slot2 and aggregate P1.3.

Provider count remains **7**.
