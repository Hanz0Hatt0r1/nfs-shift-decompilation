# Menu Setup event dequeue and downstream repeat — v112

Date: 2026-10-29
Scope: read-only original Xbox 360 guest execution under Xenos emulation and
Shift Native Vulkan.

## Result

The first guest condition that keeps Menu Setup in state 2 is confirmed: the
attached `MainMenu` scene gate at `scene+8` remains `1`. In
`sub_82FD5658`, state 2 calls the original gate getter (`sub_821F4110`); a
nonzero result retains state 2, while zero permits the original transition
helper `sub_82FD4418(setup+4, 3)`. Initialization sets the gate to one through
`sub_82DD9020`. Neither v112 run called the corresponding clear method
`sub_82DD8FF8`, and the field stayed one. This locates the immediate guest
blocker. The callback or condition that should clear the gate remains
unresolved.

The Start/A inputs take a separate path from the sampled
`sub_822E1910` service queue. Both backends delivered the same Start/A/Start
edges to the original handler `sub_8230A8E0` (event codes `0x30010400`,
`0x30010c00`, `0x30010400`) and invoked the same action-object consumers,
`sub_822EF7B0` and `sub_822F7EC8`. All 27 sampled action call/return signatures
matched between backends; the numeric status values and pointer-return
meaning are preserved as observations, not assigned new semantics. The GUI
event queue had 70 constructor calls and 9 opens, but zero enqueue calls and
zero direct appends in each run. No Start/A-correlated `sub_822FDCE0`
frontend-dispatch sample was recorded; its observed calls belong to the
separate worker completion path.

The three input event snapshots preserve all 16 event-object words, the
predicate object fields, the `r3`–`r10` and `r30`–`r31` snapshots, and the
caller LR. These fields match between both backends in both v112 pairs. The
read-only watch on event `+0x20` also recorded 138 original writes per run;
the evidence retains the button, guest field, caller LR, and before/after
values for each write.

For the service queue, `sub_822E1910` returned success (`r3=1`) with a type-2
event object. Its caller resumes at guest PC `0x822fdfb8` inside
`sub_822FDCE0`; the saved PPC context `r3` changes from 1 to 5, and the next
observed helper call is `sub_8223CE40(r3=5)`, which returns with `r3=5`. The
subsequent `sub_822FE160` call receives event type 2, callback
`0x822e8678`, and the dequeued event object; the nested `sub_822E8678` callback
returns with `r3=0` in the samples. This establishes the executed chain and
the value passed onward, but not the high-level meaning of 5. The worker
completion event is not the Start/A input event and does not establish the
missing scene-clear callback.

The first v112 Xenos/Native pair had different service-queue frequencies. A
second Xenos run with the same capture setup matched the existing Native run
across all normalized trace fields. Xenos v312 and v316 also differed from one
another in successful dequeue/callback counts while preserving the same
input, action results, state, gate, and GUI queue structure. Together with the
earlier v108/v109 reversal of which backend dequeued first, this does not
support a reproducible GPU-specific cause. No Process 2 defect is filed from
these samples.

## Paired captures

| | Xenos v312 | Native v315 | Xenos repeat v316 |
|---|---|---|---|
| Run | `nfs-shift-p1-menu-dispatch-v112-v312-xenos-20261029` | `nfs-shift-p1-menu-dispatch-v112-v315-native-20261029` | `nfs-shift-p1-menu-dispatch-v112-v316-xenos-20261029` |
| XEX SHA-256 | `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58` | same | same |
| Host SHA-256 | `ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178` | same | same |
| ReXGlue runtime SHA-256 | `693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd` | same | same |
| GPU plugin SHA-256 | `8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de` | `fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490` | same as v312 |
| State-2 updates | 65 | 65 | 65 |
| Input edges | Start 5/17, A 21/33, Start 37/49 | same | same |
| Post-pulse settle updates | 16 | 16 | 16 |
| Successful type-2 dequeues | 4 | 3 | 3 |
| Nested callbacks | 11 | 14 | 14 |
| Scene gate | `0→1`, then stays 1 | `0→1`, then stays 1 | `0→1`, then stays 1 |
| GUI enqueue / direct append | 0 / 0 | 0 / 0 | 0 / 0 |
| Probe guest-memory writes | none | none | none |
| GDB exit | 0 | 0 | 0 |

v316 Xenos and v315 Native had identical normalized input edges, action
consumer outcomes, successful dequeue signatures, saved-context writes,
nested-callback signatures, gate values, and GUI queue structure. Their GUI
queue processing call totals were 58 and 59 respectively; these scheduler
call counts are retained separately and are not treated as a scene-state
divergence. The v312 Xenos run had 38 processing calls.

All runs used the same game-data root:
`/home/pes/work/process2-retail-isolated-irq-20261023/game-data`. Runner SHA-256:
`aee764f1e908bcacf2b2b6d345559205ffbabe064bd4e345302647ca3fc64e05`. Trace
SHA-256:
`71bb57d5f81108d42f35685aad187d47244f4f0c1b289fef6b6a8eae342e86f0`. The
full GDB logs remain outside Git; the evidence file records their hashes and
normalized captured fields. No game binary, game resource, or full log was
added to the repository.

## Verification and artifacts

- Machine evidence and both pair outputs:
  [`xbox360_linux_menu_setup_event_dequeue_downstream_repeat_v112_20261029.json`](../evidence/xbox360_linux_menu_setup_event_dequeue_downstream_repeat_v112_20261029.json)
- Read-only capture wrapper:
  [`capture_linux_menu_setup_frontend_worker_gate_v112.py`](../tools/xbox360/capture_linux_menu_setup_frontend_worker_gate_v112.py)
- GDB trace:
  [`trace_linux_menu_setup_frontend_worker_gate_v112.gdb`](../tools/xbox360/trace_linux_menu_setup_frontend_worker_gate_v112.gdb)
- Pair comparator:
  [`compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py`](../tools/xbox360/compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py)
- Focused tests:
  [`test_compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py`](../tools/xbox360/test_compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py) — 5 passed.
- Prior static scene-gate condition and state-transition evidence:
  [`XBOX360_MENU_SETUP_SCENE_GATE_METHODS_PAIR_V89_20261029.md`](XBOX360_MENU_SETUP_SCENE_GATE_METHODS_PAIR_V89_20261029.md)
- Earlier dequeue first-difference repeat showing direction reversal:
  [`xbox360_linux_menu_setup_dequeue_gate_repeats_v108_v109_20261029.json`](../evidence/xbox360_linux_menu_setup_dequeue_gate_repeats_v108_v109_20261029.json)

Python compilation, focused tests, and both v112 pair comparisons passed. No
runtime build was needed: this change adds only read-only tracing analysis,
comparison, tests, and evidence. No guest logic or renderer code changed.
The function-level REA analysis request against the 78 MB host ELF did not
finish and was closed without a function dossier; no completeness claim is
made for static xrefs. The gate condition is supported by the live PPC-context
trace and the previously byte-checked generated-code contract.

## Next step

Trace the registered scene callback chain from the accepted Start/A action
objects to `sub_82DD8FF8` or the state-transition helper. Capture the callback
registration object, its vtable/slot, and the first original predicate that
prevents invocation. Keep the guest state read-only. Reopen a Process 2 issue
only if a repeatable Native-only guest-visible difference appears.
