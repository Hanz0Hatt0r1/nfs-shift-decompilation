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

The new [dispatch join utility](../tools/xbox360/join_linux_source1_gpu_dispatches_20261028.py) matches Process 1 callback IDs to Process 2's `PM4_INTERRUPT source=1` rows, then preserves the interrupt's generation, batch, packet ordinal, and source coordinates beside linked worker events. Process 2 confirmed that `EVENT_WRITE_SHD` rows carry those coordinates but no dispatch ID, so packet-level navigation uses the interrupt coordinates and must not claim an earlier store caused a worker transition without additional evidence.

The targeted regressions check the explicitly typed dynamic-symbol call, unavailable-symbol caching, zero IDs, helper errors, callback scope lookup, exact queue-slot matching, map eviction, trace-field presence, and the dispatch joiner's matched/unmatched IDs. The pytest wrapper in `tests/test_process1_gpu_dispatch_trace.py` includes both tests in CI. A real GDB smoke check against a stripped shared object confirmed the typed function call reads the active thread-local ID; this GDB build lacks the Python minimal-symbol lookup API, so the trace relies on GDB expression resolution instead. Both embedded GDB Python blocks compile. No new game capture is claimed: the currently available Native DSO (`d01405cca2dcc8d67413b3fd1ee9bebdd7db72cc3656849d57f013d3202d6d90`) does not export the getter, and Process 2's source tree is still changing. The first capture must use a frozen DSO that exports the getter and must record that DSO's build ID, hash, and source commit.

## Evidence and reproduction

- [Paired machine-readable record](../evidence/xbox360_linux_native_14841319_paired_physical_counter_20261028.json), including raw hashes, per-backend state, input comparability, queue-write histograms, and the first counter mismatch.
- [Paired Native callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_paired_source1_join_inputs_20261028.jsonl.gz): 639 guest source-1 callbacks and 1,392 source-1 PM4 interrupts, 2,031 rows total, SHA-256 `f9a20afc9adba5013a0200c75f76953e293a0c4b5a6fb5101ce6dea977c8d956`.
- [Native-only machine-readable record](../evidence/xbox360_linux_native_14841319_physical_counter_replay_20261028.json) and [callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_source1_join_inputs_20261028.jsonl.gz): 377 callbacks and 1,094 interrupts, 1,471 rows total.
- [Capture and comparator](../tools/xbox360/capture_linux_gpu_backend_pair_20261028.py) and [source-1 archive exporter](../tools/xbox360/export_linux_source1_interrupt_join_inputs_20261028.py).

The archive exporter rejected malformed records in both captures; `gzip -t` and its deterministic-export regression passed. The pair and comparator regression tests, trace-capture regression, Python compilation, and `git diff --check` passed. No selected frame-622 geometry/shader dump was produced.

## Next Process 1 / Process 2 checks

1. Process 2 should audit why Native `RingWorkerLoop()` writes `-6` head changes while Xenos advances the same watched software head only by `+2` in the paired capture. Align those writes to ring batch indices and guest memory before deciding whether they violate the guest queue contract.
2. Reproduce the head-boundary run with Process 2's per-packet source-IB/batch trace and the new guest queue correlation, after Process 2 provides a frozen DSO exporting the dispatch-ID getter. Join by `gpu_dispatch_id`; timestamp proximity alone does not prove causality.
3. Trace the exact original scene-state writers and frontend callback after the observed state `1 -> 0` cleanup. The Start/A edges are now confirmed through XAM and the controller object, but the action dispatcher and scene-gate re-entry remain unconfirmed.
4. Continue to the visible, interactive main menu and first controllable race. Neither has been reached in these captures.
