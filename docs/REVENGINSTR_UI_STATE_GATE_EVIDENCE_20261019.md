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
inside `0x0050c880`; it returns zero. A later `0x00833670` entry is consistent
with the gate's optional callback, but the history does not capture its object
pointer, callback target or return value.

## Exporter boundary and limits

The P-code export alone labels the transfer from `0x0048fb36` to `0x0050cec4`
as a call followed by a void return. The instruction slice shows that
`0x0048fb36` is actually `mov eax, 1; jmp 0x0050cec4`, where `0x0050cec4` is the
gate's shared `pop esi; ret` epilogue. Similarly, `0x0043ce36` sets `ECX` to one
and jumps into `0x0050c8a3`. These are overlapping code-entry edges; treat the
P-code function summaries as operation evidence, not as a complete account of
register setup or ABI returns across those edges.

This static evidence establishes the branch structure and caller-relative
field offset. It does not establish which branch the recompiled Linux run
currently takes, the live values at `+0x13c`, `+0x0c` or `+0x48`, or whether the
selected UI path submits a retail draw. The next useful runtime probe should
record the gate argument, those field values, callback return values, gate
return `EAX`, caller address and subsequent UI/draw calls.

## Artifacts

- [P-code export for the gate](../evidence/revenginstr_ui_gate_pcode_20261019/0050ceb0-flow.tsv)
- [P-code exports for callers and helpers](../evidence/revenginstr_ui_gate_pcode_20261019/)
- [Instruction slices used to resolve cross-boundary control flow](../evidence/revenginstr_ui_gate_pcode_20261019/ui_gate_instruction_slices.txt)
- [Machine-readable provenance and checksums](../evidence/revenginstr_ui_gate_pcode_20261019/manifest.json)
