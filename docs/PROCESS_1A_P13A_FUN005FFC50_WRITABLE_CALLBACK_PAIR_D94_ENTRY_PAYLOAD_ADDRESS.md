# Process 1A / P1.3A — `+0xd94` entry payload-address contract

The previous subset resolves the registered entry vtable slot 0 as `0x00835290`. This subset classifies the non-zero value returned by that slot.

The entry constructor configures the embedded container at `entry+0x40` through `0x0062f910` / `0x0062f520`. For this path the low flags argument is `4`, so the pointer-prefix branch controlled by bit `0x100` is not taken.

Block construction in `0x0062f2d0` / `0x0063ac20` stores the allocated payload start at `block+0x4`. Allocation in `0x0063ac90` returns `payload_base + index * stride`. `0x0062f6f0` forwards that allocation result to slot 0; with this container configuration the non-zero slot-0 result is therefore an address into the allocated payload.

This is not a proof that the `+0xd94` loop consumers at `0x005032ea` and `0x0050337a` read the same logical field as the writer at `0x0045ecd3`. The identical displacement alone is insufficient: receiver identity/provenance must be established first.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_entry_payload_address_subset_complete` and `writable_callback_pair_d94_entry_slot0_nonzero_return_is_payload_address`. The `+0xd94` value-range and aggregate callback/slot/P1.3 gates remain fail-closed.

Next: resolve receiver identity/provenance between `0x0045ecd3` and the two loop consumers before using this runtime writer in any count-bound proof.
