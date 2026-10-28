# Process 2 Native queue-head and IRQ audit — 2026-10-28

## Scope and inputs

Read-only audit of Process 1's paired retail capture. No guest runtime, Process 1 code, renderer code, or captured files were changed.

- Process 1 report: `docs/XBOX360_PROCESS1_COMPARATIVE_FRONTIER_20261028.md`, PR head `bd68e0d5d5aa2f1d400e7127d2663ed11c58f629`, SHA-256 `70b9ea5197026290e50f4042d564fbb64af6f23a71483e075b7a938849812ff2`.
- Paired record: `evidence/xbox360_linux_native_14841319_paired_physical_counter_20261028.json`, SHA-256 `1a3956600c0b258c39b9664f29300e54013335ffa0e7e0a9c49f8c37e6c62029`.
- Source-1/PM4 archive: `evidence/xbox360_linux_native_14841319_paired_source1_join_inputs_20261028.jsonl.gz`, SHA-256 `f9a20afc9adba5013a0200c75f76953e293a0c4b5a6fb5101ce6dea977c8d956`.
- Captured Native plugin: source commit `14841319bedf9ecf16e15270574381e83b021677`, SHA-256 `f794272592ea955c66f00a11c784a56bc77baa6f2205c83fdad8269fdac5443f`, Build ID `ebbb619ab5a5142d3392b62867b88848744492c0`.

## Queue-head contract and Native writes

The guest wait routine at `sub_823B34A0` reads the consumer head through `manager+10896`, reads the producer tail at `manager+10908`, and compares `tail-target` with `tail-head` before deciding whether to wait. In the captured range, moving head from 3381 back to 3375 while tail is 3401 increases the unconsumed distance from 20 to 26. This is backward consumer-cursor movement, not a ring wrap at these values.

The watched software head is guest address `0xB7AF4000`, physical alias `0x17AF4000` (host alias `0x217AF4000`). It is distinct from the PM4 ring RPTR writeback word `0x17AF403C`. The paired capture attributes the software-head stores to `RingWorkerLoop()+26867`; disassembly of the captured DSO resolves that PC to the store in the `EVENT_WRITE_SHD` handling path. The Native implementation decodes the packet's guest address and value and stores the decoded value after endian conversion ([shift_native_gpu_plugin.cpp](../native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp#L2653), [xbox_guest_ring.cpp](../native_vulkan/src/xbox_guest_ring.cpp#L228)). The Xenos SDK handler applies the same literal-value versus swap-counter rule (`ExecutePacketType3_EVENT_WRITE_SHD`, SDK source commit `b3648b013b02770fa5ca8d4618235b2326c911ca`).

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

## Follow-up observation from the P1 deep capture

Read-only inspection of `nfs-shift-p1-native-event-write-head-deep-2-14841319-20261028/runs/shift-native-r2/runner.log` found 1,985 debugger-captured writes to `0x17AF4000`. The captured packet values advance monotonically from the initial head through 3971; the 3381 boundary is `3381 -> 3383`, and no captured write regresses. This is a distinct follow-up run using the old plugin SHA above, not a clean replay of the earlier paired run, and its GDB script exited 1 after the script was edited during capture. It therefore shows that the earlier 3381 -> 3375 sequence was not reproduced in this run; it does not establish why the earlier trace differed.
The captured write at event index 1690 records `head_before=3381` and raw packet bytes `c00258000000000317af400200000d37`, whose literal value is `0x00000D37` (3383). This confirms that this separate run executed a packet explicitly advancing the head; it still cannot identify the packet(s) from the earlier paired regression.

The P2 working branch now adds opt-in `SHIFT_NATIVE_VULKAN_TRACE_RING=1` records for every successfully decoded EVENT_WRITE_SHD. Each record carries ring batch/generation and pointers, packet ordinal, source buffer and offset, nesting depth, raw packet words, the expansion-time packet snapshot comparison, decoded destination/value/endian semantics, and guest memory before/after. Source-1 PM4 interrupts receive a monotonically allocated dispatch ID, and `shift_native_gpu_trace_dispatch_id_v1()` exposes that ID only while the corresponding synchronous guest callback is running. The P1 callback-entry capture can sample this getter and carry its numeric value into queue/dequeue/completion records. These changes are diagnostic only: no PM4 ordering or writeback behavior has been altered, and no cause is claimed until the new plugin is built and a fresh capture joins the packet to the resulting guest work.

