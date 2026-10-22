# Automated retail startup frontier (Linux)

For verified Ghidra-epilogue auditing, opt-in preflight checks and the captured
D3D9-only implementation scope, see [Linux acceleration](LINUX_RETAIL_ACCELERATION.md).

This tooling shortens the **build → bounded original-PE probe → classification → regression** cycle. It does not assert gameplay, frontend readiness or D3D9/Vulkan semantic parity.

## Scope and safety

- **CI/PR (no game assets):** parse committed v173 evidence, compare synthetic D3D9 contracts, run Python regressions, and reuse compiler object caches.
- **Local retail host:** build the native runtime incrementally, invoke the existing entrypoint probe with external pinned full P-code ELF, compare against a saved frontier.
- Full ELF, original PE, original resources, raw captures and generated render assets are **not** uploaded to GitHub. Store outputs under artifacts/ or another ignored external directory.
- Dispatch-count increases are diagnostic progress, **not** proof that game behavior is correct.

## 1 — Cached native build

~~~bash
bash tools/build_shift_runtime_cached.sh --build-dir native_runtime/build --jobs 8
ctest --test-dir native_runtime/build --output-on-failure -R '^shift_runtime_recompiled_pcode_module$'
~~~

The helper reuses its CMake build directory, chooses Ninja on a fresh build if available, and enables ccache/sccache if installed (SHIFT_COMPILER_CACHE=off disables caching). It only builds the native runtime and fixture checker. It never re-lowers the 41,538-function frozen corpus or commits the multi-gigabyte ELF.

## 2 — Run and classify the original entrypoint

Set appropriate external paths on the retail host:

~~~bash
python3 tools/retail_frontier.py run \
  --runtime native_runtime/build/shift_runtime \
  --artifacts /path/to/shift-startup-artifacts \
  --build-dir native_runtime/build \
  --pe /path/to/SHIFT.exe \
  --game-data '/path/to/Need For Speed.Shift.v 1.02' \
  --module-manifest evidence/retail_frontier_20261019/entrypoint_probe_v215_supplement_replay.json \
  --build-runtime --validation --frames 120 --timeout 180 --kill-after 5 \
  --baseline evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log \
  --log artifacts/frontier/current.log \
  --output artifacts/frontier/current.json
~~~

The optional `--module-manifest` reads `execution_evidence.additional_overrides` and `additional_supplements` from a prior report. It resolves each relative path beneath `--artifacts`, verifies every recorded SHA-256, and adds the modules to the launcher's existing module set. The probe report records the manifest hash and the verified module paths/hashes. Without a manifest, the launcher still accepts newline-delimited paths through `SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS` and `SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES`; these environment variables can also add modules alongside a manifest. The full P-code module can be selected with `SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE`. Paths and versions must match the chosen retail corpus. The launcher validates pinned original PE SHA-256 before execution.

When `tools/retail_frontier.py run` is used without `SHIFT_ENTRYPOINT_PROBE_MESH`,
it writes a minimal synthetic triangle MGEO into a temporary directory to
initialize the host renderer. This fixture is not retail evidence and is
removed after the probe. Direct calls to the shell launcher require a valid
MGEO path in `SHIFT_ENTRYPOINT_PROBE_MESH`.

The report stores status, guest dispatch counts, unique functions, first failing import, return address, host frame-loop information (when present), and a baseline delta. Analyze an existing log **without running game assets**:

`--timeout` is a hard launcher wall-clock limit. At expiry, the launcher sends
SIGTERM and waits `--kill-after` seconds (default 5) before sending SIGKILL,
then appends a machine-readable timeout marker to the log. The report retains
both limits and classifies forced termination as `timeout`. Selected
`SHIFT_TRACE_*` filters are recorded in `probe_configuration.trace_environment`
so a trace report can be reproduced without recording unrelated environment
variables.

When the native frame-loop report includes `d3d9_vulkan_bridge`, the parser
retains guest Clear/Present request and Vulkan submission counts. v194 records
122 guest Clear requests and 121 Present requests across a 120-frame probe;
120 clear submissions and 120 Vulkan swapchain presents completed, with one
Present request still pending and no guest draw translation. This proves the
bounded clear/queue-present path only; it does not prove retail rendering or
frontend readiness.

