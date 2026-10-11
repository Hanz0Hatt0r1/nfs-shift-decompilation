# Process 1A / P1.3A — `+0xd94` writer singleton direct propagation

The writer singleton provenance is established at `DAT_00bc185c`. This subset asks a narrower question: after each direct load of that singleton pointer, is the exact pointer copied into non-stack memory before the first control transfer?

Across the PC retail 1.02 image there are 115 direct singleton references: 113 loads and the two already-classified singleton-storage writes. A bounded exact register-copy scan follows each load only inside its straight-line block and stops at the first call, jump, or return.

The scan observes four memory stores of the singleton alias, all to stack locals (`0x0057b6e4`, `0x00d77fad`, `0x00d77fb0`, `0x00d77fb3`). It observes zero same-block non-stack stores. At the control-transfer frontier, 30 calls receive the exact alias in `ECX` and two receive it in `EDX`.

Therefore this bounded surface contains no direct singleton-pointer store into the loop source record or any other non-stack memory. This is not an interprocedural negative proof: callees may retain, copy, return, or otherwise materialize aliases, and later basic blocks are outside this subset.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_writer_singleton_direct_propagation_subset_complete`. Receiver identity, writer relevance to the loop bound, value-range and aggregate callback/slot/P1.3 gates remain fail-closed.

Next: classify the 30 `ECX`-receiver and two `EDX`-argument call frontiers, and independently classify the key/producers stored in `source_record+0`.
