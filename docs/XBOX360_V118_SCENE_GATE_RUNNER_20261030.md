# Reproducing the v118 Menu Setup scene-gate frontier

Date: 2026-10-30
Lane: P1 (frontend). Related gate: X4 (frontend not reached).

## Summary

The evidence document
[`XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md`](XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md)
records the v118 runs only by hash:

| Artifact | SHA-256 recorded by the v118 doc |
|---|---|
| runner `capture_linux_menu_setup_callback_route_v118_20261029.py` | `f09c0f65a53ba92586a16b6e8b420c23efa451abfd10250a81cf8d7aaeeae24d` |
| trace `trace_linux_menu_setup_callback_route_v118_20261029.gdb` | `41e7b6232dabea9c0d8dcf00025b1b400c585bf8fe54f9ced4273307e4d3b753` |

**Those two files are not in Git and were not found on disk.** The v118 commit
(`488601bb1`) added only the evidence JSON, the pair comparator and their tests;
it did not add the capture pair itself. The original v118 runner/trace hashes are
therefore unreproducible as written and should not be cited as authoritative.

This document records what *is* reproducible, and pins the frontier facts with a
regression test so the prose can no longer drift from the data.

## What is reproducible today

The committed v112 capture pair already instruments every event family the v118
analysis relies on, on **both** backends:

- [`capture_linux_menu_setup_frontend_worker_gate_v112.py`](../tools/xbox360/capture_linux_menu_setup_frontend_worker_gate_v112.py)
  — backend switch `xenos` / `shift-native`, Start/A/Start schedule with
  `state2_update_index` timing, post-pulse settle.
- [`trace_linux_menu_setup_frontend_worker_gate_v112.gdb`](../tools/xbox360/trace_linux_menu_setup_frontend_worker_gate_v112.gdb)
  — emits `P1_STATE2_UPDATE`, `P1_MAINMENU_SCENE_GATE_METHOD_BREAKPOINTS_ARMED`,
  `P1_SCENE_GATE_WATCH_ARMED`, `P1_MAINMENU_SCENE_GATE_METHOD_CALL/RETURN`,
  `P1_SCENE_GATE_FIELD_WRITE`, `P1_GUI_QUEUE_CTOR_CALL/RETURN`,
  `P1_GUI_QUEUE_OPEN_CALL/RETURN`, `P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS`,
  `P1_RETAIL_CONTROLLER_EDGE_STATE`, `P1_RETAIL_INPUT_PREDICATE`,
  `P1_ACTION_CONSUMER_CALL/RETURN`, `P1_STARTUP_MEMORY_FILL_ENTRY`.

In other words the v118 frontier **is** reproducible from the v112 tooling; the
v118 hash pair is a lost convenience wrapper, not a lost capability. Any future
capture should be committed in the same change that cites it.

## The reader

[`analyse_menu_setup_scene_gate_run_20261029.py`](../tools/xbox360/analyse_menu_setup_scene_gate_run_20261029.py)
turns a run directory (`gdb.log` + `run_metadata.json`) into one JSON summary:

```bash
python3 tools/xbox360/analyse_menu_setup_scene_gate_run_20261029.py \
    /home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-native-retry-20261029
```

It is read-only and reports `unknown` rather than zero wherever the trace does
not instrument a path.

## Frontier facts, reproduced independently

[`test_analyse_menu_setup_scene_gate_run_20261029.py`](../tools/xbox360/test_analyse_menu_setup_scene_gate_run_20261029.py)
asserts the numbers below against the raw run directories. They were recomputed
on 2026-10-30 from the logs themselves, not copied from the prose.

| Fact | Native (`fd615ada…`) | Xenos (`8b5abe7a…`) |
|---|---|---|
| backend | `shift-native` | `xenos` |
| GDB exit | 0 | 0 |
| probe guest-memory writes | none | none |
| Menu Setup state-2 updates | 20 | 20 |
| first / last state-2 update | 77.460 s / 110.168 s | 76.766 s / 110.052 s |
| scene gate set calls (`sub_82DD9020`) | 1 | 1 |
| scene gate clear calls (`sub_82DD8FF8`) | **0** | **0** |
| scene gate field writes | 1 (`0xbf054ad8`, `0`→`1`, 76.303 s) | 1 (`0xbeebc078`, `0`→`1`, 75.644 s) |
| GUI queue ctor calls | 70 | 70 |
| GUI queue opens | 9 | 9 |
| GUI queue polls | 16 | 16 |
| retail input predicate samples | 36 (`=1`) | 36 (`=1`) |

Artifact identities in both `run_metadata.json` files:
XEX `8c86a34f…`, host `ff4278b3…`, runtime `693abc48…`.

## The one wording change this forces

Earlier notes said the GUI event queue had "zero enqueues". That is **not
observable** from these captures: the trace breakpoints the dequeue/poll side,
and no enqueue event family exists. The analyser therefore reports

```
enqueue_evidence: "not instrumented: the trace observes GUI queue polls only;
absence of enqueue events cannot be read as zero enqueues"
```

The defensible statement is: *the menu GUI queue was constructed 70 times, opened
9 times and polled 16 times in the captured window, and the capture instruments
no enqueue path.* Whether the guest enqueues nothing, enqueues into a different
object, or enqueues through an uninstrumented function remains open — which is
exactly what `docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md` H1/H2 must settle with
a v119 capture that adds an enqueue-side probe **and** a positive control.

## Next step

The v119 capture in `docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md` must add the
enqueue-side instrumentation together with a positive control (a known-productive
queue, or an injected host-side enqueue in a fixture build — never a guest-memory
patch). Until that control exists, "0 enqueues" stays classified as
*uninstrumented*, not as a measured zero.
