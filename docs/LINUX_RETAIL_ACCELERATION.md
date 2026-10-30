# Faster Linux retail frontier

This path covers Ghidra/P-code audits, focused local preflights, a
capture-bounded D3D9 backend plan, and deferring noncritical renderer work.
It does **not** introduce parallel workstreams, platform shortcuts, or
claims of original-game playability.

## Verified instruction completeness gate

The 2026-10-20 evidence records the return block for FUN_0050f010 at
0x0050f478..0x0050f481. Those five original PE32 instructions are missing
from the frozen 2026-10-17 export. Lowerable function counts therefore
cannot be treated as proof of complete CFG/function coverage.

The runtime follow-up v811 resolves this specific execution gap when the
verified v659 module manifest is loaded: its 249-instruction
`rvi_0050f010` override includes the exact epilogue and the live retail P-code
trace observed EAX=1, preserved ESI/EDI/EBP, and ESP advancing by the single
return address. The focused full-function export also passes the verified-byte
audit against the pinned PE. See
[`process1_cinit_register_stack_v811.md`](../evidence/retail_frontier_20261022/process1_cinit_register_stack_v811.md).
The old frozen monolithic export still fails the gate; that is an export
completeness limitation, not a reproduced v659 runtime blocker. The replay
does not establish full behavioral parity or game readiness.

When replacing the frozen export with a canonical monolithic corpus, correct
the function body in Ghidra and re-export it, then run the streaming audit
before rebuilding all 41,538 functions. The runtime override above does not
rewrite or certify the frozen base corpus:

```bash
python3 tools/ghidra/audit_pcode_corpus.py \
  --corpus /path/to/corrected-functions.jsonl.gz \
  --requirements evidence/pcode_verified_terminators_20261020.json \
  --pe /path/to/SHIFT.exe \
  --expected-pe-sha256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1 \
  --output artifacts/frontier/pcode-audit.json
```

The check fails for missing/mismatched verified bytes, overlapping
instructions, incorrect instruction counts or missing required functions.
A function with no observed return is only a **warning**, since tail
calls and nonreturning functions exist. The original frozen corpus is
expected to **fail** the new verified requirement. Do not synthesize a RET
or blindly extend a body across unrelated code. Passing this audit alone
does not prove that all function CFGs or game semantics are correct.

## Reuse incremental builds and preflight CTests

```bash
bash tools/build_shift_runtime_cached.sh --build-dir native_runtime/build --jobs 8
ctest --test-dir native_runtime/build --output-on-failure \
  -R '^shift_runtime_recompiled_pcode_module$'
```

The existing cached build helper uses Ninja and ccache/sccache when available
and does not rebuild the multi-gigabyte corpus.

To reject known-bad exports *before* an expensive retail replay, opt in to
the new startup preflights:

```bash
python3 tools/retail_frontier.py run \
  --runtime native_runtime/build/shift_runtime \
  --artifacts /path/to/shift-startup-artifacts \
  --build-dir native_runtime/build \
  --pe /path/to/SHIFT.exe \
  --game-data '/path/to/Need For Speed.Shift.v 1.02' \
  --module-manifest evidence/retail_frontier_20261019/entrypoint_probe_v215_supplement_replay.json \
  --preflight-corpus /path/to/corrected-functions.jsonl.gz \
  --preflight-ctest --validation --frames 120 --timeout 180 \
  --log artifacts/frontier/current.log \
  --output artifacts/frontier/current.json
```

The corpus gate runs before the build and probe; the focused guest P-code
CTest runs before the probe (after an optional cached runtime build).
Failing either stops the launch. On success the report records the preflight
results and writes an adjacent P-code audit JSON.

**Limit:** the native CTest checks the callback/module path, not retail
FUN_0050f010 directly. Register and stack recovery must be demonstrated
by a new retail probe with observed ESI/EBP/ESP restoration and __cinit
continuing to its later initializer callbacks.

## A SHIFT-only D3D9 → Vulkan scope

Build an inventory directly from the retained original-game capture audit,
without shipping raw game resources:

```bash
python3 tools/d3d9_capture_scope.py \
  --audit evidence/retail_frontier_20261018/d3d9_race_window_capture.json \
  --output artifacts/frontier/d3d9-usage.json
```

On the retail host, add --capture /path/to/capture.jsonl to verify that raw
event counts match the audit and enumerate actually used render/sampler
state IDs. The output never stores resource payloads or pointer identities.

Prioritize original captured device calls: vertex/index buffers, streams,
declarations, shaders and constants, textures and samplers, render/depth
state, and first DrawIndexedPrimitive submission. Complete equivalent
framebuffer output and original asset provenance must follow. Unobserved
D3D9 API functions are out of scope until the retail game demonstrates a
need. The new inventory **does not itself translate guest draw calls**.

## Deferred work

Until a real original SHIFT draw reaches Vulkan: do not rewrite the renderer,
add a new lighting model, introduce normal-map enhancements, optimize
uncaptured pipelines or resume the retired independent playable slice.
Keep the common renderer within Vulkan 1.1 requirements and portable to
ARM64/Android rather than taking Linux-only shortcuts.
