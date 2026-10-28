# Process 1 comparative frontier — 2026-10-28

## Scope and identities

This report compares original Xbox 360 game execution under Xenos emulation and Process 2's Native Vulkan plugin. It records guest state, software queue head writes, manager completion counter operations, interrupts, and input. No guest runtime, original game logic, or Vulkan renderer implementation was changed.

Both runs used the same retail `default.xex` (SHA-256 `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`), Linux host (SHA-256 `ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178`), ReXGlue runtime (SHA-256 `693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd`), game-data manifest (SHA-256 `f26a6709fa57fc36e85b75578ac05563bc8aa12f3641faf045f6bc8cef9fc1f6`), and SDK revision. Native plugin commit `14841319` had SHA-256 `f794272592ea955c66f00a11c784a56bc77baa6f2205c83fdad8269fdac5443f` and Build ID `ebbb619ab5a5142d3392b62867b88848744492c0`; Xenos plugin SHA-256 was `19053b691d7d1f8f17bbe3e90be38ba3acc60439cbe5c1dfcad271e07b47ce43`.

## Paired retail result

A 135-second paired replay completed both GDB traces with exit 0. Both backends reached Bink 281/281. Xenos reached the instrumented scene gate and its XAM returns contained Start `0x0010` and A `0x1000`; the retail controller trace recorded both edges. Native did not reach the gate, and its XAM returns contained only zero masks. Inputs after the gate therefore cannot be compared between the two runs.

After the common initial scene states, Xenos re-entered the scene sequence and reached the gate. Native's observed scene manager changed from state 1 with four populated child slots to state 0 with empty slots, then did not re-enter the gate during the pair. A separate Native-only replay on the same plugin reached the gate once and observed the Start edge, but did not observe A `0x1000`; the paired result shows that Native's gate outcome is not yet reproducible.

The physical alias watch captured writes to guest software queue head `0xB7AF4000` through host address `0x217AF4000`:

| Backend | Writes | Head deltas | Writer |
| --- | ---: | --- | --- |
| Xenos | 477 | `+2`: 477 | `CommandProcessor::ExecutePacketType3_EVENT_WRITE_SHD` |
| Native Vulkan | 830 | `+2`: 713; `-6`: 114; `-18`: 1; `-8`: 1; `+10`: 1 | `ShiftNativeGraphicsSystem::RingWorkerLoop()+26867` |

The counter at `manager+11012` had 3 increments and 116 decrements in Native, ending at signed `-113`. Xenos had 27 increments and 26 decrements, ending at `1`. Native stopped with head `3381`, tail `3401`, and predicate byte `0x14` (completion bit `0x02` clear); Xenos stopped with head `4759`, tail `4769`, and predicate `0x04`.

The first counter operation mismatch followed five common writes. Native `sub_823B85D0` decremented `1 -> 0` at 81.450 s for token `0xC0000000`, linked by the trace to parent dequeue 760. Xenos `sub_823B31A0` incremented `1 -> 2` at 81.695 s for a tag-35 producer record. This is a 245 ms ordering difference; it does not identify a causal GPU interrupt or establish that either backend's operation is correct.

## Separate Native-only replay

The same plugin also completed Bink 281/281 and reached the scene gate in one 135-second Native-only replay. Its combined head/counter capture recorded 537 physical-alias head writes: 502 were `+2` and 35 had other deltas. The head repeatedly moved `3333 -> 3327 -> 3329 -> 3331 -> 3333`. The manager counter received 12 increments and 40 decrements, ending at `-28`. Start reached the retail controller edge; the sequence harness issued Start/A/Start, but no XAM return contained A `0x1000`. The scene children cleared after Start. This run did not confirm frontend action dispatch or a visible menu.

Together, the paired and Native-only runs show variable Native scene-gate behavior on the same plugin. They do not show a stable Native main menu.

## Raw Native EVENT_WRITE_SHD and immediate input replay

An additional decoder-entry trace used the frozen Native plugin SHA-256 `f794272592ea955c66f00a11c784a56bc77baa6f2205c83fdad8269fdac5443f` (Build ID `ebbb619ab5a5142d3392b62867b88848744492c0`, source commit `14841319`). It recorded every raw 16-byte `EVENT_WRITE_SHD` packet targeting guest physical `0x17AF4000` and sampled the host alias immediately before decoding. A clean 320-second Native run ended just below the earlier regression range: the final packet value was `3349`, with sampled head `3347`. A second run crossed that range and retained strictly `+2` packet values through `3971`; however, GDB exited 1 after the trace script was edited while that run was still reading it. Its runner log preserves the raw packet records, but it is partial evidence rather than a clean repeat. Around the reported boundary, packet values were `3377, 3379, 3381, 3383, 3385`; each `head_before` matched the previous packet value, and no regression was observed. This does not disprove the separate `3381 -> 3375` observation.