## Instrumentation validation and current limits

The provenance instrumentation passed the Native guest-ring unit test, the plugin factory smoke test, and the live-ring trace-only CTest with `VK_LAYER_KHRONOS_validation` enabled. Python regressions passed for both the EVENT_WRITE_SHD auditor and exact dispatch-ID interrupt join. The trace-only fixture validates provenance and interrupt logging; it deliberately does not evaluate rendering.

The ordinary live-ring fixture still fails its existing synthetic presenter assertion on the current retail-lwsync SDK: captured operation stream packet 2 has unresolved resources, so it reports two resolved resources, one unresolved packet, and zero Vulkan frames. Rebuilding commit `14841319bedf9ecf16e15270574381e83b021677` against the same SDK and runtime produced the same failure. This is a fixture/SDK baseline limitation for this check, not evidence about retail scene rendering. The renderer check remains enabled and has not been weakened.

The Linux diagnostic plugin was built against SDK commit `923a7a03575b43f6c22ee97c376077a7022d17d6`, using its prebuilt `librexruntime.so`. Its SHA-256 is `2a0b63a6c6e4563818cda48bb24664c627e555aec10c864c5d951198de231a9a` and ELF Build ID is `8932d691d1e9d5f0cdfe57590a2f9829b5c62477`. This is the artifact intended for the next paired Linux capture.

The frozen Linux DSO was rebuilt from source commit `b1855edbeafd426364d3711e3776aa8b7ee80dfd` and copied to `/home/pes/work/nfs-shift-process2-eventwrite-dispatch-b1855edb/linux-x86_64/librexgpu-shift-native.so`; its adjacent `manifest.txt` records the hashes and build identities. Run the original paired workload with `SHIFT_NATIVE_VULKAN_TRACE_RING=1` (do not set `SHIFT_NATIVE_VULKAN_TRACE_ONLY`), confirm the loaded DSO hash, and retain the complete runner log. The Android compile-only DSO is in the same artifact directory under `android-arm64/`.

An Android ARM64 compile also succeeded with NDK r28c, API 26, the compatible Android SDK snapshot v0.10.0, and its matching runtime. The output SHA-256 is `29a9ad24c94c167cf63aef6bdd246e12ef062966056dcecadee707abb6a89afd`, Build ID `8f9b396a1a18bd00f256e77dc9b9672464ee7baa`. This is compile-only; no Android device execution was performed. The retail-lwsync Linux SDK did not compile for Android because its headers use unsupported `std::from_chars` floating-point and `clock_time_conversion` facilities in that Android toolchain. Therefore this Android artifact validates the plugin source against the compatible Android snapshot, not parity with the Linux lwsync SDK.

## Partial paired attempt and replacement artifact

The first paired attempt using the `b1855edb` Linux DSO is preserved under `/dev/shm/nfs-shift-p1-gpu-dispatch-pair-20261028`. It loaded the expected plugin SHA but ended after 81.278 seconds with GDB exit `-6`: the debugger's inferior call to the thread-local dispatch getter resumed another thread into a breakpoint, then GDB hit its `keep_going_pass_signal` internal assertion. The callback's `gpu_dispatch_id` was null, and Native only reached software head 2573, below the 3381 window. Treat this run as partial, not as the paired result.

The independent P2 audit of both Native log rotations recovered EVENT_WRITE_SHD event IDs `0..2577` without gaps. It found 1,286 writes to `0x17AF4000`, all `+2`, with no guest-head regressions, no discontinuity between adjacent writes, and no mismatch between expansion-time and execution-time IB packet bytes. This demonstrates trace integrity only for the captured interval; it does not reproduce or explain the earlier rollback.

The aborted run also exposed that placing `dispatch_id` between `source=1` and `generation=` broke the existing P1 interrupt-line parser. Commit `36aad9274f6c39be9c60028da085300fcafeccf8` restores the legacy field order and appends the ID after `callback_dispatches`; the P1 parser was verified against this format and returns one record with zero malformed lines. Process 1 separately confirmed that GDB `scheduler-locking on` around the pure getter call returns the TLS ID and prevents another thread's breakpoint from interrupting the call.

