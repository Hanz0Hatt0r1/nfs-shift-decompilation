# Process 1A / P1.3A — `+0xd94` loop receiver provenance

The runtime writer at `0x0045ecd3` is now known to receive a payload-derived address. Before treating that writer as a producer for the two `+0xd94` loop bounds, receiver identity must be established rather than inferred from the shared displacement.

`FUN_005031e0` is slot 1 of the loop-owner vtable at `0x00ac4a58`; its function address has one literal pointer occurrence in the retail image. The loop owner constructs a source container at `this+0x4` and a derived container at `this+0x38`.

The `this+0x4` source container is configured through `0x00502e20 -> 0x004d7470 -> 0x0062ffd0`. The wrapper passes `0xd98` into the allocator initialization path, establishing a source-record stride of `0xd98`.

When `FUN_00503390` populates the derived container, it indexes `this+0x4`, reads DWORD 0 of the selected source record, and `FUN_00502fd0` copies that DWORD unchanged into DWORD 0 of the derived record inserted at `this+0x38`.

`FUN_005031e0` then indexes `this+0x38`, loads `ECX = [derived_record+0]` at `0x005032e6`, and uses `[ECX+0xd94]` as the bound at `0x005032ea` and `0x0050337a`.

This proves the local loop-receiver chain but does not yet classify the producer of `source_record+0`. The writer `0x0045ecd3` operates on the `ECX/ESI` receiver of `FUN_0045ec60`; equality with the loop receiver has not been established. Therefore the payload-address writer cannot yet be used to invalidate or bound the loop field solely because both instructions mention `+0xd94`.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance_subset_complete` and `writable_callback_pair_d94_loop_receiver_source_chain_proven`. Receiver identity, runtime-writer relevance, value-range, callback/slot and aggregate P1.3 gates remain fail-closed.

Next: classify producers of `source_record+0` in `loop_owner+0x4` and compare their object class/provenance with the receiver of `FUN_0045ec60`.
