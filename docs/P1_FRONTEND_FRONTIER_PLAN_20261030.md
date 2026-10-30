# Process 1 frontend frontier plan — Menu Setup scene gate clear

Date: 2026-10-30
Status: plan for the next work lane. This document does not claim the X4
blocker is solved; it states the question, the hypotheses, the exact probes,
and the static narrowing that must happen before any expensive capture.
Scope: original Xbox 360 guest execution under Xenos emulation and Shift
Native Vulkan, read-only probes only.

## 1. The one question this lane answers

Who is supposed to clear the `MainMenu` scene gate at `scene+8` — through
`sub_82DD8FF8` (scene vtable `0x8211e280` slot `+0x14`) or through the
state-transition helper `sub_82FD4418(setup+4, 3)` — and why does the code
that is supposed to do it never reach that call?

What is already established (v112, v107, v118):

- `sub_82FD5658` state 2 calls the gate getter `sub_821F4110` (`scene` slot
  `+0x08`). A nonzero result retains state 2; zero would permit
  `sub_82FD4418(setup+4, 3)`. See
  [`XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md`](XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md).
- Initialization sets the gate to one through `sub_82DD9020` (`scene` slot
  `+0x0c`), called from `sub_82FD53B8`'s path with caller LR `0x82fd5468`.
- The clear method `sub_82DD8FF8` was never entered in v112 or v118: the
  method breakpoints were armed at 0.855 s (Native) / 0.876 s (Xenos) and the
  only gate method entry is the `sub_82DD9020` set.
- Start/A edges reach the retail handler and the action consumers on both
  backends, but no frontend dispatch follows.

The lane is therefore narrow: it is *not* "find the main menu", it is "find
the producer of the `scene+8 = 0` write and the first original predicate that
stops it".

## 2. Facts extracted from the v118 logs (2026-10-29)

Sources (outside Git, read-only):
`/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-native-retry-20261029/`
and `/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-xenos-20261029/`
(`gdb.log`, `run_metadata.json`, `bin/logs/nfs_shift_001.log`).

Run identity (`run_metadata.json`, both): schema
`shift.xbox360.linux-menu-setup-state2-update-input-run.v1`; XEX
`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`; host
`ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178`; runtime
`693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd`; game data
`/home/pes/work/process2-retail-isolated-irq-20261023/game-data`;
`gdb_exit = 0`, `guest_memory_modified_by_probe = false`, duration 111.93 s
(Native) / 110.945 s (Xenos). Native plugin
`fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490`; Xenos
plugin `8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de`
(hashes as recorded in metadata; the Xenos hash is not re-derived here).

Capture contract as recorded: `runner_path
tools/xbox360/capture_linux_menu_setup_callback_route_v118_20261029.py`
(sha256 `f09c0f65a53ba92586a16b6e8b420c23efa451abfd10250a81cf8d7aaeeae24d`),
`trace_path tools/xbox360/trace_linux_menu_setup_callback_route_v118_20261029.gdb`
(sha256 `41e7b6232dabea9c0d8dcf00025b1b400c585bf8fe54f9ced4273307e4d3b753`).
Both captured 2026-10-29 21:22 local. Input schedule
`input_timing = {mode: state2_update_index, first_down_index: 2,
hold_updates: 2, gap_updates: 1}`, pulses Start 79.243 s, A 80.187 s,
Start 81.617 s (Native), `post_pulse_settle_updates 10/10`,
`post_pulse_settle_stop_reason settle_updates_observed`.

`gdb.log` line counts are identical between the two backends for every event
family below. The values that differ are guest heap addresses and timestamps;
no structural difference was found.

| Event family (v118) | Native | Xenos |
|---|---:|---:|
| `P1_STATE2_UPDATE` | 20 | 20 |
| `P1_STATE2_CALL` / `P1_STATE2_RETURN` | 75 / 74 | 75 / 74 |
| `P1_STATE2_DYNAMIC_CALL` | 36 | 36 |
| `P1_GUI_QUEUE_CTOR_CALL` | 70 | 70 |
| `P1_GUI_QUEUE_OPEN_CALL` | 9 | 9 |
| `P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS` | 16 | 16 |
| `P1_MAIN_MENU_EVENT_QUEUE_CALL` | 16 | 16 |
| `P1_SCENE_GATE_FIELD_WRITE` | 1 | 1 |
| `P1_MAINMENU_SCENE_GATE_METHOD_CALL` | 1 (`sub_82DD9020`) | 1 (`sub_82DD9020`) |
| `P1_WORKER_GATE_CALL` | 49 | 49 |
| `P1_ACTION_CONSUMER_CALL` / `RETURN` | 36 / 36 | 36 / 36 |
| `P1_ACTION_EVENT_FIELD_WRITE` | 37 | 37 |
| `P1_RETAIL_INPUT_PREDICATE` | 36 | 36 |
| `P1_DEQUEUE_DOWNSTREAM_CALL` | 9 | 9 |
| `P1_WORKER_EVENT_CALLBACK_CALL` | 9 | 9 |
| `P1_XAM_INPUT_ENTRY` | 12 | 12 |

