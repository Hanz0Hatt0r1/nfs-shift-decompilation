# Process 1A / P1.3A — `+0xd94` vtable key contract

The remaining runtime producer for `[receiver+0xd94]` is the return value of the `DAT_00c26058` virtual call at `0x0045ecca`. This subset ties that lookup to the earlier registration of the exact backing handle storage rather than treating it as an unconstrained unrelated indirect call.

On PC retail 1.02, routine `0x0040d910` loads the singleton from `DAT_00c26058` and invokes vtable slot `+0xe0` twice with output storage `0x00bbf2d4` and `0x00bbf2d0`. The descriptor starts with DWORD `1`, two zero DWORDs, and its byte at offset `+0x0c` is changed to `1` between the two registrations.

Routine `0x0045ec60` loads the same singleton from `DAT_00c26058`. It then invokes vtable slot `+0xec` with the value stored at `0x00bbf2d0`, storing the result at `+0xd98`, and invokes the same slot with the value stored at `0x00bbf2d4`, storing the result at `+0xd94`.

Therefore the `+0xd94` producer is a lookup of a handle registered by the same runtime singleton, not an arbitrary independent indirect-call source. The image contains 13 references to `0x00bbf2d0` and 24 references to `0x00bbf2d4`.

This does **not** resolve the concrete implementation installed in vtable slot `+0xec`, and does not prove a numeric bound for its return value. `DAT_00c26058` is runtime storage beyond the file-backed `.data` extent, so its initial object/vtable pointer cannot be recovered by directly reading the retail image bytes. All aggregate callback/P1.3 gates remain fail-closed.

Next: resolve construction/vtable installation for `DAT_00c26058`, or derive a sound return-domain bound for slot `+0xec` when queried with the `0x00bbf2d4` handle.