A separate clean 360-second Native run injected Start/A/Start immediately after Bink completion. The original game reached Bink `281/281`; the input probe observed XAM masks `0x0010` and `0x1000`, and the original controller object recorded both rising edges. The scene manager briefly had state `1` with populated children, then returned to state `0` with empty children. The frontend input gate did not recur, so this confirms input delivery but not action consumption or a main menu.

The long captures exposed a clock-origin bug in the replay harness: GDB and the outer runner started their monotonic timers at different times. Bink-triggered input scheduling now compares their shared wall-clock epoch values, and a regression covers nonzero startup skew. Partial-log recovery also preserves raw `EVENT_WRITE_SHD` records, and XAM returns are sampled for six seconds after host input changes so a missing scene gate no longer hides button masks.

See [head-boundary and immediate-input evidence](../evidence/xbox360_linux_native_event_write_shd_head_frontier_20261028.json) for identities, hashes, packet rows around `3381`, event histograms, and capture limitations.

## GPU dispatch-ID guest-worker correlation

The Process 1 GDB trace now samples the Native plugin's exported `shift_native_gpu_trace_dispatch_id_v1()` at guest callback `sub_823B37B8` for `source=1`. It carries that ID through synchronous guest producer/enqueue records, binds IDs to the queue tuple `(queue, producer_index, slot_value)`, and transfers the ID to dequeue, completion, `manager+11012` counter writes, queue field writes, worker field writes, and event waits. The in-memory queue map is capped at 16,384 records; eviction totals and getter availability/errors are written to `events.json`. The trace does not infer causality from timestamps.

The new [dispatch join utility](../tools/xbox360/join_linux_source1_gpu_dispatches_20261028.py) matches Process 1 callback IDs to Process 2's `PM4_INTERRUPT source=1` rows, then preserves the interrupt's generation, batch, packet ordinal, and source coordinates beside linked worker events. It checks the mapped runtime/plugin hashes and the interrupt log's recorded same-run SHA-256 against run metadata. Process 2 confirmed that `EVENT_WRITE_SHD` rows carry those coordinates but no dispatch ID, so packet-level navigation uses the interrupt coordinates and must not claim an earlier store caused a worker transition without additional evidence.

The targeted regressions check the explicitly typed dynamic-symbol call, unavailable-symbol caching, zero IDs, helper errors, callback scope lookup, exact queue-slot matching, map eviction, trace-field presence, and the dispatch joiner's matched/unmatched IDs. The pytest wrapper in `tests/test_process1_gpu_dispatch_trace.py` includes both tests in CI. This GDB build lacks the Python minimal-symbol lookup API, so the trace relies on GDB expression resolution instead.

The first capture attempt with an exported getter used Native DSO SHA-256 `2a0b63a6c6e4563818dca48bb24664c627e555aec10c864c5d951198de231a9a`, Build ID `8932d691d1e9d5f0cdfe57590a2f9829b5c62477`, and Process 2 source commit `b1855edbeafd426364d3711e3776aa8b7ee80dfd`; the SDK provider commit was `923a7a03575b43f6c22ee97c376077a7022d17d6`. The shared XEX, host, runtime, Xenos plugin, and resource manifest matched the identities above. The Xenos run completed 367.4 seconds with GDB exit 0; Native stopped after 81.278 seconds with GDB exit `-6` and partial-log recovery. Both observed Bink 281/281, but the Xenos trigger missed the first Start XAM poll and only A `0x1000` was observed. Native reached the first source-1 callback with queue head `2573`, tail `2577`, predicate `0x14`, and manager counter `0`; GDB aborted while calling the getter with `keep_going_pass_signal: Assertion ecs->event_thread->ptid == inferior_ptid`. This pair is retained at `/dev/shm/nfs-shift-p1-gpu-dispatch-pair-20261028` as a failed/partial capture, not valid comparative evidence.