The cumulative v215 replay reproduces that same host-frame-loop checkpoint
from the v210 frontier using two additional overrides and a cumulative set of
19 supplements. Its five saved reports show the missing-export chain from
`0x0090a007` through the D3D9 methods before it reaches 120 host frames.
See
[`entrypoint_probe_v215_supplement_replay.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v215_supplement_replay.json)
for the exact module paths, hashes, lowerer revisions, and per-run results.
`SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS` and
`SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES` are the complete extra module lists
for a run; when extending a frontier, include earlier required modules again.
Omitting a prior supplement can produce a false earlier missing-export stop.
The v215 replay still reports no guest draw translation, frontend, or race.

The follow-up after PR #2123 adds binary80 `LOG2`, `F2XM1`, and `FSCALE`
userops and uses the shared RevEngInstr exporter to recover a missing x86 call
fallthrough plus bounded entrypoint trampolines. Probes v463–v466 advanced the
guest frontier through 4,621 unique functions; they still stop before frontend
or retail rendering. Compact hashes and blockers are recorded in
[`x87_call_fallthrough_followup_v462_v466.json`](../evidence/retail_frontier_20261020/x87_call_fallthrough_followup_v462_v466.json).
The continued chain through v474 reached 4,656 unique guest functions; a
fresh `0x00427770` override cleared the generic failure, and the current
missing export is `0x0082db10`. See the
[`v467–v474 follow-up`](../evidence/retail_frontier_20261020/x87_call_fallthrough_followup_v467_v474.json)
for per-run and module hashes.

PR #2123's corpus and focused-CTest preflights were used before the v506–v520
retail probes. The frozen corpus contains 41,552 functions and 2,089,743
instructions; the active requirements contain 358 function-boundary records
(414 audit checks across repeated corpus rows) and pin the complete instruction
bodies of `0x0057ddf0`, `0x005ab6c0`, `0x00655040`, `0x006550f0`, and
`0x006496f0` in addition to earlier
frontier boundaries.

The v512 diagnostic logged call attempts from `0x0064879e` to `0x005a8870` and
from `0x005a8870` to `0x0057ddf0`. Those entry records do not by themselves
prove that the target bodies resolved or executed. The v513 caller-scoped trace
then proved `0x0057ddf0` executed several returning calls and reached its
`0x005ab740` callsite. In v516, a caller-scoped trace proved `0x005ab6c0`
executed: `0x00649cb0` returned `0x008f3d01`, `0x00655040` returned `1`, and
`0x006550f0` repeatedly returned `0` at return address `0x005ab6f7`. The loop
therefore remained active and `0x00655110` was not reached before timeout.
The v517 sample found `[ECX+4]=0x27f39bf0`; `0x006550f0` then reads bit 2
from the indirect field at `[0x27f39bf0+0x74]` (candidate address
`0x27f39c64`). v518 sampled the word as `0x00000002`, leaving bit 2 clear.
The v519 live provenance trace identified `0x006496f0` as the writer of that
value. `0x00655040` tail-dispatches to it; the body clears bit 3, then calls
the indirect pointer at `0x00aa62b8`. v520 resolves that callback to
`KERNEL32.dll!ResumeThread`, which returns `1`; the subsequent worker action
that should set predicate bit 2 is still unknown. No frontend, race, retail
D3D9 draw, or retail rendering is proven. See the
[`post-PR #2123 follow-up evidence`](../evidence/retail_frontier_20261020/post_pr2123_retail_frontier_followup.json)
for report, log, corpus, requirements, and module hashes.

Process 1 replayed the v520 call chain on the current runtime before changing
scheduler behavior. The pinned PE repeatedly called `0x006550f0` from
`0x005ab6c0`; the call returned `EAX=0` while `[0x27f39bf0+0x74]` stayed
`0x00000002`, and the diagnostic was stopped manually after dispatch
6,983,183 to avoid continuing the same poll. The latest available external
frontier artifacts were v523 and v524 (Oct 21): v523 retained that poll, while
v524 reported a 120-frame host loop with no retail draw translation and an
incomplete PE entrypoint. The return-quantum implementation now lets ready
guest threads run after 64 successful nested guest-call dispatch returns, at a
guest call boundary. It changes no guest memory or API result and only yields
when the cooperative scheduler has another runnable thread; this is a
host-neutral scheduling approximation, not a cycle-accurate Windows time
slice. A focused fixture now busy-polls a marker written by a resumed worker
and passes without calling `SwitchToThread` in that polling interval.

The rebuilt runtime passed `shift_runtime_recompiled_pcode_module`. A
120-frame replay using the pinned PE and v512 cumulative module manifest
reached the host frame loop, but ended before caller `0x005ab6c0` ran. A
caller-only trace with a 2,000-frame bound then captured the retail wait-loop
transition: `0x006550f0` returned `EAX=1`, the following calls to `0x00655110`
and `0x005ab560` executed, and the failure snapshot recorded a write of
`0x00000006` to predicate word `0x27f39c64` by `0x00649b10` on worker thread
`0x00010006`. This confirms bit 2 became set and the poll loop was passed.

The retail frontier was then advanced with exact P-code exported from a
read-only working copy of the pinned Ghidra project. Ghidra 12.1.2_DEV and the
repository's targeted instruction exporters ran under OpenJDK 21. Functions
missing from the project were created only in `/tmp/process1-ghidra-copy`; the
original project and pinned PE were left untouched. The exports were lowered
with the pinned RevEngInstr snapshot `08a31b94c304f8b7a57996974dafe352413f7924`.
Across v527–v542, replay progressed through the missing-export chain from
`0x0057da20` to the `0x00587xxx` class accessors. In v542, Ghidra-confirmed
`0x00587c20` (`MOV EAX, 0x00ad5598; RET`) returned that exact pointer; the next
retail call from `0x00587790` stopped at the still-missing
`rvi_005879f0`. The PE entrypoint remains incomplete. Guest draw translation,
frontend readiness, a race, and retail rendering remain unproven. See the
[`Process 1 scheduler-quantum evidence`](../evidence/retail_frontier_20261021/process1_scheduler_return_quantum.json)
for the full frontier chain, hashes, commands, and limits. Latest main is `380f0283` (#2133), which updates captured mobile D3D9 target formats in the Vulkan bridge; it changes no Process 1 files.

The v569–v576 follow-up adds exact missing accessors from the pinned retail
PE, preserves unknown runtime targets for Ghidra BRANCHIND, and overrides
0x0063c670 with exact Ghidra P-code after the previous version returned -1.
The v576 UI-gate trace reaches the host frame loop with 5,211 unique functions
in that run, 715 frames, and zero Vulkan validation errors. This is a per-run
diagnostic count, not proof of frontend readiness or a race. The same trace
records 1,619 gate calls with the state word, callback object, and helper flag
still zero; guest draw translation and retail rendering remain unproven. See
the [v569–v576 Process 1 P-code evidence](../evidence/retail_frontier_20261021/process1_pcode_frontier_v569_v576.json)
for per-run reports, module hashes, and the remaining frontend limitation.

The v577–v593 continuation added exact P-code slices for the new retail
frontier and implemented the I386 `imagehlp.dll!StackWalk64` import. The API
fixture checks a valid frame-pointer chain, an uninitialized stack address,
and x86 stdcall cleanup. v591 advanced past the missing import; v592 reached a
P-code read at address `0x18`. v593 repeats that blocker with selected-call
tracing. Its dispatch totals vary and are diagnostic only. The complete
frontier, report/log hashes, module manifest, and test results are in the
[`v587–v593 evidence`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v587_v593.json).

To distinguish a translation fault from original retail behavior, the original
PE32 `SHIFT.exe` was launched directly under Wine 11.17 and stopped in the same
retail code at `0x0083a006`. A conditional WineDbg breakpoint captured the
receiver chain: thunk `0x0083a5c0` loads a nested record from outer `+0x50`,
then `0x0083a000` loads a null array pointer from nested `+0x3c`; with `EDX=0`,
the retail instruction reads `0x18`. The recompiled path reports that same
reserved-low-memory address. This shows the current P-code stop follows the
original read on this Wine run; it does not explain why the retail record is
null, prove native Windows behavior, or confirm frontend/race entry. The
[original retail evidence](../evidence/retail_frontier_20261021/original_shift_wine_crash.json)
records the exact debugger logs and limits.

The v594–v596 provenance follow-up sampled the nested array field directly.
Retail constructor `0x00839f30` stores zero at `inner+0x3c`; the later getter
thunk `0x0083a5c0` reaches `0x0083a006` with that field and `EDX` both zero.
The live v595 trace records the constructor and getter on the same guest thread
ID, so it does not support a scheduler race. Repeating the bounded probe with
the full copied retail game-data root did not change the first failing read.
No zero substitution or other guest semantic workaround was added because the
read follows the original instructions and the expected field population path
is still unidentified. See the [v594–v596 P-code evidence](../evidence/retail_frontier_20261021/process1_pcode_frontier_v594_v596.json).

The v597 trace found the missing initialization branch. Retail function
`0x0083dc50` passes the exact ASCII effect embedded at `0x00b8e988` to
`D3DXCreateEffect`; the compatibility layer accepted binary effects only and
returned `E_FAIL`. The retail caller then skipped `0x0083d470` and
`0x0083d850`, leaving its constructor-cleared `inner+0x3c` field null before
the getter read. A 32-bit D3DX9_41/D3DCompiler_41 compiler accepted the exact
retail source and produced a 1,140-byte effect with one `worldViewProj`
parameter, one `Default` technique and one pass. The runtime now uses that
compiled record only when the input matches the embedded retail source
byte-for-byte; altered text still returns `E_FAIL`. The focused test checks
both paths. This compatibility fix does not implement general ASCII HLSL
effect compilation or Vulkan shader binding. See the
[v597 trace and compiler evidence](../evidence/retail_frontier_20261021/process1_pcode_frontier_v597_d3dx_ascii_effect.json).

The original `SHIFT.exe` was also launched through PortProton GE-Proton 11-5
from a copy-on-write game-root and prefix clone. The process remained alive
for about eight minutes and GDB samples showed execution at three different
Gecko/Scaleform functions, while two screenshots showed a black game window.
That confirms original code execution, but not frontend or race readiness. It
is separate from the successful, user-confirmed race capture on 2026-10-18.
The [PortProton run evidence](../evidence/retail_frontier_20261021/original_shift_portproton_run.json)
records the image hash, cloned paths, screenshots, and limits. A separate
read-only observation of an already-running original retail process under
system Wine confirmed an X11 game window with Bink, D3DX9_41, and WineD3D
loaded; the visible capture was black and the process remained alive after
detach. Native GDB could not recover guest instruction pointers because of
the Wine i386:x64-32 target architecture. This was not a fresh controlled
launch and does not confirm frontend or race entry; see the
[live process evidence](../evidence/retail_frontier_20261021/original_shift_live_wine_observation.json).

The v621–v632 P-code continuation merged the exact `0x0049f2c0` body,
preserved lower-address Ghidra blocks while honoring each declared entrypoint,
and recovered all eight indirect switch targets in `0x00911429`. Caller-scoped
traces prove two completed calls to `0x00906246` and three completed returns
from `0x00911429`; the next confirmed stop was the internal block
`0x00d6fcbb` reached from entry `0x00d6fecc`. v631 merged that block under the
correct entrypoint, but its 360-second traced replay timed out. A 900-second
untraced v632 replay passed that loop and stopped at the exact RET instruction
`0x00403cbb` reached from `0x0046ffd1`; v633 exported that RET as a one-byte
alias. v634 then corrected the dynamic `BRANCHIND` path in `0x006d8d90` and
captured two successful calls each to `0x006d8d30` and `0x006d9680` before the
next virtual dispatch at `0x006d8de0` stopped with `-1`. v635 applied the same
Ghidra-derived dynamic-target fallback to that thunk and captured a successful
call to `0x006d9800`; its caller then stopped at an unexported two-instruction
getter, `0x006dcf20`. Ghidra had not marked that address as a function, so the
exact retail LEA/RET body was defined in an isolated project copy and exported
as v636. That run passed the getter and reached `0x0052b380`, where a
conditional branch targets a non-contiguous success epilogue at `0x0052b3c5`.
v637 merged the exact Ghidra-exported epilogue into the same function body; the
generated code kept the conditional path as an internal branch and the replay
passed that function. The next function, `0x0052bad0`, has the same omitted
success-epilogue shape at `0x0052bb34`; v638 merged that block into its parent
body.
v638 produced no frontier result and was stopped for debugger inspection;
v639/v640 also timed out without a confirmed failure. The full v641 replay
advanced to the next missing export, `0x00515970`, called by `0x00514760`.
Ghidra had not marked that address as a function. In an isolated project copy,
Ghidra defined the exact 14-byte retail body and exported four instructions
(18 P-code operations) for v642. Its trace confirmed a return with `EAX=0x00bdcf68`
and exposed the next missing getter at `0x00515a60`. v643 returned from that
getter with `EAX=0x00bdcff8`, then reached `0x00515b80`. Its generic comparison
marked fewer dispatches as regressed; the caller-scoped trace proves the later
unresolved target, and dispatch counts remain diagnostic. Ghidra exported the
exact `0x00515b80` body as four instructions and 18 P-code operations for v644.
Its replay returned `EAX=0x00bdd088`, then reached `0x00515d80`; the generic
comparison marked fewer dispatches as regressed, while the caller trace proves
the later target. Ghidra exported the exact 14-byte `0x00515d80` body for v645
(four instructions, 18 P-code operations), and its replay is running against a
fresh runtime build with caller-scoped tracing. v645 returned from `0x00515d80`
with `EAX=0x00bdd1bc`, then reached `0x00516120`; again, the exact trace
confirms progress despite the counter comparison. Ghidra exported the exact
`0x00516120` body for v646 (four instructions, 18 P-code operations). Its
replay returned `EAX=0x00bdd258` and reached `0x00515ee0`. A retail `.text`
scan then found 15 more exact 14-byte wrappers around the same lookup; Ghidra
exported all 15 together and a single supplement carries their exact P-code.
The v647 replay returned from six distinct getter functions in the traced caller,
including `0x00515ee0` with `EAX=0x00bdd2f4`, then reached `0x005136a0`. The
remaining four wrappers at the start of this method family were exported as an
exact Ghidra batch for v648. The six returns are specific call evidence, not a
global count of all functions. Current evidence is tracked in
[`process1_pcode_frontier_v621_v659.json`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v621_v659.json).
These call returns are function-specific evidence. Per-run dispatch and unique
function counts remain diagnostics and do not prove that the frontend or a race
was reached.

The v649/v650 continuation returned from two exact state setters and reached
`0x00894da0`; v652 exported that function and its selected trace recorded a
normal return with `EAX=0`. The next missing export, `0x0088a2c0`, was a flag
clear followed by a direct tail jump to `0x0088a0e0`. v653 merged both exact
Ghidra bodies under entry `0x0088a2c0`; generated C keeps the tail jump as an
internal `goto`, and a targeted regression covers this shape. The trace proves
entry but no return before a nested call reached the next missing target,
`0x007d6570` from `0x007d5f10`. Ghidra had not marked that retail address as a
function. An isolated copy of the pinned Ghidra project defined the exact
77-byte body through `0x007d65bc`. v654 recorded entries into `0x007d6570` and
its helper `0x007d6470`, then stopped at the nested missing export
`0x00698390` from `0x0064879e`. Ghidra had not marked that address as a
function either; the exact 20-byte retail body ending at `0x006983a3` was
defined and exported for v655. Caller-scoped traces then confirmed returns
from `0x00698390` (EAX `0`), `0x00647860` (EAX `0x11`), `0x007d6470` (EAX `0`),
and `0x007d6570` (EAX `0xfffffff9`). The next P-code failure was at the retail
indirect-jump thunk `0x00888f70`; its failure snapshot retained EAX
`0x0040ae20`, loaded from `[ECX+0x958]`. v656 exports the exact Ghidra body
for that thunk and applies the builder's tested runtime `BRANCHIND` fallback,
preserving its conditional `JMP EAX` semantics. Its caller-scoped trace then
proved that the runtime reached the exact dynamic target `0x0040ae20`, where
the next missing P-code export stopped execution. Ghidra had not marked that
target as a function; the exact 26-byte body through `0x0040ae39` was defined
in an isolated Ghidra copy and lowered for v657 (eight instructions, 35
P-code operations, no rejected instructions). v657 then proved that
`0x00888f70`, `0x0040ae20`, and its helper `0x00489ad0` all returned; the getter
took its exact null-field path and returned `EAX=0xffffffff`. v658 exported the exact 116-byte body of `0x005ab3f0` from the pinned retail
Ghidra project (30 instructions, 119 P-code operations, zero rejected). The
replay entered it from `0x00647d80`, then reached `0x005ab230` and stopped at
that method's dynamic target `0x005a0ef0`. A trace-return event showed
`EAX=0x005a0ef0`, but the failure snapshot retained the nested unresolved call
and the retail body's terminal path explicitly returns zero, so this is not
counted as a normal return. v659 exported the exact two-instruction getter at `0x005a0ef0` (`MOV
EAX,[ECX+0xb8]; RET`, six P-code operations). Its caller-scoped replay
confirmed 701 returns each from `0x005a0ef0`, `0x005ab230`, and `0x005ab3f0`,
all with `EAX=0`. The bounded run completed 1,440 host frames and reached the
host frame loop with no P-code blocker; `guest_main_thread_function` was
`0x007d7620`. This is recompiled-runtime evidence, separate from the original
retail launches. It does not confirm frontend/race readiness, and the bridge
recorded no guest draw translation. The current frontier and per-run hashes
are in
[`process1_pcode_frontier_v621_v659.json`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v621_v659.json).
Dispatch totals remain diagnostic; they do not prove game startup.

For a UI-gate probe, set `SHIFT_TRACE_UI_STATE_GATE=1` and
`SHIFT_TRACE_GUEST_PROVENANCE=0x00be250c,0x00be2534`. Each `0x0050c880` trace
event then includes exact-byte `helper_flag_last_writer` provenance, with the
last P-code writer's function, receiver, caller, return addresses, and store
details when available.
`SHIFT_TRACE_GUEST_CALLER=0x0049eb30` records calls from the helper activation
path. For a selected caller, `SHIFT_TRACE_GUEST_CALLER_SLOTS=0x1ef8,0x1efc`
samples 32-bit words at those offsets from the caller's entry ECX. Events keep
`ecx_entry` for the child callee and `caller_ecx` for the selected caller's
entry receiver. Direct P-code calls also record their return EAX and completion
status. A call `entry` is an attempted dispatch; it can appear for a missing
export. The trace now records `target_resolved`, and unresolved targets emit a
`shift_guest_call_trace_unresolved` event with the missing-export reason. If a
sampled absolute address is included in
`SHIFT_TRACE_GUEST_PROVENANCE`, its `last_writer` records the last overlapping
P-code store. At most 32 offsets and 8,192 call events are retained. An omitted
writer means the probe did not record a P-code store overlapping that address;
synthetic MGEO or other host-side state is not retail evidence.

`SHIFT_TRACE_GUEST_CALL_TARGETS=0x0066bb50,0x0066b8d0` instead records calls
to up to 32 selected guest targets from any caller. If caller and target filters
are both set, either match records the event. Each event carries the actual
caller, callee-entry registers, return address, and direct-call EAX result. The
frame JSON lists selected `guest_call_trace_targets`.
`SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS=0x218,0x340` additionally samples up to
32 32-bit words at those offsets from each selected target's entry ECX. These
`target_slots` use the same read and last-writer fields as `caller_slots`, but
are relative to the callee receiver. They make state read by a selected method
observable even when its caller is not known in advance. Offsets are direct
receiver-relative reads; they do not follow pointer fields.
`SHIFT_TRACE_GUEST_CALL_STACK_SLOTS=0x4,0x8,0xc` samples words at those offsets
from the callee-entry ESP for each selected call. Since `[ESP]` holds the return
address, offset `0x4` is the first 32-bit stack argument. This also exposes
arguments passed to selected imported calls. The `stack_slots` array has the
same value and writer fields, with the same 32-offset limit. `dispatch_count`
marks call entry; `completion_dispatch_count` marks its return and is null while
the call is still pending.
`SHIFT_TRACE_GUEST_CALL_IMPORTS=KERNEL32.dll!SetEvent,KERNEL32.dll!ResetEvent`
selects named imported API calls independent of their synthetic stub addresses;
import events carry the same caller, return address, and stack slots.
`SHIFT_TRACE_GUEST_CALL_STRING_SLOTS=0x4` additionally samples bounded
printable ASCII C strings from selected calls' entry stack arguments. Each
`string_slots` item records its stack offset, guest pointer, captured value,
whether a terminator was seen, and whether the 256-byte sample limit was hit.
This is opt-in and complements the numeric `stack_slots`; it is intended for
inspecting paths passed to APIs such as `CreateFileA` without dumping guest RAM.
For target/caller/import traces, `SHIFT_TRACE_GUEST_CALL_LIVE_LOG=1` writes a
compact entry line to the probe log before the selected call runs and a return
line when it completes. Imported calls include their resolved API name in both
lines. This preserves entry registers and sampled stack/target slots if the
bounded probe later times out; a missing return line means the selected call
had not completed when execution stopped.

The v217/v218 bounded runs reproduce the same 96,082-dispatch, 1,559-function
host-frame-loop checkpoint with 120 Vulkan clear and 120 present submissions,
zero validation errors, and no guest draw translation. Across 121 gate/helper
evaluations, the state word and helper byte remain zero and the helper byte's
last writer is constructor `0x0050c820`. A call trace from `0x0049eb30` records
no activation calls. See
[`entrypoint_probe_v217_v218_ui_helper_flag_writer.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v217_v218_ui_helper_flag_writer.json)
and the [UI state-gate evidence](REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md).

The v219 repetition uses exact-byte last-writer tracking and confirms the same
121 zero-valued helper calls with the final instrumentation build. Its fixture
also verifies that a later write to an adjacent byte cannot replace the
target byte's writer record. See
[`entrypoint_probe_v219_ui_helper_exact_writer.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v219_ui_helper_exact_writer.json).

The v223/v225/v226/v228 activation trace narrows the next UI gate. Across the
same 120-frame host-loop checkpoint, `0x00508ea0` and `0x00508e90` each return
zero 121 times from `0x0054bb20`; `0x00508ec0` is never called. Ghidra maps
`0x00508e90` to the helper object's `+0x2d` byte, which remains zero. The
`0x005093a0` update leaves a child in state 7; its `0x00508af0` readiness method
returns a zero low byte while `+0x218` is 2 and `+0x340` is 1. Exact-byte
provenance attributes the pending `+0x218` value to `0x0066bb50`, called from
`0x0066cc00` during the request path through `0x0065fa60`. Follow-up caller
traces v229–v239 expose the setup path and distinguish the active flag from
cleanup. In v237, a target-wide trace sees one call to `0x0066bb50` from
`0x0066cc00`, but no call to `0x0066b8d0` in the 120-frame guest call stream.
In v238, owner byte `+0xb8` is zero on entry to `0x0066cc00`; v239 shows that
function setting it to one before the following `0x00653480` call. Static PE
disassembly shows `0x0066cc00` calls `0x0066cb60` only if the byte is already
set, and `0x0066cb60` conditionally calls `0x0066b8d0`. That cleanup is not
established as the asynchronous completion callback. The pending request is
active, but the worker/consumer transition that should update readiness remains
unresolved. See the [activation-frontier analysis](SHIFT_RETAIL_UI_ACTIVATION_FRONTIER_20261019.md)
and [machine-readable evidence](../evidence/retail_frontier_20261019/entrypoint_probe_v229_v239_async_request_calls.json).

The v240 target-receiver-slot probe follows the consumer call after
`0x00653480`. It reaches `0x0066bab0` once, which returns one; its selected state
checks return `1, 0, 0`, then the path calls `0x006880c0` and `0x00650350`.
There are still no calls to `0x0066b8d0`. The target-slot samples independently
confirm that `0x00508af0` is called 120 times with receiver `+0x218 == 2` and
`+0x340 == 1`, returning a value whose low byte is zero each time. The run
remains at 96,082 dispatches, 1,559 unique functions, four waiting workers,
120 Vulkan clear/present submissions, zero validation errors, and no guest
draw translation. This narrows the state-machine path but does not identify a
completion callback or prove frontend readiness. See the
[v240 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v240_consumer_target_slots.json).

The v246 imported-API trace resolves the `0x60004` event sequence. The
`CreateEventW` call creates it as auto-reset and initially unsignaled. A worker
enters an infinite `WaitForSingleObjectEx` at dispatch 19324; `SetEvent` on
that handle succeeds at dispatch 64589, and the original wait returns at
dispatch 64636. The same worker enters another infinite wait at dispatch 65095,
which remains pending. No `ResetEvent` call targets `0x60004`. This is a normal
one-signal/one-waiter sequence: the wake was consumed by the wait already in
progress, then the worker returned to waiting. The import trace records 127
events and is not truncated. See the
[v246 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v246_import_event_api_completion.json).

The v247 worker trace follows the first wake back through the loop at
`0x00667284`: the wait completes at dispatch 64639, `0x00655190` runs at
64640, and `0x00649750` runs at 64641 before the worker enters another wait at
65096. Static PE disassembly maps the indirect call at `0x00aa62e8` inside
`0x00649750` to `KERNEL32.dll!SetThreadPriority`. The v248 named-import trace
confirms that this call receives thread handle `0x00080000` and priority `0`,
then returns success. `0x00655190` loads the worker object's child and its
`+0x54` priority field before tail-calling `0x00649750`; this path applies
thread priority after a wake and does not identify a queue payload consumer.
The selected trace recorded 13 `SetThreadPriority` calls and seven
`0x00649750` calls without truncation. See the
[v247 worker-loop record](../evidence/retail_frontier_20261019/entrypoint_probe_v247_post_wake_worker_loop.json)
and [v248 priority record](../evidence/retail_frontier_20261019/entrypoint_probe_v248_thread_priority.json).

The v249–v252 probes follow the request through the worker queue. In v249,
`0x00650350` calls `0x0064fef0`, `0x00650290`, and `0x0064f530`; the last call
successfully signals auto-reset event `0x60004`. The async-file worker
(`0x00010000`) wakes from its pending wait and dispatches operation 3 through
`0x006671b0` to callback `0x00655ab0` on receiver `0x27ed9284` (v250/v251).
The callback returns status 4. Its guard `0x00655440` calls `CreateFileA` with
read-only access, but the API returns `0xffffffff`; the worker then takes its
status-4 path, and readiness fields remain unchanged (v252). This explains why
the event wake alone did not complete the UI request. The file path pointer
`0x28249b16` was visible, but its string was not captured in v252. The next
probe uses the opt-in string-slot trace to record that path and identify the
resource lookup failure. See the [v249–v252 worker evidence](../evidence/retail_frontier_20261019/entrypoint_probe_v249_v252_async_file_frontier.json)
and the [activation-frontier analysis](SHIFT_RETAIL_UI_ACTIVATION_FRONTIER_20261019.md).
All four probes remain bounded 120-frame host-frame-loop runs with no guest
draw translation; they do not establish frontend readiness or gameplay
rendering.

The v253/v254 follow-up captures the file path and fixes the resulting generic
Linux path lookup gap. The worker passes `C:\\pakfiles\\bootpersistent.bff`;
the installed retail file is `Pakfiles/BOOTPERSISTENT.bff`. Before the fix,
`CreateFileA` returned `0xffffffff`. The guest path resolver now resolves
existing ASCII path components without case sensitivity, while keeping the
resolved canonical path inside the game-data root. The mixed-case fixture
regression passes. In v254, `CreateFileA` opens the retail file and the caller
consumes `GetFileSize` result `0x00156c72`, then P-code function `0x005f1830`
returns `-1` at 71,631 dispatches. This advances the file path but does not
reach the bounded host-frame loop; no frontend or rendering claim follows.
See the [case-folded file lookup evidence](../evidence/retail_frontier_20261019/entrypoint_probe_v253_v254_casefold_file_lookup.json).

The v256 failure trace exposes a second P-code lowering boundary. Static PE
evidence and the sampled guest vtable agree that `0x005f1830` loads the vtable
from `[ECX]` and tail-dispatches through `[EAX+8]` to `0x0066cd60`. The
generated function only accepts its two internal branch addresses and returns
`-1` for this external target. A tested address-specific override in the
frontier module now preserves that instruction sequence and hands the target
to the runtime dispatcher. In v257, `0x0066cd60`, `0x0066bbf0` and
`0x0066ccc0` all complete; execution advances nine dispatches and seven unique
functions before stopping at missing export `0x00652b13`, called from
`0x00652af0`. The probe still does not reach the host-frame loop, and proves
neither frontend readiness nor rendering. See the [v256/v257 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v256_v257_indirect_tail_frontier.json).

The v258–v273 cumulative sequence resolves the async-file and P-code chain, then
separates a bad indirect target from a split-continuation return. `ReadFileEx`
uses the `OVERLAPPED` offset and queues its callback for the initiating guest
thread's alertable wait. The path then reaches the exact virtual dispatcher
`0x005b0d50`, request handler `0x0066cc70`, and CRC32 worker `0x0066caf0`.
Flattening the CRC worker's direct-jump loop avoids one nested runtime dispatch
per input byte. v261 reaches 457,430 dispatches / 1,727 unique functions and
stops at `0x00509689`; the subsequent recovered blocks `0x00509e60` and
`0x0050967d` advance to 515,860 / 1,751.

v264 stops at indirect call target `0x27f30a50` from `0x0040ba50`. The runtime
now traces unresolved targets: v266 records return address `0x0040bb04`, which
places the failing `CALL EAX` at `0x0040bb02`. v267 provenance identifies the
actual table slot at `0x27f30a90`: allocator `0x00427330` wrote pool address
`0x27f30a50` there. The first word at that target is `0x0b`; this is pool data,
not a P-code function address. Do not add a dynamic-code adapter for it.

The selected-call trace then shows a separate register issue. In v268–v270,
`0x0054bb20` returns with `EDI` changed from `0x27e31278` to `0x27f30a98`.
v269 narrows the change to nested `0x005093a0`; v270 shows `0x005089c0`
preserves `EDI`, while the `0x0050958c` continuation returns with `EDI` changed
and `EAX == 3`. Ghidra shows that this continuation belongs to the active
`0x005093a0` frame and reaches a shared callee-saved-register epilogue. The
separately dispatched continuation can return before that epilogue, leaving
the parent frame active. The `0x0050967d` adapter now completes that epilogue
only when `ESP == EBP - 0x18`, restoring saved `EDI`/`ESI`/`EBX`/`EBP`, the
expected `ESP`, and the function's zero return value. Its fixture covers both
the tail continuation and this active-frame case.

v271 advances to missing export `0x005095f0`, called from `0x00509551`, at
516,250 dispatches / 1,751 unique functions. This confirms the previous
heap-address stop was caused by the incomplete continuation return; it does
not reach the host-frame loop. One-dispatch fluctuations in v267–v270 keep the
same blocker and unique-function count, so they are treated as probe noise.
The `0x005095f0` state-3 adapter advances v272 to missing initializer
`0x0054b560`, called from `0x005088e0`, at 516,254 / 1,752. Ghidra 12.1.2
instructions lowered through revenginstr produce a 20-instruction, 48-op
initializer body; its fixture verifies helper order, receiver values, `RET 4`
cleanup, ESI preservation, and return value 7.

v273 executes that initializer and reaches missing export `0x0085b0b0` from
`0x0040e630`, at 518,457 dispatches / 1,789 unique functions. Byte-level
disassembly of the pinned PE shows the exact two-instruction body:
`MOV AL,[ECX+0x32f]; RET`. Its adapter preserves EAX's high bytes and models the
guest return. The cumulative v274 trace confirms entry EAX=`0x0085b0b0`,
return EAX=`0x0085b000`, and unchanged EDI; the sampled receiver byte is zero.
The run advances to missing export `0x0082f600` from `0x0040d910`, at 524,846
dispatches / 2,006 unique functions. That stateful body is the next recovery
target. Exact per-run hashes, lowering provenance, and object/register evidence
are in the
[v258–v274 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v258_v274_pcode_worker_frontier.json).
All runs remain bounded startup probes before the host-frame loop. They do not
establish frontend readiness, retail draw translation, or gameplay rendering.

The v275–v280 sequence follows a later cold-start path. v275 adds the exact
49-instruction P-code body at `0x0082f600` and stops at
`KERNEL32.dll!CreateDirectoryA` from `0x00a631f0`; the captured path is
`render\shaders\cache\`. The bounded `CreateDirectoryA` implementation keeps
the existing guest-root path confinement and single-directory semantics. Its
failure to create this nested path when parents are absent returns false, after
which v276 reaches `IDirect3DDevice9::TestCooperativeLevel` from
`0x0084f3b0`. The method currently returns `D3D_OK` only for a registered
runtime device. v277 then identifies missing P-code `0x0082d5f0`; its exact
two-instruction body loads `[ECX+0x680]` and returns. Lowering that function
through revenginstr advances v278 to `d3dx9_41.dll!D3DXCreateEffect` from
`0x0083de30`, at 526,429 dispatches / 2,049 unique functions.

The v279/v280 diagnostics establish that the D3DX source argument is binary,
not an ASCII string. It is 0x7c0 bytes and begins with
`01 09 ff fe 0c 04 00 00`; v280 records the next 24 bytes in the machine
evidence. The v281 one-frame repeat captures the complete 1,984-byte input
outside Git (SHA-256
`74901707d164f3014e8dc72da7232b1076d003ae3288535ca7c8376aec923fa9`). Its
binary effect table describes two parameters, one technique, three shader
variables, and seven objects. The technique/pass are `ShadowGen`/`Pass0`; the
resource is `ERMB_RENDER`, with `ps_3_0` and `vs_3_0` shader profiles. The
captured data is not committed.

v281 reproduces the same blocker at 526,429 dispatches / 2,049 unique
functions. Static caller analysis shows that `0x0083de30` checks and releases
the compile-error buffer, then uses the effect pointer at receiver `+0x0c` to
call `ID3DXEffect::FindNextValidTechnique` at vtable byte offset `0xf4`.
Successful setup then enumerates techniques, parameters, annotations, and
passes through helpers `0x0083d470` and `0x0083d850`. Thus a parser that only
returns a placeholder effect cannot advance this caller; shader creation and
binding are also required later. The probe remains blocked before the host
frame loop, with no retail draw or Vulkan submission. See the [v275–v280
machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v275_v280_pcode_effect_frontier.json)
and [v281 effect capture record](../evidence/retail_frontier_20261019/entrypoint_probe_v281_d3dx_effect_capture.json).
For the API contract, Microsoft documents that `D3DXCreateEffect` accepts an
ASCII or binary effect description and returns an `ID3DXEffect` on success;
Wine's parser reads the binary tag and offset before its structured effect
parser ([Microsoft API reference](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dxcreateeffect),
[Wine effect parser](https://github.com/wine-mirror/wine/blob/master/dlls/d3dx9_36/effect.c)).
This confirms that implementing the next step requires effect state and
interface behavior; returning a fabricated success pointer would not be a
valid compatibility fix.

The v282 implementation adds a bounds-checked parser for D3DX9 binary effect
version 9.1, including parameter types and values, annotations, techniques,
passes, states, and resource blobs. A synthetic CTest covers a shader state,
resource-to-object association, and truncated input. Running that checker
against the external v281 capture parses 2 parameters, 1 `ShadowGen` technique,
1 `Pass0`, 7 objects, and 2 shader resources of 144 and 404 bytes. This is
format parsing evidence only: `D3DXCreateEffect` still has no runtime COM
implementation, the shader bytecode is not translated or created on Vulkan,
and the retail startup probe has not advanced. The capture and its payloads
remain outside Git. See the [v282 parser record](../evidence/retail_frontier_20261019/entrypoint_probe_v282_d3dx_effect_binary_parse.json).
The capture check accepts an optional external file argument:
`native_runtime/build/shift_runtime_d3dx9_effect_binary_check /path/to/effect.bin`.
The next runtime change must construct the effect interface from these parsed
records and route shader creation through the D3D9/Vulkan backend.

The v283 runtime step routes `d3dx9_41.dll!D3DXCreateEffect`, parses the
captured binary into a guest `ID3DXEffect`, retains its D3D9 device reference,
and implements `QueryInterface`, `AddRef`, `Release`, and vtable slot 61
(`FindNextValidTechnique`) in the 79-slot D3DX9_41 table. A regression test runs both a synthetic shader
effect and the external v281 capture through this import and COM path. Since
the runtime still cannot create or bind the effect's shaders, searching from a
null technique returns `S_FALSE` and a null handle; the remaining effect
methods are still unimplemented imports. A bounded retail probe was rerun with
the v215 pinned module set, but timed out after PE load at 300 seconds without
a usable frontier report. Earlier runs with the launcher's default module set
stopped on missing P-code exports and are not comparable to v281. The capture
test confirms the COM import path only; no retail startup advance, game draw,
or Vulkan submission is established. The v281 capture remains external. See
the [v283 effect COM record](../evidence/retail_frontier_20261019/entrypoint_probe_v283_d3dx_effect_com.json)
and [v284 retail probe record](../evidence/retail_frontier_20261019/entrypoint_probe_v284_d3dx_effect_retail_timeout.json).

The v285 repeat used the same pinned v215 module set, one host frame, Vulkan
validation, and a 120-second bound. It again timed out after the PE-load
diagnostic; the parser produced no dispatch count or frame-loop report. A GDB
snapshot taken while the process was live placed its main thread in generated
P-code exports `0x0090e4b6`, `0x0090e50d`, `0x009015b0`, and `0x006344c0`.
The other sampled threads were waiting inside the NVIDIA driver. This locates
the active native stack in guest P-code, but the bounded snapshot does not
identify the owning guest call chain, prove that `FindNextValidTechnique` was
called, or establish that Vulkan is the cause. System I/O pressure was above
94% during the run, which may have affected timing but does not explain the
guest stack. See the [v285 stack record](../evidence/retail_frontier_20261019/entrypoint_probe_v285_effect_native_stack.json).
The subsequent v286 work decompiled the zero-fill helpers and samples the next
guest path; see the next record before changing effect semantics.

The v286 change implements the exact cdecl byte-fill behavior of
`0x0090e50d` through a bounds-checked runtime `memset` callback. The
address-specific P-code adapter retains guest return state, and selected-write
provenance records only watched words overlapped by the fill. Its fixture
passes an unaligned 200 KiB fill, boundary sentinels, register-preservation,
and zero-length cases. The pinned one-frame retail probe still times out at
120 seconds and emits only the PE-load message, so there is no dispatch-count
or frame-loop proof. GDB snapshots no longer show the previous
`0x0090e50d` zero-fill chain; they show `0x0066f680 → 0x00675420 → 0x00678480`
and nested `0x00679aa0/0x00679760`. Static disassembly shows table-driven
bit/symbol reads and output-byte writes, consistent with compressed-stream
decoding, although the exact resource and codec are not established. This is
evidence that execution passed the zero-fill hot path, not a measured frontier
advance. See the [v286 record](../evidence/retail_frontier_20261019/entrypoint_probe_v286_bulk_fill_frontier.json).
The next step is to identify and profile the decode path before choosing a
second optimization; the timeout does not identify an effect or Vulkan fault.

The v290 static inspection pins the same retail PE hash and disassembles the
decoder wrapper at `0x0066f680`. Its five cdecl arguments are a context, output
buffer, output-count pointer, input buffer, and input byte length. The wrapper
reserves the final five input bytes, reads either a two-byte length header for
`0x8000` output bytes or a five-byte `0xFF` extended header containing
big-endian output/input lengths, then invokes stateful block decoding. The
wrapper uses the encoded length as its loop range when it is shorter than the
remaining bytes; malformed overlong lengths are not characterized. The
`0x00675420` helper stores the input range and output pointer in the context;
the nested `0x00679aa0`/`0x00679760` path performs table-driven bit/symbol
decoding and output writes. The v290 record captured the then-current static
interpretation, including a hypothesis that the final five bytes were reserved
once for the whole input. The later live captures supersede that framing
hypothesis: the XMem decoder's per-`0xFF` five-byte trailer matches the retail
outputs exactly in 310 sampled calls. See the [v290 decoder record](../evidence/retail_frontier_20261019/entrypoint_probe_v290_decoder_framing.json)
and the [v296 equivalence record](../evidence/retail_frontier_20261020/entrypoint_probe_v296_decoder_equivalence.json).

The v291 report records only PE loading, with no dispatch count or decoder
call. Its external runtime did not stop when the requested 300-second SIGTERM
limit elapsed; the former launcher had no kill-after bound. That report is now
retained as
[`entrypoint_probe_v291_decode_call_trace.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v291_decode_call_trace.json).
An in-flight debugger snapshot placed the main thread in guest function
`0x00455ba0`; pinned-PE disassembly shows a tail thunk at `0x00427250` and a
count-dependent aligned allocation followed by 16-byte link initialization.
This identifies a potentially expensive setup path, but without the entry
`EDX` value it does not explain the stall or provide decoder input.

The bounded v292 replay used the verified 2-override/19-supplement v215
manifest and a 120-second wall limit. It loaded the PE but emitted no dispatch
frontier before timing out. Two GDB snapshots during the live process show the
guest stack inside `0x0066f680 → 0x00675420 → 0x00678480 → 0x00679aa0 →
0x00679760`, ending in guest-byte reads/writes. This confirms the decoder
wrapper is active in the PortProton game-data root; it does not provide the
wrapper's stack arguments or bytes. The live-stack summary and snapshot hash
are in
[`entrypoint_probe_v292_decoder_live_stack.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v292_decoder_live_stack.json).
The v296 capture uses the current `native_runtime/build` P-code frontier module
and selects `0x0066f680` calls from `0x0066cec0`. It captured 310 completed
calls through dispatch 346,879: 817,378 compressed bytes and 5,393,638 decoded
bytes, with one-, two-, and three-frame inputs. The shared output-count word
can be overwritten by the next call before an external observer reads it, so
capture lengths are derived from each input's checked frame headers. Raw pairs
remain in the external artifact directory; Git stores only hashes and counts.
The existing `shift_xmem_decompress_auto` result was byte-identical to every
retail output (310/310), including calls with multiple frames. A fresh native
decoder state per wrapper call was sufficient for this sample. The probe was
stopped after collecting the pairs and does not provide a frame-loop or
rendering result.

The runtime now overrides `0x0066f680` with a fail-closed native XMem adapter.
It validates the captured cdecl stack contract, bounds compressed and decoded
sizes, copies guest memory in the runtime's 16-byte access limit, writes the
decoded-size out parameter, and emulates the observed `EAX=0`, cdecl return.
A synthetic raw-block fixture verifies decoded bytes, the out parameter,
callee-saved registers, and `ESP/EIP`. The next retail probe must load this
frontier module from `native_runtime/build`, then compare startup progress with
the v215 host-loop checkpoint; decoder equivalence alone is not a boot or
rendering result.

The bounded v297/v298 cold starts timed out after PE load and produced no
dispatch/frame report. Two v298 live GDB snapshots showed the main thread in
the recurring allocator path
`0x0082de70 → 0x0083f0f0 → 0x004f5e60 → 0x004f5e10 → 0x00d86830 →
0x00427250 → 0x00455ba0`; those snapshots alone did not establish a hang in
that function. The v299 live target trace resolves the pending call: 79 of 80
calls to `0x00455ba0` returned, then the call at dispatch 417,061 entered with
`EDX=0` and had no return event before the 120-second bound. PE disassembly
shows this function sizing a 16-byte-node pool from `EDX`, then using an
unsigned decrement loop; zero underflows to `0xffffffff` and prevents the loop
from finishing.

The v300 receiver trace shows the zero comes from global receiver
`0x00c288cc`: the first call from `0x0083f0f0` sees receiver fields `+0x4` and
`+0x8` both zero, then `0x00d86830` forwards `EDX=0` to the allocator. Static
PE disassembly of `0x00a8d940` shows it initializes this object, calls
`0x0067cbc0`, writes `0x10` to `+0x4` and `+0x8`, and clears selected fields.
The v301 trace records one call to CRT helper `0x00915fe8` at dispatch 300; it
returns immediately with `EAX=0x00b6c15c`. Its PE body iterates the empty range
`[0x00b6c15c, 0x00b6c15c)`. This is distinct from the non-empty C++ global
initializer list later traversed by CRT `__cinit`. The PE TLS directory has no
callback entries. The `.rdata` excerpt at `0x00aa92c0` contains absolute
pointers to functions with global-initialization effects: `0x00a8d770` and
`0x00a8d800` initialize camera globals, and `0x00a8d940` initializes receiver
`0x00c288cc`.

The v302 bounded replay selected 14 function VAs from the nearby `.rdata`
excerpt for live call logging. It timed out with only PE-load and timeout
lines, so it did not locate the stall. Static disassembly then resolved the
consumer: entrypoint startup calls CRT `__cinit` at `0x00907583`, which calls
`__initterm_e` over `[0x00aa996c, 0x00aa9988)` and, on success, walks the C++
initializer list `[0x00aa66d4, 0x00aa9968)` in four-byte steps. The list contains
`0x00a75c40` at `0x00aa6828` and `0x00a8d940` at `0x00aa92f0`.

v303 observed the startup call into `__cinit`, all six nonzero error-init
callbacks returning `EAX=0`, and the return from `__initterm_e`. v304 then
recorded C++ initializer calls through `0x00a75c40`; it saw no later list
entries. The v305 register trace explains why: `0x00a75c40` enters with
`ESI=0x00aa6828` and returns with `ESI=0x27f48c20`, while the upper bound in
`EDI` remains `0x00aa9968`. Its next loop iteration therefore reads outside
the initializer list. v306 traces the change through `0x0041d7b0`, a jump thunk
to `0x0050f010`; the preceding call to `0x0063a210` preserves ESI.

v307–v310 locate the observed register/stack mismatch at `0x0050f010`, but an
audit of the exact frozen instruction corpus used by the frontier module
changes the diagnosis. Its `0x0050f010` row declares a 531-byte function but
contains only 188 instructions, ends at NOP `0x0050f3f3`, and has no RET or
return-flow instruction. In the pinned PE, the function's return block is at
`0x0050f478`–`0x0050f481`: it sets EAX to 1, restores ESI/ESP/EBP, then RETs.
None of the epilogue instruction addresses appears in any row of the frozen
corpus. This makes incomplete function-body/CFG export the leading cause of
the mismatch; the traces do not establish a defect in the shared P-code
lowerer or native runtime. Recover and verify the complete Ghidra body, rebuild
the function export/module, and replay startup before changing generic runtime
behavior. Do not add a loader-side initializer scan or allocator workaround.
The fast XMem adapter and v215 D3D9/Vulkan frame-loop checkpoint are still not
revalidated. See the
[v297–v302 machine record](../evidence/retail_frontier_20261020/entrypoint_probe_v297_v302_initializer_order.json)
and [v303–v310 initializer trace](../evidence/retail_frontier_20261020/entrypoint_probe_v303_v310_cinit_esi_stack.json).

The v120 caller-call trace independently maps the common tail of `0x0054be00`:
the `+0x13c` virtual call dispatches `0x00833670` (D3D9 EndScene path), and the
`+0x130` call dispatches `0x00835d80` (D3D9 Present path), 121 times each in a
120-frame probe. The false UI-gate branch therefore reaches frame EndScene and
Present service calls. This still does not establish retail draw submission or
frontend readiness; see
[`ui_gate_common_tail_dispatch.json`](../evidence/retail_frontier_20261019/ui_gate_common_tail_dispatch.json).

~~~bash
python3 tools/retail_frontier.py inspect \
  --log evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log \
  --baseline evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log \
  --output artifacts/frontier/v173-check.json
~~~

Exit status: 0 for unchanged/advanced observed frontier; 1 for regression/changed frontier needing review; 2 for configuration, failed build, timeout or unparseable probe. A blocked game startup is explicitly recorded as **blocked**, never as a successful game launch.

## 3 — Compare D3D9 call contracts with Windows/PortProton

~~~bash
python3 tools/compare_shift_d3d9.py \
  --reference /path/to/original-proxy-capture.jsonl \
  --candidate artifacts/frontier/current.log \
  --event create_texture --max-events 2000 \
  --output artifacts/frontier/d3d9-comparison.json
~~~

The comparator reads original proxy JSONL and a candidate Linux JSONL or v173-style diagnostic. It compares **stable argument fields** in event order, ignoring device pointers, texture addresses, frame numbers and machine-local paths. Supported events: create_texture, create_device_begin, create_device_result, clear, draw_indexed_primitive, set_texture. Use repeated --event flags to select more types.

The v173 diagnostic only shows a *request* to D3DXCreateTexture. If those fields appear in retail capture, result request-only-match is **not** confirmed creation or render parity. For full comparisons the Linux runtime must emit structured events with the corresponding event names. Use --strict to make missing events fail. A positive comparison still needs resource provenance and lifetime validation.

## 4 — Regression gates

~~~bash
python3 -m unittest discover -s tests -p test_retail_frontier_tools.py -v
bash -n tools/build_shift_runtime_cached.sh
~~~

The stable linux-vulkan GitHub workflow runs these tests, checks the pinned v173 parser and uses an object-compiler cache. It does not attempt original-game execution on public runners. An **opt-in workflow_dispatch** input named run_retail_frontier runs a real probe on a Linux runner carrying the shift-retail label. That runner must already have Vulkan/XCB/Xvfb, CMake, the pinned retail resources, supplements and generated ELF installed; no asset is uploaded to Actions. Configure repository variables SHIFT_RETAIL_PE, SHIFT_RETAIL_DATA_ROOT, SHIFT_RETAIL_ARTIFACTS, SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE and (where needed) newline-delimited SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS and SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES. Outputs remain local under artifacts/frontier/ on the runner, and only the exit status gates the workflow. Without such a runner, use the local command above.

## Release milestones

Startup frontier metrics cannot stand in for gameplay. v194 and its
v215/v217/v218/v219/v240 replays establish the bounded retail-requested Vulkan
clear and queue-present milestone; v240 also narrows the pending UI consumer
path. The separate milestones still to measure are first retail draw, frontend
and offline race.

## 2026-10-22 — v751 UI callback gate provenance

The v751 controlled P-code replay requested 120 host frames and completed the
host-frame loop without a runtime blocker. Across 594 calls to `0x0050CEB0`,
the state word at `parent+0x34`, callback pointer at `parent+0x48`, and gate
return were all zero. The last traced writer to the callback pointer in every
gate event was constructor `0x004EB550`, which wrote zero; the helper byte at
`parent+0x0c` remained zero from base initializer `0x0050C820`, so
`0x0050C880` returned zero and the gate skipped its wait loop. This explains
the observed state but does not prove that no registration/setter path exists
in other UI states. Retail draw translation, frontend readiness, and race
entry remain unproven. See the [v751 provenance report](../evidence/retail_frontier_20261022/process1_ui_callback_pointer_provenance_v751.md)
and its [machine-readable evidence](../evidence/retail_frontier_20261022/process1_ui_callback_pointer_provenance_v751.json).
The v752 360-frame replay extended this observation to 1,123 gate calls; the
same constructor remained the last observed writer, and no guest draw
translation appeared. A v753 360-frame targeted trace selected the nested
candidate `0x00852760` and all four D3D9 Draw/DrawUP imports; none were reached
in that bounded replay. This is not a proof of unreachability in other UI
states. See the [v753 evidence](../evidence/retail_frontier_20261022/process1_ui_gate_nested_draw_candidate_v753.md)
and [machine-readable trace](../evidence/retail_frontier_20261022/process1_ui_gate_nested_draw_candidate_v753.json).

A byte-level Process 1 analysis then established a conditional retail path from
the UI rendering method `0x00852760` through nested methods `0x00850F10`,
`0x00851730`, and `0x008521F0` to D3D9 `DrawIndexedPrimitive`. The evidence
resolves the concrete adapter vtable and traces the created device pointer
through adapter `0x0084FD60` to the underlying device's COM slot. This proves
that the original PE contains the draw path; it does not prove that the P-code
replay entered it. In the v753 run, neither `0x00852760` nor the selected
Draw* imports were observed. A v755 replay then selected forwarding adapter
`0x0084FD60` and all four Draw* imports. Its full, untruncated trace contained
zero events over 360 host frames; this remains a bounded negative observation
and does not contradict the static path or prove unreachability in another UI
state. A second v756 trace also selected all three nested methods
`0x00850F10`, `0x00851730`, and `0x008521F0`; it observed none of them, the
parent, the adapter, or the Draw* imports during its 360-frame interval. This
narrows only the observed frontier for that run. The Vulkan bridge still
reports `guest_draw_translation=false`. See the
[full static analysis](../evidence/retail_frontier_20261022/process1_nested_draw_static_00852760.md),
[v755 report](../evidence/retail_frontier_20261022/process1_drawindexed_forwarder_v755.md),
its [machine-readable trace](../evidence/retail_frontier_20261022/process1_drawindexed_forwarder_v755.json),
the [v756 report](../evidence/retail_frontier_20261022/process1_nested_draw_v756.md),
and [machine-readable trace](../evidence/retail_frontier_20261022/process1_nested_draw_v756.json).
