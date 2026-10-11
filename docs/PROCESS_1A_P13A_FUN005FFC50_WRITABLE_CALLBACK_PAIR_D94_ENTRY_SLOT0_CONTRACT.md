# Process 1A / P1.3A — `+0xd94` entry slot-0 contract

The concrete singleton lookup from the previous subset dispatches non-null handle entries through entry vtable slot 0. This subset resolves that entry class and slot-0 target for the retail image.

The registration path at `0x008313b0` allocates `0x68` bytes and constructs the entry with `0x008309f0`. The constructor installs vtable `0x00b17fe0`; its first slot is `0x00835290`.

At the consumer `0x0045ecca`, lookup target `0x0082da60` calls that slot with `EDX = &[ESI+0xcb0]` and two zero stack arguments. The result is stored at `[ESI+0xd94]`.

`0x00835290` queries the embedded container at `entry+0x40` via `0x0062f6f0`. It can return zero. On the non-zero path it forwards the returned container-derived value through `0x008339e0` and returns that same value on success.

The analyzer asserts these concrete instructions and the first DWORD of vtable `0x00b17fe0` against the PC retail 1.02 image; unknown or drifted instructions fail the subset rather than widening the claim.

This closes the indirect-dispatch identity but not the non-zero return domain. In particular, the downstream loop shape at `0x005032ea` / `0x0050337a` is not by itself sufficient to prove that `+0xd94` is a small integer count.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_entry_slot0_contract_subset_complete` and the concrete slot-0 target `0x00835290`. The `+0xd94` value-range gate and all aggregate callback/slot/P1.3 gates remain fail-closed.

Next: trace the value returned by `0x0062f6f0` / `0x0062f460` for the embedded `entry+0x40` container and classify its domain before attempting any range proof.