The replacement Linux DSO is frozen at `/home/pes/work/nfs-shift-process2-eventwrite-dispatch-36aad927/linux-x86_64/librexgpu-shift-native.so`, SHA-256 `cf9ffc3775db83c874d69da6dc3e6995976a2ab8243409d8e2ef048c4aa61deb`, Build ID `b3a4dcc4f3b45c41779f773c9295f20d7805ebf1`. `SHIFT_NATIVE_VULKAN_TRACE_RING=1` captures both EVENT_WRITE_SHD packets and source-1 interrupt IDs; no trace-only setting should be enabled in the retail run. A matching Android ARM64 compile-only DSO is in the adjacent `android-arm64/` directory; it was built with the compatible Android SDK snapshot, NDK r28c, and API 26, not executed on a device.

No root cause for the earlier `3381 -> 3375` stores is established yet. The replacement paired run below completed with the Linux artifact and P1 callback sampling, but Native stopped at head 3017 and did not reach that window. The stale/replayed-command question therefore remains open.

## Replacement paired run: provenance joined, regression not reached

The completed capture is preserved as [a compact audit report](../evidence/process2_native_queue_dispatch_pair_36aad927_20261028.json) and [a compressed raw archive](../evidence/process2_native_queue_dispatch_pair_36aad927_20261028_raw.tar.gz). The report includes input hashes and the archive hash. The original temporary capture root was `/dev/shm/nfs-shift-p1-gpu-dispatch-pair-36aad927-20261028`.

This run used the frozen Linux DSO above (`cf9ffc...61deb`, Build ID `b3a4...20ebf1`) for 360.591 seconds and finalized with GDB exit 0. Both runs reached Bink 281/281 and used matching host, runtime, XEX, and resource-manifest hashes. The input replay trigger fired, but the Native input gate was not observed; the comparison records no delivered Native input pulses and no Native scene transition. Xenos recorded 336 source-1 callbacks and two scene-state samples. These outcomes are not input-comparable past Bink.

The completed Native trace contains EVENT_WRITE_SHD IDs `0..3021` without gaps. For target `0x17AF4000`, all 1,508 stores advance by `+2`; there are no regressions, expansion-to-execution source-byte mismatches, or previous/after-value discontinuities. The final store is event 3021: generation 1, batch 1815 (`rptr=869`, `wptr=875`), ring `0x09752580`, packet ordinal 66, source IB `0x0973F480` + byte offset 344, raw words `[0xC0025800, 0x3, 0x17AF4002, 0xBC9]`, decoded head `3017` (`3015 -> 3017`). The `3381 -> 3375` window was not reached, so this trace neither identifies nor refutes the packet responsible for the earlier rollback.

The dispatch-ID join succeeds for one real Native callback. P1 recorded source 1 with `gpu_dispatch_id=4892`, queue head/tail `3013/3017`, registered callback `0x823A4758`, and CPU mask `0x04`. It joins to P2 PM4_INTERRUPT #819, source IB `0x0973C380` + byte offset 11924, packet ordinal 246 in ring batch `[866,869)`, outer wrapper `0x823B37B8`, CPU mask `0x04`, with a 2 ms timestamp delta. P2 logged 820 source-1 interrupts for this Native run, while P1's finalized events contain only that one callback and no dequeue/completion events. At the capture deadline P1 sampled the guest main thread in `sub_823B2AF0 -> sub_823B31A0 -> sub_823B33A0`; the ring worker was sleeping inside `RingWorkerLoop`. This establishes that ID propagation works for the joined callback, but it does not explain the subsequent missing P1 callback/queue records or the earlier head regression.

Next, Process 1 needs to inspect the Native-only post-Bink callback discrepancy using the archived event and GDB logs. For the head question, the required replay must continue beyond software head 3381 and retain the exact EVENT_WRITE_SHD provenance already captured here. Do not classify a guest packet as stale or alter negative-value handling until such a packet is observed and joined to its ring/IB execution order.

## Extended Native-only capture: long WAIT_REG_MEM stall

A 420-second Native-only follow-up using the same frozen DSO is preserved in [its audit report](../evidence/process2_native_wait_420_36aad927_20261028.json) and [raw archive](../evidence/process2_native_wait_420_36aad927_20261028_raw.tar.gz). It is not a paired Xenos comparison. The run finalized with GDB exit 0 after 421.338 seconds, reached Bink completion, and ended with the Native input gate unobserved and `state_348=1`.