The trace now temporarily sets GDB `scheduler-locking on` around the typed getter call and restores the prior mode in `finally`. A multithreaded GDB smoke returned thread-local ID `0x5a17`, restored the original `replay` mode, and showed a worker-thread breakpoint did not interrupt the call. This validates the debugger workaround in isolation; it does not yet prove that a full game capture completes. The P1 PM4 parser accepts `dispatch_id` on either side of `generation`; regressions cover both field orders.

Process 2 provided a replacement frozen Native DSO at `/home/pes/work/nfs-shift-process2-eventwrite-dispatch-36aad927/linux-x86_64/librexgpu-shift-native.so`, SHA-256 `cf9ffc3775db83c874d69da6dc3e6995976a2ab8243409d8e2ef048c4aa61deb`, Build ID `b3a4dcc4f3b45c41779f773c9295f20d7805ebf1`, source commit `36aad9274f6c39be9c60028da085300fcafeccf8`, and SDK commit `923a7a03575b43f6c22ee97c376077a7022d17d6`. I verified its hash, Build ID, and exported getter. With the plugin's `SHIFT_NATIVE_VULKAN_TRACE_RING=1` mode, same-run PM4 source-1 dispatch IDs and `EVENT_WRITE_SHD` provenance are available.

## Latest paired capture: early Native stop at queue head 3017

The completed one-repeat capture is in `/dev/shm/nfs-shift-p1-gpu-dispatch-pair-36aad927-20261028`. Both runs used the same XEX (`8c86a34f…`), host (`ff4278b3…`), runtime (`693abc48…`), resource manifest (`f26a6709…`), and SDK commit (`923a7a03…`). Xenos plugin SHA-256 was `19053b69…`; Native plugin SHA-256 was `cf9ffc37…` (Build ID `b3a4dcc4…`, P2 source commit `36aad927…`). GDB finalized both traces with exit 0: Xenos ran 371.317 seconds and Native 360.591 seconds. The P1 trace-script SHA-256 recorded for the run is `d1aa0f26294e4a234f5b8db2c8dbc833912dcd4cfdc9c555390124a2b2bad43a`.

Both runs completed Bink 281/281 (Xenos at 57.458 seconds, Native at 69.358). Xenos then entered scene-manager state 1 at 57.944 and cleared to state 0 at 58.209; its final state remained 0. Native's final snapshot was state 1 with `update_count_356=312` and four nonzero child words. Its GDB trace recorded one post-Bink source-1 callback and no scene-state callback, dequeue, completion, queue-field write, or XAM return after that point. The first callback sampled queue head 3013, tail 3017, predicate `0x14`, and manager counter 0. The stop-time guest stack was `sub_823B2AF0 → sub_823B31A0 → sub_823B33A0 → sub_823A4E48`; the guest GPU worker was in `RingWorkerLoop()`'s `nanosleep`. This locates the Native stop but does not establish why the original guest path waits there.

The cross-backend producer trace has a first-call candidate: both runs recorded producer call 1, tag 11, caller LR `0x823B342C`, routed through `sub_823B2AF0`. Xenos' four record words were `[0, 0, 0xC0000001, 0]`; Native's were all zero. The record layout and causal link to the later wait remain unverified, so this is not classified as a runtime defect yet.

The exact Native callback/PM4 join matched P1 dispatch ID 4892 (`0x131C`) to P2 `PM4_INTERRUPT #819`, packet 246 in batch `[866, 869)`, source IB `0x0973C380 + 11924`, CPU mask `0x04`, callback `0x823B37B8`. The P1 and P2 event timestamps differ by 2 ms. This confirms the ID sampling and packet locator; it does not connect an earlier store causally to the guest wait. Across the three same-run Native log rotations, the P2 audit validated 3,022 `EVENT_WRITE_SHD` records (IDs 0–3021). All 1,508 writes to guest head `0x17AF4000` advanced by `+2`, with no missing event IDs, source-byte mismatch, value discontinuity, or regression. The final head was 3017, so this run did not reach the earlier 3381 regression window.

The same Start/A/Start sequence was scheduled after Bink for both backends. Xenos XAM returns contained Start `0x0010` and no A `0x1000`; Native produced no XAM returns after its queue stop. Input action consumption, the visible main menu, and a race remain unconfirmed. The machine-readable capture summary and hashes are in [paired source-1 dispatch evidence](../evidence/xbox360_linux_gpu_backend_comparison_source1_dispatch_20261028.json). The P2 ring trace captured `EVENT_WRITE_SHD` directly; the separate legacy P1 packet tap was disabled in this run.

