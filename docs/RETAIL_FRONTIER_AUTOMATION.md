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