The Native trace contains EVENT_WRITE_SHD IDs `0..2743`, with no gaps or expanded-byte mismatches. All 1,369 stores to `0x17AF4000` are `+2`, ending at head 2739. This again does not reach the earlier 3381 rollback window.

At ring batch `[rptr=32,wptr=35)`, generation 1, the worker executed WAIT_REG_MEM packet 250 in IB `0x0969E640` + byte offset 11972. It polls guest address `0x1B964004` through encoded address `0x1B964006`, memory mode, endian 2, compare 3 (equal), reference 0, mask `0xFFFFFFFF`, interval `0x100`. The observed value was 1, so the condition was false through poll 7000 at 7.868 seconds. The initial P2 log does not retain this WAIT packet's raw words or the later memory transition.

The ring did not emit another event until 16:26:15.678 +0300, when it processed EVENT_WRITE_SHD #2740/#2741 in that same root batch and #2742/#2743 in the next batch. These advance the software head `2735 -> 2737 -> 2739`. The title logged hard termination at 16:26:16.151, within 0.473 seconds of that burst and at the 420-second capture deadline. Thus ring execution left the wait, but the captured evidence does not show who changed the polled memory; treat this as shutdown-tail activity rather than proof of normal guest progress. Other WAIT_REG_MEM samples in this run commonly became true within 4–11 polls, making this batch's long delay an outlier. The GDB snapshot has the guest main thread blocked in a mutex lock and no recorded dequeue/completion or scene transition.

The interrupt join also repeats once: P1 callback ID 14787 at queue head/tail `2735/2741` joins to P2 source-1 PM4_INTERRUPT #704, packet ordinal 246, IB `0x0969E640` + byte offset 11924 in batch `[32,35)`, wrapper `0x823B37B8`, CPU mask `0x04`, timestamp delta 2 ms. P2 recorded 705 source-1 interrupts; P1 recorded one callback and no dequeue/completion. This reinforces the post-Bink callback discrepancy for Process 1, but neither the interrupt join nor the wait sample identifies the prior `3381 -> 3375` packet.

The follow-up instrumentation added after this capture logs each memory-mode WAIT_REG_MEM entry under `SHIFT_NATIVE_VULKAN_TRACE_RING=1`, including six raw PM4 words and decoded fields. It also records the final raw/decoded value, poll count, elapsed time, and packet provenance when the wait completes, or records the same last sample if ring shutdown interrupts it. Without the trace setting, the existing first-16 wait-entry limit remains. The added records are diagnostic-only and do not change wait or EVENT_WRITE_SHD execution semantics; a fresh capture with the rebuilt DSO is still required to determine who releases the long wait.

## Follow-up diagnostic builds

The updated logger was built from source commit `7aa414ab31e1d8035f074ca8c5226e86c48f3a55`. The frozen Linux x86-64 DSO is `/home/pes/work/process2-wait-regmem-shutdown-aware-7aa414ab/linux-x86_64/librexgpu-shift-native.so`, SHA-256 `d8ee49c10c4650d2bce5e9f5c124b62d0ea25c8b8bc126f1360967a2e6db230c`, Build ID `195c9e7de23289d6039cd26ef4d336af6a733291`. It uses the retail-lwsync SDK provider commit `923a7a03575b43f6c22ee97c376077a7022d17d6`.

An Android ARM64 compile-only artifact is at `/home/pes/work/process2-wait-regmem-shutdown-aware-7aa414ab/android-arm64/librexgpu-shift-natived.so`, SHA-256 `8cb8fe68a55708acd7c17d3b9024e9450e69c230bf26a8c531d96f345f1b3a8f`, Build ID `845cd69356797dbe3cfd32237d28a802a6778426`. It targets API 26 with NDK r28c and the compatible ReXGlue v0.10.0 Android SDK snapshot. It was not run on a device and was not built against the Linux retail-lwsync SDK.

Verification on this source passed 2/2 plugin CTests (`rexgpu_shift_native_factory_check`, `rexgpu_shift_native_live_ring_write_trace_check`), 2/2 guest-ring/draw-input CTests, and 13 Python auditor/interrupt-join tests. The build identities and commands are recorded in the adjacent external artifact `manifest.json`. The 420-second WAIT observation above predates these binaries; no runtime conclusion is attributed to the new logger until a fresh run captures its records.