Timing (Native / Xenos):

- Menu Setup state 1 entered at 66.443 s / 66.836 s (`P1_MENU_SETUP_INIT_ENTRY`,
  caller LR `0x82fbc974`); state observed at 66.525 s / 66.883 s.
- Setup scene pointer written `0 -> attached scene` at 76.297 s / 75.639 s
  (`setup+8`, e.g. `0xbf0fda58`), writer `sub_82FD53B8`, backtrace
  `sub_82FD53B8 -> sub_82DD8D38 -> sub_82E336B8 -> sub_82E32640 ->
  sub_82FD5658 -> sub_82FC1880 -> sub_82D30380 -> xstart`.
- Scene-gate watch armed at 76.298 s / 75.640 s on `scene+8`, value 0,
  scene vtable `0x8211e280` (`P1_SCENE_GATE_WATCH_ARMED`).
- The one and only gate write: `P1_SCENE_GATE_FIELD_WRITE` at 76.303 s /
  75.644 s, field `scene+8` (`0xbf054ad8` / `0xbeebc078`), **before 0 after
  1**, writer `sub_82DD9020 + 107` on `Core 0/0: Main`.
- Gate method entry `sub_82DD9020` at 76.300 s / 75.641 s, caller LR
  `0x82fd5468`, `receiver == attached_scene`, `receiver_vtable 0x8211e280`,
  `setup_state 1`; returns at 76.304 s / 75.644 s with `field_after 1`,
  `return_r3 0x831c3198`.
- `sub_82DD8FF8` (`scene+0x14`, "clear scene+8 to zero"): **zero entries** in
  both runs. `MAINMENU_SCENE_GATE_METHOD_BREAKPOINTS_ARMED` at 0.855 s /
  0.876 s lists both `0x82dd8ff8` and `0x82dd9020`.
- State 2 first update at 77.460 s / 76.766 s (`P1_STATE2_FIRST_ENTRY`), 20th
  at 110.168 s / 110.052 s. `caller_lr 0x82fc1a08`, object `0xbf0fda50` /
  `0xbf082270`, `embedded_child_object 0xbf0fda6c` / `0xbf08228c` with vtable
  `0x82117fb4`, `child_ready 0`, `child_state 0`, `child_fallback 1`.
  Native `scene_words` are `[0x8211e280, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]`
  at both the first and the last update — i.e. `scene+8 = 1` throughout.
  Xenos `scene_words` are `[0x8211e280, 0, 1, 0xbf000004, 0x200, 0, 0x40,
  0x3c6c4a6f, 0, 0, 0, 0]` at every sampled update.
- GUI event queue: `P1_MAIN_MENU_EVENT_QUEUE_INTERFACE` at 77.655 s / 76.902 s,
  `gui_object 0xbf054ad0` / `0xbeebc070`, `queue_receiver 0xbf054b50` /
  `0xbeebc0f0`, `queue_vtable 0x82128f1c`; the queue object word at `+0x8` is 0
  (`queue_words = [0x82128f1c, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`). The queue
  object addresses quoted in the lane brief (`0x8310ab80` with vtable
  `0x8212b2e8`) are the first `P1_GUI_QUEUE_CTOR_CALL` receiver
  (`caller_lr 0x822d619c` at 4.438 s / 4.367 s, vtable null before
  construction, flags `0x0`) and the sampled `sub_822E1910` service-queue
  receiver `0xbcad2c60` (vtable `0x8212b2e8`), which returns `r3 = 0` on all
  49 sampled calls; the *menu GUI* queue is the separate vtable `0x82128f1c`
  object below.
  `getter_target 0x822bdf20` (queue getter), `queue_flags 3221225472 =
  0xC0000000` (Native) / 3489660927 = 0xD0000BFF (Xenos — the Xenos flags
  word differs and needs its own static bound).
- `P1_MAIN_MENU_EVENT_QUEUE_SUMMARY`: `constructor_calls 70`,
  `enqueue_calls 0`, `enqueue_returns 0`, `direct_append_calls 0`,
  `direct_append_returns 0`, `open_calls 9`, `process_event_queue_calls 16`,
  `getter_calls 16`, `queue_words[0] = 0x82128f1c` (the queue object's first
  word holds `0x82128f1c`, not the vtable word `0x82128f1c` — both are the
  same value in these samples; the vtable is reported separately as
  `queue_vtable 0x82128f1c`). No `P1_*ENQUEUE*` event family exists in the
  v118 schema at all, so "zero enqueues" means "the enqueue breakpoint was
  never hit", and no positive control has yet proved that enqueue breakpoint
  would fire.
