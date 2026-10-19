# Automated retail startup frontier (Linux)

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
  --build-runtime --validation --frames 120 --timeout 180 \
  --baseline evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log \
  --log artifacts/frontier/current.log \
  --output artifacts/frontier/current.json
~~~

The existing tools/run_shift_recompiled_entrypoint_probe.sh determines supplements and accepts additional newline-delimited paths via SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS. Additional override modules can be supplied through SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES; this supports address-specific corrections that must take precedence over the default frontier module. The full P-code module can be selected with SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE. Paths and versions must match the chosen retail corpus. The launcher validates pinned original PE SHA-256 before execution.

When `tools/retail_frontier.py run` is used without `SHIFT_ENTRYPOINT_PROBE_MESH`,
it writes a minimal synthetic triangle MGEO into a temporary directory to
initialize the host renderer. This fixture is not retail evidence and is
removed after the probe. Direct calls to the shell launcher require a valid
MGEO path in `SHIFT_ENTRYPOINT_PROBE_MESH`.

The report stores status, guest dispatch counts, unique functions, first failing import, return address, host frame-loop information (when present), and a baseline delta. Analyze an existing log **without running game assets**:

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
status. If a sampled absolute address is included in
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
