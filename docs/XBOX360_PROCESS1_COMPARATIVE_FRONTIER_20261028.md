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

## Evidence and reproduction

- [Paired machine-readable record](../evidence/xbox360_linux_native_14841319_paired_physical_counter_20261028.json), including raw hashes, per-backend state, input comparability, queue-write histograms, and the first counter mismatch.
- [Paired Native callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_paired_source1_join_inputs_20261028.jsonl.gz): 639 guest source-1 callbacks and 1,392 source-1 PM4 interrupts, 2,031 rows total, SHA-256 `f9a20afc9adba5013a0200c75f76953e293a0c4b5a6fb5101ce6dea977c8d956`.
- [Native-only machine-readable record](../evidence/xbox360_linux_native_14841319_physical_counter_replay_20261028.json) and [callback/PM4 inputs](../evidence/xbox360_linux_native_14841319_source1_join_inputs_20261028.jsonl.gz): 377 callbacks and 1,094 interrupts, 1,471 rows total.
- [Capture and comparator](../tools/xbox360/capture_linux_gpu_backend_pair_20261028.py) and [source-1 archive exporter](../tools/xbox360/export_linux_source1_interrupt_join_inputs_20261028.py).

The archive exporter rejected malformed records in both captures; `gzip -t` and its deterministic-export regression passed. The pair and comparator regression tests, trace-capture regression, Python compilation, and `git diff --check` passed. No selected frame-622 geometry/shader dump was produced.

## Next Process 1 / Process 2 checks

1. Process 2 should audit why Native `RingWorkerLoop()` writes `-6` head changes while Xenos advances the same watched software head only by `+2` in the paired capture. Align those writes to ring batch indices and guest memory before deciding whether they violate the guest queue contract.
2. Join the first manager-counter mismatch to its exact source-1 interrupt and completion work item. The supplied same-run archive is timestamp/order input only; it does not prove causality.
3. Reproduce Native scene-gate entry with paired inputs, then verify whether A reaches XAM and the original action dispatcher. A green controller gate or a later frame alone is not proof of a working menu.
4. Continue to the visible, interactive main menu and first controllable race. Neither has been reached in these captures.