- `P1_FRONTEND_DISPATCH_SUMMARY` (function `sub_822FDCE0`): `calls 0`,
  `returns 0`, `samples_by_button {A: 0, Start: 0}` in both runs.
- `P1_QUEUE_POP_BRANCH_SUMMARY` (caller filter LR `0x822fdf88`): `calls 0`,
  `returns 0`; recorded static branch text: after a successful pop,
  `output[2]` at guest `r1+0x68` must be nonzero and `queue+0x10` must be
  zero, and the original code then executes `li r3,5`.
- The 9 observed `sub_822FDCE0` queue-pop/dequeue records are **not** Start/A
  correlated: they belong to the worker completion path. `P1_DEQUEUE_RETURN_CONTEXT`
  at 79.665 s / 78.949 s shows saved context `r3 = 1` at return,
  `guest_r1_plus_0x68 = 0xBB000004 (2800109188)` and `guest_r28_plus_0x10 = 0`;
  the downstream call at `guest_pc 0x822fdfb8` already carries `r3 = 5` and
  `sub_8223CE40(5)` returns 5. Dequeued event object `0xa6e64684`, event type
  2, `event_flags_plus_0xcc = 16384 (0x4000)`, `event_field_plus_0x44 = 0`,
  `event_flag_ppc_bit_1_present false`, `event_flag_ppc_bit_4_present false`;
  nested dispatch into `sub_822E8678` (9 calls, caller LR `0x822fe1a8`),
  helpers `sub_822E81F8` (9) and `sub_822E8510` (8), callback returns
  `r3 = 0`. The 9 dequeue times are 79.671, 80.144, 86.967, 87.532, 88.111,
  89.049, 90.053, 91.065, 107.001 s (Native) and 78.956, 79.442, 86.533,
  87.029, 87.671, 88.692, 89.695, 90.740, 106.849 s (Xenos).
- `P1_WORKER_GATE_SUMMARY`: active hits `sub_822E1910` 901/918,
  `sub_822E80A8` 894/912, `sub_822E7F70` 339/346; sampled (throttled) calls
  24+16+9 = 49 with 49 returns, **all returning `r3 = 0`**. Sampled queue
  `0xbcad2c60` has vtable `0x8212b2e8`, flags `0xe0000000`, `opened true`,
  head and tail empty after the call. 16 of the 49 sampled callers are
  `sub_822bdf5c` with first argument equal to the menu GUI queue receiver
  (`0xbf054b50` / `0xbeebc0f0`) — i.e. the menu GUI queue is *opened* and
  *polled*, and the poll is empty.
- Input: `P1_HOST_INPUT_SAMPLE` 19, `P1_HOST_INPUT_CALL` 8,
  `P1_XAM_INPUT_ENTRY` 12 (`user 0x0` and `0x3`), `P1_RETAIL_CONTROLLER_FOUND`
  1, `P1_RETAIL_CONTROLLER_EDGE_STATE` 18; `predicate = 1` in all 36
  `P1_RETAIL_INPUT_PREDICATE` records (Start 24, A 12; caller LR `0x8230a9d0`
  12, `0x822fbf3c` 24). `P1_RETAIL_INPUT_TRUE_HANDLER` 6 and
  `P1_ACTION_EVENT_FIELD_WRITE` 37 writes to `Start+0x20` (`0xbf509cd0` /
  `0xbf509bb0`, 21 writes, event code `0x30010400`, guest LR `0x8230a9f0` and
  `0x8230ab24`) and `A+0x20` (`0xbf50a750` / `0xbf50a630`, 16 writes, event
  code `0x30010c00`). All writes are original-guest writes; the probe wrote
  nothing (`guest_memory_modified_by_probe false` everywhere).
- `P1_ACTION_CONSUMER_SUMMARY`: `sub_822EF7B0` 20 calls, `sub_822F7EC8` 16
  calls, both with matching returns; `P1_ACTION_CONSUMER_RETURN` `return_r3`
  values `{0x0: 8, 0x1: 8, 0xb: 4, and stack pointers 0x705afd20/0x7060fd20:
  8 each}` — identical multiset on both backends.
- `P1_CONTEXT_R3_WATCH_SUMMARY`: `armed false`, `watchpoints 0`, policy
  "disabled after return-register snapshot; no hardware watchpoint". The v107
  one-shot `r3 1 -> 5` watch is therefore **not** part of the v118 capture;
  the v118 run only sees the downstream call arguments.
