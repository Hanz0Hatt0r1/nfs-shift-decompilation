# UI state-gate evidence from Revenginstr — 2026-10-19

## Provenance

The shared `revenginstr` `GhidraFunctionPcodeFlow/1` exporter from `main`
(commit `40cff63`) exported nine functions from the analyzed retail `SHIFT.exe`
image (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`).
The result contains 351 High-P-code rows. Focused x86 instruction slices from the
same image were cross-checked with GNU `objdump` because several control-flow
edges cross Ghidra function boundaries. The file list, schema, row counts and
SHA-256 values are recorded in the [manifest](../evidence/revenginstr_ui_gate_pcode_20261019/manifest.json).

## Caller and field path

P-code for `0x0045c480` and `0x004692e0` shows these two callers obtain the pointer
from `0x00545d90`, add `0x108`, and pass that address to `0x0050ceb0`. In
`0x0045c480`, the gate result controls whether the following update/service
calls execute. In `0x004692e0`, the first gate call is conditional on the byte
at caller offset `0x46c1`; a later call at `0x0046955f` is reached only after
additional caller-state checks.

The gate passes its argument plus `0x10` to `0x0082f3c0`. That helper reads a
32-bit value at its argument plus `0x24` and returns whether it equals zero.
Combined, the gate checks the word at `gate_argument + 0x34`; because callers
pass `singleton + 0x108`, this is `singleton + 0x13c`. This identifies the
precise field path but not its live value or semantic meaning.

## Branch behavior

Instruction evidence confirms the gate behavior:

- If the `+0x34` word is nonzero, execution jumps to `0x0048fb36`. That code
  sets `EAX` to one and jumps to the shared `0x0050ceb0` epilogue, so the gate
  returns true.
- If the word is zero, the gate calls `0x0050c880`. A zero result may invoke
  the callback at the object in `gate_argument + 0x48`, through vtable offset
  `0x24c`, then returns zero. A nonzero result jumps through `0x0048fb36` and
  returns one.
- In `0x0050c880`, a zero byte at `+0x0c` returns zero. Otherwise it calls the
  virtual function at vtable offset `+4`. A zero callback result returns one;
  a nonzero result calls cleanup `0x0050c830` and transfers through
  `0x0043ce36` to `0x0050c8a3`. That path sets `ECX` to one, calls the function
  pointer stored at `0x00ac59d0`, and returns zero.

The previously observed history address `0x0050c8a9` is the zero-byte branch
inside `0x0050c880`; it returns zero. The v114 history also showed a later
`0x00833670` entry, but that bounded history did not prove it was nested under
the gate.

## Runtime observation

An optional runtime tracepoint, enabled with `SHIFT_TRACE_UI_STATE_GATE=1`,
recorded 484 gate-subtree function events during 120 host Vulkan frames. The
run rendered all 120 frames with zero Vulkan validation errors. It observed 121
gate calls, all from caller `0x0054be00`; every call had the same result:

- Gate receiver `ECX` was `0x00be2500`, so the singleton candidate was
  `0x00be23f8`; the tested `singleton + 0x13c` word at `0x00be2534` was zero.
- `0x0082f3c0` returned `AL=1` for the zero word. Helper `0x0050c880` then
  observed byte `+0x0c == 0` and returned `AL=0`.
- The gate returned `EAX=0`. Its callback object pointer at `+0x48` was null,
  and the trace recorded no gate-descendant virtual callback.
- Caller `0x0054be00` executes `test eax,eax; je 0x0054bec8`; the trace's false
  result takes that branch and skips `0x0054be85` through `0x0054bec7`.

This resolves the branch taken by the recompiled run and corrects the earlier
callback inference: the later `0x00833670` history entry was not observed as a
callback beneath this gate. It may be one of the caller's later dispatches,
but that exact mapping remains unproven. The state field's semantic meaning is
also unknown, so the false branch is not yet established as the cause of the
missing frontend.

## Field-writer follow-up (v117)

The v117 probe enabled targeted guest-write provenance for `0x00be2534` and
captured the writer frame's entry ECX. Across the same bounded 120-frame run,
all 121 gate calls reported the same last write: function `0x0062fde0`, entry
ECX `0x00be2510`, a four-byte zero write at `0x00be2534`. This address equals
both `writer ECX + 0x24` and `gate ECX + 0x34`.

The Revenginstr High-P-code export for `0x0062fde0` contains a zero `STORE` to
`this + 0x24` at `0x0062fee8` (and a separate zero store to `this + 0x28`). The
runtime ECX and write address match that exact member store. Thus the trace
identifies the writer and subobject offset, rather than merely correlating a
function address with the word. The semantic name of the member and why this
initialization path is selected remain unknown; this still does not establish
that the gate's false branch causes the missing frontend. The v117 run rendered
120 host Vulkan frames with zero validation errors and observed no frontend-
ready state or retail D3D9 draw.

The [v117 machine-readable trace](../evidence/retail_frontier_20261019/entrypoint_probe_v117_ui_gate_field_writer_ecx.json),
[raw runtime log](../evidence/retail_frontier_20261019/shift-probe-v117-ui-state-field-writer-ecx-120-validation.log),
[writer P-code exports and manifest](../evidence/revenginstr_ui_gate_writer_pcode_20261019/manifest.json),
and [writer instruction slice](../evidence/revenginstr_ui_gate_writer_pcode_20261019/0062fde0-instructions.txt)
preserve the join.

The machine-readable [v115 trace record](../evidence/retail_frontier_20261019/entrypoint_probe_v115_ui_gate_trace.json)
includes counts and hashes. The [captured runtime log](../evidence/retail_frontier_20261019/shift-probe-v115-ui-state-gate-trace-120-validation.log)
preserves the full trace; the [caller instruction slice](../evidence/retail_frontier_20261019/ui-gate-caller-0054be00-branch.txt)
cross-checks the branch.

## Exporter boundary and limits

The P-code export alone labels the transfer from `0x0048fb36` to `0x0050cec4`
as a call followed by a void return. The instruction slice shows that
`0x0048fb36` is actually `mov eax, 1; jmp 0x0050cec4`, where `0x0050cec4` is the
gate's shared `pop esi; ret` epilogue. Similarly, `0x0043ce36` sets `ECX` to one
and jumps into `0x0050c8a3`. These are overlapping code-entry edges; treat the
P-code function summaries as operation evidence, not as a complete account of
register setup or ABI returns across those edges.

The static and runtime evidence establishes the branch structure, caller-
relative field offset, and the path selected in this bounded recompiled run.
It does not establish why the state word remains zero or whether the selected
caller path submits a retail draw. The next probe should map the false branch's
skipped calls and subsequent caller dispatches to frontend state and retail
D3D9 submissions.

## Artifacts

- [P-code export for the gate](../evidence/revenginstr_ui_gate_pcode_20261019/0050ceb0-flow.tsv)
- [P-code exports for callers and helpers](../evidence/revenginstr_ui_gate_pcode_20261019/)
- [Instruction slices used to resolve cross-boundary control flow](../evidence/revenginstr_ui_gate_pcode_20261019/ui_gate_instruction_slices.txt)
- [Machine-readable provenance and checksums](../evidence/revenginstr_ui_gate_pcode_20261019/manifest.json)
- [v115 runtime trace record](../evidence/retail_frontier_20261019/entrypoint_probe_v115_ui_gate_trace.json)
- [v115 runtime log](../evidence/retail_frontier_20261019/shift-probe-v115-ui-state-gate-trace-120-validation.log)
- [Caller `0x0054be00` branch instructions](../evidence/retail_frontier_20261019/ui-gate-caller-0054be00-branch.txt)
- [v117 runtime trace with writer ECX](../evidence/retail_frontier_20261019/entrypoint_probe_v117_ui_gate_field_writer_ecx.json)
- [v117 runtime log](../evidence/retail_frontier_20261019/shift-probe-v117-ui-state-field-writer-ecx-120-validation.log)
- [v117 writer P-code exports and manifest](../evidence/revenginstr_ui_gate_writer_pcode_20261019/manifest.json)
