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

No root cause for the earlier `3381 -> 3375` stores is established yet. The next required evidence is a fresh paired run using the Linux artifact above, with the complete ring trace and P1's callback getter sampling in the same run. A logged literal write of 3375 would identify the packet that performed it; deciding whether it is stale/replayed or an original guest command still requires joining its source coordinates to ring/IB processing and the paired backend trace.
