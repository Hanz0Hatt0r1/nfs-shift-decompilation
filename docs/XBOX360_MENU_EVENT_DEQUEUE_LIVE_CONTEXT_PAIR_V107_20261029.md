# Menu event dequeue live-context pair — v107

Date: 2026-10-29
Scope: original Xbox 360 guest execution under Xenos emulation and Shift Native Vulkan.

## Result

The v105/v106 deferred continuation probe was not a reliable snapshot of the
same queue-pop return: it installed a breakpoint at an address where the
thread was already stopped. V107 now records the live PPC context inside the
`sub_822E1910` return callback and arms one write watch on that context's `r3`.

The Xenos v301 and Native v298 runs used the same retail XEX, host executable,
ReXGlue runtime, runner, trace, game-data root, and Start/A/Start schedule. Both
completed 49 Menu Setup state-2 updates. All eight shared queue-pop sample
keys matched. At each matched immediate return, the live `$r14` context was
the saved PPC context and its `r3` matched the function's return value.

The one-shot write watch observed the same change in both runs:

| Observation | Xenos v301 | Native v298 |
|---|---|---|
| Guest caller LR | `0x822fdf88` | `0x822fdf88` |
| `r3` before / after | `1 → 5` | `1 → 5` |
| Host write site | `sub_822FDCE0 + 3271` | `sub_822FDCE0 + 3271` |
| Probe guest-memory writes | none | none |

The host instruction immediately before the watchpoint stop is
`movq $0x5,(%r14)`, which writes the new value into the live PPC context. The
initial `r3=1` therefore reached the caller; subsequent original guest execution
changed it. This rules out interpreting the v106 deferred `r3=0` sample as
proof that the event was discarded. Its precise later re-entry remains a probe
timing inference, not a guest-logic finding.

No backend-specific queue or live-context divergence was found. This does not
show that Start/A advances the menu: both games remained in Menu Setup state 2.
It also does not establish the semantic meaning of the later `r3=5` value.

## Run identity

| | Xenos v301 | Native v298 |
|---|---|---|
| Run directory | `/home/pes/work/nfs-shift-p1-menu-dispatch-v107-v301-xenos-20261029` | `/home/pes/work/nfs-shift-p1-menu-dispatch-v107-v298-native-20261029` |
| Duration | 152.140 s | 129.448 s |
| State-2 updates | 49 | 49 |
| Start/A/Start | 5/17, 21/33, 37/49 | 5/17, 21/33, 37/49 |
| GDB exit | 0 | 0 |

| Artifact | SHA-256 |
|---|---|
| Retail XEX | `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58` |
| Host executable | `ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178` |
| ReXGlue runtime | `693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd` |
| Xenos plugin | `8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de` |
| Native Vulkan plugin | `fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490` |
| v107 runner | `a79f84a503e3aaca08ec9002ec1ba3a9aabf697a181b482ad5555485167fa95a` |
| v107 trace | `1ada8339461a17bf33f6f89b592d6cca35cc10f0e41a1d3c9aa8ac1781aa63e5` |

The two runs shared 8 queue-pop sample keys with no outcome differences. The
resource root is the previously verified 2,098-file manifest
`7d8ee2079d50787832526df9cadf492497e6d42c02ce6748eb940db7a1fd63cd`.

## Verification and artifacts

- Pair evidence: [`xbox360_linux_menu_worker_gate_pair_v107_xenos_v301_native_v298_20261029.json`](../evidence/xbox360_linux_menu_worker_gate_pair_v107_xenos_v301_native_v298_20261029.json)
- Comparator: [`compare_linux_menu_setup_frontend_worker_gate_pair_v107_20261029.py`](../tools/xbox360/compare_linux_menu_setup_frontend_worker_gate_pair_v107_20261029.py)
- Focused tests: [`test_compare_linux_menu_setup_frontend_worker_gate_pair_v107_20261029.py`](../tools/xbox360/test_compare_linux_menu_setup_frontend_worker_gate_pair_v107_20261029.py) — 2 passed.
- Capture: [`capture_linux_menu_setup_frontend_worker_gate_v107.py`](../tools/xbox360/capture_linux_menu_setup_frontend_worker_gate_v107.py)
- Trace: [`trace_linux_menu_setup_frontend_worker_gate_v107.gdb`](../tools/xbox360/trace_linux_menu_setup_frontend_worker_gate_v107.gdb)

No runtime, guest logic, or renderer code was changed or rebuilt. The capture
and comparator were syntax-checked; the focused comparator tests passed.

## Next step

Follow the original guest path from the post-pop branch through the callback
that consumes the dequeued object, correlating its event fields with the Start
and A action consumers. Keep the return-context watch local to the trace and
compare any new branch or memory changes across both backends before assigning
a renderer issue to Process 2.