## Native-only WAIT_REG_MEM frontier

Process 2 completed a separate 420-second Native-only replay with the same XEX, host, runtime, resource manifest, and frozen Native plugin (`36aad927`, SHA-256 `cf9ffc37…a61deb`). GDB exited 0 after the bounded capture. Bink completed 281/281 at 236.366 seconds. The run is not a paired Xenos comparison.

At 237.282 seconds, source-1 dispatch ID `0x39C3` entered registered guest callback `0x823A4758` (the ReXGlue callback entry is `0x823B37B8`). The guest software queue was at head 2735, tail 2741, target 2739, predicate byte `0x04`, and manager counter 0. The retail queue wait returned after 2 ms with the same head/tail and predicate byte `0x14`; no dequeue or completion event was recorded. The final scene snapshot was state 1 with update count 407. The configured Start/A/Start input sequence did not reach an XAM call or return, and the scene gate was not observed.

P2's ring trace recorded packet 250 in source IB `0x0969E640` at byte offset 11972: WAIT_REG_MEM polled guest address `0x1B964004` (poll address `0x1B964006`) with reference 0, mask `0xFFFFFFFF`, endian 2, compare 3. The captured guest dword was 1 and the plugin reported the predicate false from poll 0 through poll 7000, spanning 7.868 seconds. Process 2 reports from source inspection that this wait has no timeout, does not change the polled value, and exits only when the predicate succeeds or the worker shuts down; its exact source revision/location is pending. This makes the unwritten or late-written guest-memory value a concrete Process 2 investigation target.

An EVENT_WRITE_SHD packet from the same source IB and root-batch coordinates appears 0.473 seconds before capture teardown, but no execution-instance link or write to `0x1B964004` was recorded. Treat it as shutdown-tail activity; it does not show the guest wait released naturally. The bounded stop had no guest fault, and the GPU worker was in `RingWorkerLoop()` at `nanosleep`. Full fields and log hashes are in [Native WAIT_REG_MEM frontier evidence](../evidence/xbox360_linux_native_wait_reg_mem_frontier_20261028.json).

## Evidence and reproduction

- [Paired machine-readable record](../evidence/xbox360_linux_native_14841319_paired_physical_counter_20261028.json), including raw hashes, per-backend state, input comparability, queue-write histograms, and the first counter mismatch.
- [Paired Native callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_paired_source1_join_inputs_20261028.jsonl.gz): 639 guest source-1 callbacks and 1,392 source-1 PM4 interrupts, 2,031 rows total, SHA-256 `f9a20afc9adba5013a0200c75f76953e293a0c4b5a6fb5101ce6dea977c8d956`.
- [Native-only machine-readable record](../evidence/xbox360_linux_native_14841319_physical_counter_replay_20261028.json) and [callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_source1_join_inputs_20261028.jsonl.gz): 377 callbacks and 1,094 interrupts, 1,471 rows total.
- [Capture and comparator](../tools/xbox360/capture_linux_gpu_backend_pair_20261028.py) and [source-1 archive exporter](../tools/xbox360/export_linux_source1_interrupt_join_inputs_20261028.py).

The archive exporter rejected malformed records in both captures; `gzip -t` and its deterministic-export regression passed. The pair and comparator regression tests, trace-capture regression, Python compilation, and `git diff --check` passed. No selected frame-622 geometry/shader dump was produced.

## Next Process 1 / Process 2 checks

1. Process 2 should identify all writers to guest `0x1B964004`, then correlate the write value and time to WAIT_REG_MEM packet 250. The 420-second capture saw the predicate false for 7.868 seconds and did not record a natural release.
2. Capture the same WAIT_REG_MEM packet and guest-memory value under Xenos at a matched guest state. Do not infer that Xenos is correct solely because it progresses farther.
3. Continue the software-head `3381` investigation only with the queue-field and wait observations aligned to the relevant source packets; the paired capture stopped at 3017, and the 420-second Native-only follow-up did not establish a natural release.
4. Trace the exact original scene-state writers and frontend callback after the observed state `1 -> 0` cleanup. The Start/A edges are confirmed in earlier captures, but action dispatch and a stable scene-gate re-entry remain unconfirmed.
5. Continue to the visible, interactive main menu and first controllable race. Neither has been reached in these captures.
