# Process 2 Native queue-head and IRQ audit — 2026-10-28

## Scope and inputs

Read-only audit of Process 1's paired retail capture. No guest runtime, Process 1 code, renderer code, or captured files were changed.

- Process 1 report: `docs/XBOX360_PROCESS1_COMPARATIVE_FRONTIER_20261028.md`, PR head `bd68e0d5d5aa2f1d400e7127d2663ed11c58f629`, SHA-256 `70b9ea5197026290e50f4042d564fbb64af6f23a71483e075b7a938849812ff2`.
- Paired record: `evidence/xbox360_linux_native_14841319_paired_physical_counter_20261028.json`, SHA-256 `1a3956600c0b258c39b9664f29300e54013335ffa0e7e0a9c49f8c37e6c62029`.
- Source-1/PM4 archive: `evidence/xbox360_linux_native_14841319_paired_source1_join_inputs_20261028.jsonl.gz`, SHA-256 `f9a20afc9adba5013a0200c75f76953e293a0c4b5a6fb5101ce6dea977c8d956`.
- Captured Native plugin: source commit `14841319bedf9ecf16e15270574381e83b021677`, SHA-256 `f794272592ea955c66f00a11c784a56bc77baa6f2205c83fdad8269fdac5443f`, Build ID `ebbb619ab5a5142d3392b62867b88848744492c0`.

## Queue-head contract and Native writes

The guest wait routine at `sub_823B34A0` reads the consumer head through `manager+10896`, reads the producer tail at `manager+10908`, and compares `tail-target` with `tail-head` before deciding whether to wait. In the captured range, moving head from 3381 back to 3375 while tail is 3401 increases the unconsumed distance from 20 to 26. This is backward consumer-cursor movement, not a ring wrap at these values.

The watched software head is guest address `0xB7AF4000`, physical alias `0x17AF4000` (host alias `0x217AF4000`). It is distinct from the PM4 ring RPTR writeback word `0x17AF403C`. The paired capture attributes the software-head stores to `RingWorkerLoop()+26867`; disassembly of the captured DSO resolves that PC to the store in the `EVENT_WRITE_SHD` handling path. The Native implementation decodes the packet's guest address and value and stores the decoded value after endian conversion ([shift_native_gpu_plugin.cpp](../native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp#L2606), [xbox_guest_ring.cpp](../native_vulkan/src/xbox_guest_ring.cpp#L219)). The Xenos SDK handler applies the same literal-value versus swap-counter rule (`ExecutePacketType3_EVENT_WRITE_SHD`, SDK source commit `b3648b013b02770fa5ca8d4618235b2326c911ca`).

Observed paired Native head writes: 830 total; `+2`: 713; `-6`: 114; `-8`: 1; `-18`: 1; `+10`: 1. All 114 `-6` writes are `3381 -> 3375`; the other two negative writes also land at 3375 (`3383 -> 3375`, `3393 -> 3375`). Xenos wrote the same watched field 477 times, all `+2`. Native's negative stores therefore violate forward progress of the guest-visible consumer head in this capture. They are not explained by the separate PM4 RPTR wrap behavior.

The capture does **not** retain the EVENT_WRITE_SHD packet bytes/source identity for those later writes. The Native log emits detailed EVENT_WRITE_SHD records only for the first 16 events; the guest watchpoint records the value and writer PC but not ring batch, packet ordinal, source IB, or byte offset. The source-1 archive contains interrupt/callback rows, not the EVENT_WRITE_SHD packet stream. The evidence proves the Native plugin stored a regressing head value through its EVENT_WRITE_SHD path, but does not distinguish a stale/replayed/out-of-order command in Native processing from a retail packet that explicitly carried 3375. Xenos is a useful comparator here, not a correctness oracle: its paired run reached the scene gate and received inputs that the Native run did not.

## First manager-counter mismatch

The Native write is mapped exactly to guest queue work, but not to a PM4 interrupt:

- Counter write #6: `manager+11012` at `0xB7368A04`, `1 -> 0`, signed delta `-1`, guest caller `sub_823B85D0`.
- Completion id 771, token `0xC0000000`, is explicitly joined to parent dequeue id 760 / record `0xC969D480` on queue `0xB7368BE0`; that dequeue advances consumer `5 -> 6` while producer is `9 -> 12`, slot 1.
- The nearest source-1 PM4 candidate is ordinal 908 / packet ordinal 663 at `0x09752580`, batch `[rptr=2075, wptr=2090)`, source IB `0x09679600` + byte offset 19632. It is 2 ms before the counter write. A guest callback entry for the same manager is 8 ms before it. The PM4 archive callback is the registered wrapper on CPU 2; the guest callback record has no PM4 ordinal/dispatch ID, and the dequeue/completion records have no interrupt ID.

Therefore the exact linked work item is dequeue 760/completion 771. Ordinal 908 is only a temporal candidate; assigning the counter decrement to that batch or packet would exceed the available join evidence. The paired capture's first Native/Xenos counter-operation mismatch remains an execution difference, not a proven interrupt-causality result.

## Next capture needed

For the head regression, capture each EVENT_WRITE_SHD targeting `0x17AF4000` with ring generation, root batch rptr/wptr, packet ordinal, source IB and byte offset, raw initiator/address/value, decoded stored value, and old/new head. For the interrupt question, carry one dispatch identifier from the PM4 source-1 record through `ExecuteInterrupt`, guest callback entry, and the resulting dequeue/completion record. This makes the next join causal rather than timestamp-based.
