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
120 guest-requested full color/depth/stencil clears and 120 Vulkan swapchain
presents in a 120-frame probe, with one Present request still pending and no
guest draw translation. This proves the bounded clear/queue-present path only;
it does not prove retail rendering or frontend readiness.

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

Startup frontier metrics cannot stand in for gameplay. v194 establishes the
bounded retail-requested Vulkan clear and queue-present milestone. The separate
milestones still to measure are first retail draw, frontend and offline race.
