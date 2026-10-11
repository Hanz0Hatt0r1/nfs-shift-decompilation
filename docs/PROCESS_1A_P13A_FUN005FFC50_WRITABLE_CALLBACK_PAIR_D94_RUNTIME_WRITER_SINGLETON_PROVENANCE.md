# Process 1A / P1.3A — `+0xd94` runtime-writer singleton provenance

The loop receiver is now traced back to DWORD 0 of a `0xd98` source record, but equality with the runtime writer receiver remains open. This subset characterizes the writer side independently.

The PC retail image allocates `0x46e0` bytes, calls constructor `0x0045ef50`, and installs the result in `DAT_00bc185c`. The only direct writes to that singleton storage are the successful constructor result at `0x00d362ec` and the null fallback at `0x00d362f3`; the image contains 115 direct references to the storage.

The constructor installs primary table `0x00ab5644` and secondary tables `0x00ab55f0` / `0x00ab55e4`. Runtime refresh wrapper `0x00462d10` compares receiver fields `+0xd9c` and `+0xcbc`; on mismatch it is the sole direct branch in the decoded image to writer body `0x0045ec60`. The sole direct call to that wrapper is `0x004694fb`.

This bounds the direct writer-class surface, but it does not prove that every possible receiver reaching `0x0045ec60` is the singleton, nor that DWORD 0 of the loop source record is `DAT_00bc185c`. Copy/alias and indirect propagation remain open.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_runtime_writer_singleton_provenance_subset_complete`, singleton-constructor provenance, and the bounded direct writer-entry surface. Receiver identity, writer relevance to the loop bound, `+0xd94` value range, and aggregate callback/slot/P1.3 gates remain fail-closed.

Next: inventory exact/direct propagation of `DAT_00bc185c` toward source-record construction and independently classify producers of `source_record+0`.