- `P1_STOP_CONTEXT` at 110.203 s: guest registers show `context
  0x5555666ceb90`, `lr 0x0`, `memory_base -0x1`, host stopped in
  `VulkanPresenter::PaintAndPresentImpl` (NVIDIA driver frames).
- Renderer log (`bin/logs/nfs_shift_001.log`, 16402 lines): at 21:24:18.605
  `Vulkan frame refresh failed for 1280x720 with 1 captured draws (failure
  1): captured operation stream contains unresolved draw packet 0 ... (packet
  23), then `draw(packet=24, valid_mask=0x1ffff, surface=0xa020280, ...)`
  and `copy(packet=49, ...)`. At 21:25:29.781 the loader fails
  `d:\tracks\_data\instances\scenes\menu_background.xml` and
  `d:\tracks\_data\static\scenes\menu_background.xml`
  (`0xc000000f`), earlier `d:\devmodeconfig.xml` (21:24:18.067),
  `render\shaders\cache\` (21:24:18.788), `d:\pakfiles\dir\audio.bff`
  (21:24:23.021), `d:\tracks\cameraconfig.xml` (21:24:23.988). At 21:25:30.760
  `unresolved captured draw #6 ... unsupported captured shader control-flow
  opcode 7 at instruction 1`.

Interpretation of the above: the retention of state 2 is *not* input-starved —
the guest sees the pad, the retail handler raises the predicate, the action
consumers run, and the gate write that would release state 2 never happens.
Whether the missing producer is the menu GUI queue (never enqueued, polled
empty 16 times), an uninvoked callback, a rejected status, an asset early-out,
a scheduling artifact, or a false internal predicate is exactly what H1–H6
below decide.

## 3. Hypotheses

Each hypothesis carries (a) a falsifiable prediction, (b) the cheapest static
check that can kill it, (c) the GDB probe that would confirm it. All probes
are read-only; none writes guest memory.

| ID | Hypothesis | Falsifiable prediction if true | Falsified when |
|---|---|---|---|
| **H1** | The clear is driven by a UI/frontend dispatch callable that never fires because the menu GUI event queue (`getter_target 0x822bdf20`, queue receiver `scene+0x80`, vtable `0x82128f1c`) has zero enqueues; `sub_822FDCE0` polls it empty 16 times and returns. | The queue's enqueue method is never entered; the 16 `process_event_queue` polls report head==tail; the first enqueue would correlate in time with a gate clear. | An enqueue is observed with the gate still `1`; or the static dispatch path shows the clear does not depend on the queue. |
| **H2** | The enqueue source is a registered guest object callback dispatched from the retail software queue (vtable `0x82032df0`, object `0xbb9cc130`, slot `+0x24c` target `0x82648438`) which is never invoked in the capture window, so nothing reaches the enqueue. The lane brief also named `0x82649B68` and `0x82321198` (object `0xB7365F00`) as candidate registered callbacks; **unknown**: none of `0x82649B68`, `0x82321198` or `0xB7365F00` appears in the v118 native or Xenos `gdb.log`, and no committed doc on this branch names them, so they are carried as static-check candidates only (§6-S1/S2), not as captured facts. | Callback entry counters are zero for the candidate producers upstream of the enqueue; a repeat with a longer window shows the callback either never enters or enters without enqueuing. | The candidate callback is entered and either enqueues (H1 false) or clears the gate directly. |
| **H3** | The action path returns a status the caller rejects: the saved-context `r3` becomes `5` at the `sub_822FDCE0` post-pop branch and the status `5` is passed on. | Status `5` maps to "queue empty / no work" in the retail disassembly and the branch that consumes it skips the frontend dispatch. | Static bound of status `5` shows a different meaning (e.g. success), or the rejected branch is not on the path that could clear the gate. |
| **H4** | A missing asset causes an early-out that skips the enqueue/clear: `menu_background.xml` (instances + static), `audio.bff`, `devmodeconfig.xml`, `cameraconfig.xml`, `render\shaders\cache\`. | The failing loader returns a distinct failure that propagates to the `MainMenu` setup, and a run with the asset resolvable (correct path/mapping) changes the scene path. | The loader callers ignore the failure and continue into the GUI queue path unchanged — then H4 cannot explain the missing enqueue. |
| **H5** | Scheduling/timing: the host has 4 CPUs for 6 guest CPUs, so the producer thread is starved; the capture window (settle 10 updates after the last pulse, ~24 s of state 2 observed) is too short or the producer runs on a thread the trace does not see. | The producer's owning thread never schedules in the window; counts scale with window length and CPU contention. | Paired runs with a longer window and increased host CPU availability show identical zero counts; or the producer thread is seen running (e.g. in a `nanosleep`) without reaching the enqueue. |
| **H6** | The callback does run but its predicate is false: `scene+8` already blocks its own re-entry by design (a self-guard), or another state bit (`child_ready 0`, `child_state 0`, `embedded_child_object` words) is false, so the clear is never attempted. The lane brief additionally names a scene-manager `object+0x2ABD` bit and a queue-completion bit; **unknown**: `0x2ABD` appears in no v118 event (no scene-manager event family records that offset), so that specific bit is a static-check candidate only (§6-S6), not a captured fact. | The producer callback is entered and takes a "nothing to do" branch that reads `scene+8` (or child state) before any enqueue/clear attempt. | The producer callback is never entered at all (then H1/H2/H3/H5 own the explanation). |

### Ordering and expected discriminators

v118 already constrains H5 weakly: state 2 was observed for ~24 s past the
last input with `post_pulse_settle_updates 10/10`, and the guest main thread
was observed running the gate poll at 110.168 s, well after the last pulse at
81.617 s. So "the run was too short" is not the explanation by itself. H5 is
retained only for the case where the producer lives on a different guest
thread that the trace does not schedule (the trace already shows `Core 0/0:
Main`, `Core 2/1: Contr` and `Core 0/1: Base` threads, so multi-thread
dispatch is visible).

H6 now has one new, concrete datum: `P1_STATE2_FIRST_ENTRY` records
`child_ready 0`, `child_state 0`, `child_fallback 1`, and the state-2
`scene_words` show `scene+8 = 1` with `child_state = 0`. If the child's
`ready` transition is the event that would clear the gate, the question
becomes "who sets child+0x0c ready", which is a static check, not a capture.

## 4. Capture design for the next version (v119)

Everything below is read-only. The invariant `guest_memory_modified_by_probe
= false` must hold in `run_metadata.json` for every run, and every event
family must carry the same field. Any probe that would need to write the
guest (e.g. to force an enqueue) is out of scope.

### 4.1 Runner and trace to base on

Base the v119 runner and trace on the committed pair (the v118 pair itself is
not in the repository; `run_metadata.json` records only its paths and hashes —
`tools/xbox360/capture_linux_menu_setup_callback_route_v118_20261029.py`
sha256 `f09c0f65...ae24d`, `tools/xbox360/trace_linux_menu_setup_callback_route_v118_20261029.gdb`
sha256 `41e7b623...753` — and neither file is present at commit
`488601bb1`):

- `tools/xbox360/capture_linux_menu_setup_frontend_worker_gate_v112.py`
- `tools/xbox360/trace_linux_menu_setup_frontend_worker_gate_v112.gdb`
- comparator/test pair
  `tools/xbox360/compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py`
  and `tools/xbox360/test_compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029.py`
- event families to add on top of v112, taken from the actual v118 `gdb.log`
  schema: `P1_MAINMENU_SCENE_GATE_METHOD_BREAKPOINTS_ARMED`,
  `P1_SCENE_GATE_WATCH_ARMED`, `P1_MAINMENU_SCENE_GATE_METHOD_CALL/RETURN`,
  `P1_SCENE_GATE_FIELD_WRITE`, `P1_STATE2_UPDATE/RETURN`,
  `P1_STATE2_DYNAMIC_CALL/RETURN`, `P1_STATE2_CALL/RETURN`,
  `P1_RETAIL_INPUT_PREDICATE`, `P1_ACTION_CONSUMER_CALL/RETURN`,
  `P1_ACTION_EVENT_FIELD_WRITE`, `P1_WORKER_GATE_CALL/RETURN`,
  `P1_WORKER_EVENT_CALLBACK_HELPER_CALL/RETURN`,
  `P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS/RETURN`, `P1_GUI_QUEUE_CTOR_CALL/RETURN`,
  `P1_HOST_INPUT_SAMPLE`, `P1_RETAIL_CONTROLLER_EDGE_STATE`,
  `P1_STARTUP_MEMORY_FILL_ENTRY`.

The v119 trace must add exactly three new capability groups (each as its own
event family, so a run can be analysed without them):

1. **Positive control on the queue** — breakpoint the queue's enqueue method
   (to be identified statically, see §6-S1) and record call/return plus the
   enqueued event words. Rationale: the v118 schema has no enqueue event at
   all, so "0 enqueues" is currently a *negative observation without a
   positive control*. Also arm a *watch* (read-only) on a queue slot that the
   enqueue path writes, so a same-run write from an un-breakpointed caller is
   still seen.
2. **Producer-candidate entry counters** — breakpoints at the candidate
   producers' entries (H2 list), recording call count only, not arguments, to
   keep overhead low: `0x82648438` (service reject gate, slot `+0x24c` of
   `0x82032df0`), plus every caller of the enqueue method found in §6-S1.
3. **Status-5 bound** — record `r3` and the post-call branch taken at
   `sub_822FDCE0 + 3320`/`+3324` (downstream call/return host offsets already
   used by v118) together with the guest PC of the next branch. This turns the
   `r3 = 5` observation into a branch-identity observation.

Keep the v118 event families unchanged so v118 and v119 can be compared with
the existing comparator pattern.

### 4.2 Breakpoint list (guest addresses)

| Guest address | Role | Event family |
|---|---|---|
| `0x82dd9020` | scene gate set (`scene+0x0c`) | `P1_MAINMENU_SCENE_GATE_METHOD_CALL/RETURN` |
| `0x82dd8ff8` | scene gate clear (`scene+0x14`) — **the target** | `P1_MAINMENU_SCENE_GATE_METHOD_CALL/RETURN` |
| `scene+8` (e.g. `0xbf054ad8`) | gate word, write watch only | `P1_SCENE_GATE_FIELD_WRITE` |
| `0x82fd5468` (caller LR of set) / `0x82fd53b8` | setup scene-pointer writer | `P1_SETUP_SCENE_POINTER_WRITE` |
| `0x82fd5658` | state machine step | `P1_STATE2_UPDATE` |
| `0x821f4110` | gate getter (`scene+0x08`) | `P1_STATE2_DYNAMIC_CALL` (slot `0x8`) |
| `0x82ddb330` | `scene+0x1c` dispatch | `P1_STATE2_DYNAMIC_CALL` (slot `0x1c`) |
| `0x82fd4418` | transition helper `(setup+4, 3)` — entry and return | new `P1_TRANSITION_HELPER_CALL/RETURN` |
| `0x822bdf20` | menu GUI queue getter | `P1_MAIN_MENU_EVENT_QUEUE_CALL` |
| `0x82128f1c` | menu GUI queue vtable (slots to be resolved statically) | `P1_MAIN_MENU_EVENT_QUEUE_*` |
| queue enqueue method (TBD by §6-S1) | the enqueue itself | new `P1_MAIN_MENU_EVENT_QUEUE_ENQUEUE` |
| `0x822e1910`, `0x822e80a8`, `0x822e7f70` | retail software queue service gates | `P1_WORKER_GATE_CALL/RETURN` |
| `0x822e8678` | type-2 worker event callback | `P1_WORKER_EVENT_CALLBACK_CALL` |
| `0x822e81f8`, `0x822e8510` | worker callbacks' helpers | `P1_WORKER_EVENT_CALLBACK_HELPER_*` |
| `0x82648438` | service reject gate (slot `+0x24c`, vtable `0x82032df0`) | `P1_PRODUCER_CANDIDATE_CALL` |
| `0x82649b68`, `0x82321198` | candidate registered callbacks (object `0xb7365f00`), **pending static confirmation** — not observed in v118 | `P1_PRODUCER_CANDIDATE_CALL` |
| `0x822fdce0` | frontend dispatch / queue pop | `P1_FRONTEND_DISPATCH_*` |
| `0x8223ce40` | status consumer (`r3 = 5`) | recorded via downstream call/return |
| `0x8230a8e0`, `0x8230a9f0`, `0x8230ab24` | retail controller handler and event-field writers | `P1_ACTION_EVENT_FIELD_WRITE` |
| `0x822ef7b0`, `0x822f7ec8` | action consumers | `P1_ACTION_CONSUMER_CALL/RETURN` |
| `0x82f7c560`, `0x82f7c938` | resource loader child/parent (H4) | new `P1_RESOURCE_LOAD_RETURN` |
| `0x82fc1a08` (state-2 update caller), `0x82fc1880`, `0x82d30380` | startup/update chain | kept as caller LR fields |

Hardware watchpoint budget: the v112/v107 experience (and
`XBOX360_PROCESS1_COMPARATIVE_FRONTIER_20261028.md`) shows x86 gives roughly
four hardware watchpoints; v118 spent one on `scene+8`. v119 keeps that one
and adds at most one queue-slot watch, at most one loader-result watch, and
uses breakpoints (not watchpoints) for everything else. If a fifth watch is
needed, retire the worker+72 watch as the 2026-10-28 report already did.

### 4.3 Run length and pairing

- Paired Xenos + Native, same XEX/host/runtime/game-data, same input schedule
  as v118 (`state2_update_index`, three pulses Start/A/Start, hold 2, gap 1).
- Minimum run: state-2 observed for at least 60 guest updates or 30 s of
  wall time after the last pulse, whichever is later — v118 only reached 20
  updates in ~33 s of state 2 (~0.86 updates/s at that point, widening to
  ~1.5 s cadence). Confirmation requires the producer to have had a fair
  chance: 60 updates ≈ 60 s of state 2.
- Both backends must produce the same counts for every event family for the
  run to be admissible; a backend-only difference is recorded but does not
  close a hypothesis (v112 already showed that backend dequeue frequency is
  not reproducible and is not the cause).
- `run_metadata.json` must record, in addition to the existing keys (see
  §2 for the full v118 key list and `schema
  shift.xbox360.linux-menu-setup-state2-update-input-run.v1`): `guest_memory_modified_by_probe`,
  `gdb_exit`, `events_log_sha256`, `runner_sha256`, `trace_sha256`,
  `post_pulse_settle_updates_requested/observed/stop_reason`, the
  `input_timing` block, the `hashes` block, `host_cpu_count` (H5), and a new
  `static_preconditions` object naming the commit(s) of the static narrowing
  that produced each breakpoint (so a capture is never run on an unverified
  address map).

Necessary condition to call v119 admissible: `gdb_exit == 0`,
`guest_memory_modified_by_probe == false` in metadata and in every event,
`P1_MAINMENU_SCENE_GATE_METHOD_BREAKPOINTS_ARMED` confirms both
`0x82dd8ff8` and `0x82dd9020` are armed, and the gate field write count is 1
(if it becomes 2, the gate was cleared by someone).

## 5. Acceptance criteria and red lines

### 5.1 Per-hypothesis acceptance

| ID | Confirmed by | Falsified by |
|---|---|---|
| H1 | A v119 run where the enqueue method is armed (positive control proven by at least one enqueue somewhere) and the menu queue's enqueue count is 0 while the gate is 1; plus a static path showing `sub_822FDCE0`'s dispatch depends on that queue. | Enqueue observed while gate stays 1; or static path shows the clear does not depend on the queue. |
| H2 | Producer callback entry count 0 in a run of sufficient length, with the static caller chain from that callback to the enqueue established. | Callback entered; or static chain shows another enqueue source. |
| H3 | Static bound of status `5` (retail bytes + generated C++) and a trace row showing the branch taken after the `sub_8223CE40(5)` return skips the dispatch. | Static bound shows `5` is success / the branch is unrelated. |
| H4 | Loader failure return observed reaching `MainMenu` setup, plus a run where the asset resolves and the GUI path changes. | Loader failure ignored by all relevant callers. |
| H5 | Producer thread never scheduled across a longer, lower-contention run; counts stay 0 while the trace proves the thread is live. | Longer run with equal counts; or the producer thread observed running without reaching the enqueue. |
| H6 | Producer callback entered and observed taking a branch reading `scene+8`/child state before any enqueue attempt. | Producer callback never entered. |

### 5.2 Red lines — do not guess

- Never patch, poke, or initialize guest memory, including `scene+8`,
  `child+0x0c`, queue fields, or the saved PPC context.
- Never force the predicate: no breakpoint command may `set` a register or
  write a variable to make the gate clear. The `r3 = 5` and `r3 = 1 -> 5`
  observations are inputs to static analysis, not things to override.
- Never fabricate a callback, hook, or shim to make the frontend dispatch
  fire; no "stub the enqueue" experiment.
- Never claim an address is an enqueue method, a callback producer, or a
  status meaning without a file:line (generated C++ or disassembly) or a
  trace row to back it.
- Never generalise a Native-only or Xenos-only observation to a cause; the
  v108/v109/v112 data already showed backend reversal.
- Never cite the v118 runner/trace hashes as if the files were in the
  repository. They are recorded in `run_metadata.json` and the files are
  absent at `488601bb1`; a committed runner must be re-hashed when it lands.
- Where evidence is missing, write "unknown" plus what would prove it, rather
  than filling the gap with a plausible story.

## 6. Static narrowing first (cheap before expensive)

Build the whole address map below from the retail XEX bytes (Ghidra import or
`objdump`/capstone on the PE code section, matched against the generated
recompiled C++ under `xbox360/rexglue/`) **before** running any new capture.
Each step is a yes/no that can retire a hypothesis without a 2-minute run.

- **S1 — the menu GUI queue enqueue method (H1).** Resolve
  `queue vtable 0x82128f1c` and `0x8212b2e8` slot layouts; find the method
  that pushes into the queue and, crucially, find *every* caller: if no
  caller exists in the guest image, H1 becomes "queue is never fed by
  design" and the gate clear must come from elsewhere. Deliverable: method
  address, vtable slot, xref list.
- **S2 — `sub_82DD8FF8` callers (H2/H6).** Enumerate all call sites of the
  clear method and of `sub_82FD4418`. Each call site gets a caller-chain up
  to a retail entry. This is the direct answer to "who is supposed to clear
  it".
- **S3 — `sub_82FD4418` (transition helper).** Bound its arguments
  (`setup+4`, `3`), the branch conditions that gate it in `sub_82FD5658`,
  and whether `3` is a state id or an action id. Deliverable: byte-level
  pseudo-code of the state-2 branch with the two conditions that must hold.
- **S4 — status `5` bound (H3).** Disassemble `sub_822FDCE0` around
  `+3271` (the v107 `movq $0x5,(%r14)` write site) and the `sub_8223CE40`
  call; identify the return paths that produce `5` and whether the caller
  treats `5` as "empty" or "not-ready". Cross-check with the v112 doc's
  preserved `r3` values.
- **S5 — resource-loader early-out (H4).** Disassemble `sub_82F7C560`
  (child loader) and `sub_82F7C938` (parent, success value at `0x82F7CB50`,
  result stored at `0x82F7CB4C` per
  [`xbox360_linux_menu_background_missing_flow_20261025.json`](../evidence/xbox360_linux_menu_background_missing_flow_20261025.json));
  determine whether the parent returns success when the child fails and
  whether the `MainMenu` setup path inspects that result at all.
- **S6 — child readiness (H6).** Find who writes the embedded child's
  `+0x0c` (`child_ready`) and its `+0x08` (`child_state`); if the ready
  transition is missing because an upstream scene never finishes loading,
  that is the same root as H4 with a different reporting surface.

If S1–S4 together name the producer of `scene+8 = 0` and the first false
predicate on the path, no new capture is needed to state the blocker — only
to confirm it. Only then run v119 (§4). If S1–S4 are inconclusive, run v119
with the §4 breakpoint list, not a broader guess.

## 7. What X4 becomes provable, and the fallback

- **If H1/H2 are confirmed**: X4 is provable as "state 2 retention is caused
  by an unfed GUI event queue; the feeder callback is identified and its own
  blocker is the next frontier." The scene gate clear becomes a downstream
  symptom; the plan then moves to the feeder's predicate.
- **If H3 is confirmed**: X4 is provable as "the frontend swallows the action
  because the queue-pop status is interpreted as empty"; the fix is a status
  contract question in the guest logic, still fail-closed (bound the status,
  do not force it).
- **If H6 is confirmed**: X4 is provable as "the scene manager's child never
  becomes ready"; the gate clear is correct behaviour and the frontier moves
  upstream to the missing scene load, which is likely the same root as H4.
- **If H4 is confirmed**: X4 is provable as an asset-resolution blocker, and
  the fallback work becomes the retail `index.directory` mapping. Open
  question, not answered in this plan: the guest asks for
  `d:\pakfiles\dir\audio.bff` and `d:\tracks\_data\{static,instances}\scenes\menu_background.xml`,
  while the extracted tree on a case-sensitive filesystem contains
  `PakFiles/Dir/audio.bff` and `PakFiles/...` with capitalisation
  ([`xbox360_linux_asset_open_triage_20261025.json`](../evidence/xbox360_linux_asset_open_triage_20261025.json)
  lists `PakFiles/Dir/audio.bff`); there is currently no committed evidence
  of the exact case-insensitive fold the retail `NtCreateFile` path applies
  (a search for `index.directory` in `docs/` and `evidence/` returns nothing).
  What would prove it: a static read of the guest path-normalisation routine
  and the retail `index.directory`/BFF table, plus a run whose `NtCreateFile`
  logs show which folded path is actually opened. Do not rename the extracted
  tree from a guess.
- **If H5 is confirmed**: X4 is provable as a harness scheduling limitation,
  and the lane's output is a scheduling/capture-window fix, not a guest-logic
  finding.

Neither result may be described as "menu works". X4 stays open until the gate
actually clears in a clean paired run with `guest_memory_modified_by_probe =
false`, and even then the renderer frontier (P2) remains the separate blocker
for a visible menu.

## References

- [`XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md`](XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md)
- [`XBOX360_MENU_EVENT_DEQUEUE_LIVE_CONTEXT_PAIR_V107_20261029.md`](XBOX360_MENU_EVENT_DEQUEUE_LIVE_CONTEXT_PAIR_V107_20261029.md)
- [`XBOX360_PROCESS1_COMPARATIVE_FRONTIER_20261028.md`](XBOX360_PROCESS1_COMPARATIVE_FRONTIER_20261028.md)
- [`xbox360_linux_menu_setup_event_dequeue_downstream_repeat_v112_20261029.json`](../evidence/xbox360_linux_menu_setup_event_dequeue_downstream_repeat_v112_20261029.json)
- [`xbox360_linux_menu_background_missing_flow_20261025.json`](../evidence/xbox360_linux_menu_background_missing_flow_20261025.json)
- [`xbox360_linux_asset_open_triage_20261025.json`](../evidence/xbox360_linux_asset_open_triage_20261025.json)
- v118 runs (outside Git): `/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-native-retry-20261029/`,
  `/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-xenos-20261029/`
