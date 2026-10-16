# Process 1B — Ghidra acquisition bridge for the helper-setter frontier

## Why this exists

`SHIFT.P1B.Manager374HelperSetterRetailFrontier/1` is the canonical merged runner for the three bounded decoded-image helper-mediated `manager+0x374` transports. Its primary path accepts the pinned raw PC retail 1.02 `SHIFT.exe` and disassembles it once with `objdump`.

The analyzed Ghidra project for the same PC retail executable is also available, while raw executable bytes may not always be transferable into the environment doing the integration work. This bridge lets that already-analyzed project produce the exact compact instruction fields consumed by the merged probes without adding another semantic transport class.

Ghidra acquisition is corroborating static evidence. It does not silently replace the raw-PE execution path or promote global P1.3 gates.

## Components

```text
revenginstr/ghidra/ExportGhidraCompactInstructionStream.java
tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh
tools/ghidra/adapt_revenginstr_compact_instruction_stream.py
tools/ghidra/ShiftCompactInstructionStreamExporter.java
```

The local Java exporter remains a fallback when the shared generic checkout
does not contain the compact-stream runner. The compatibility wrapper adapts
only the row format tag before passing the stream to the existing bridge.

The downstream bridge is:

```text
tools/ghidra/run_p1b_manager374_helper_setter_ghidra_frontier.py
```

Contracts:

```text
REVENGINSTR.GhidraCompactInstructionStream/1
SHIFT.GhidraCompactInstructionStream/1
SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1
```

The shared exporter emits the `REVENGINSTR` tag. The adapter changes that tag
to the existing `SHIFT` contract for the domain-specific bridge.

The downstream composed frontier remains:

```text
SHIFT.P1B.Manager374HelperSetterRetailFrontier/1
```

## Pinned Ghidra program identity

The Python bridge refuses any stream whose header does not match:

```text
program        SHIFT.exe
MD5            705af8b420e5eb1e3834ac43d5533c6b
language       x86:LE:32:default
image base     0x00400000
pointer size   4
```

That MD5 is the established Ghidra identity of the same PC retail 1.02 executable whose known raw SHA-256 is:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

The bridge records the SHA-256 as a known cross-pin but explicitly emits:

```text
raw_executable_sha256_verified_in_this_run = false
```

because the Ghidra stream does not contain the original executable bytes.

## Compact whole-program export

The exporter walks `listing.getInstructions(true)` in address order. The first JSONL row is an identity header. Every remaining row contains only the instruction data needed by the merged P1B analyzers:

```text
address
mnemonic
operand strings
flow type
flow target addresses
```

If the output filename ends with `.gz`, the exporter uses gzip. This is recommended for the whole-program stream.

The exporter intentionally omits p-code, references, raw instruction bytes and function metadata because #2011 does not consume them; keeping the row format compact materially reduces a multi-million-instruction export.

## Run the Ghidra acquisition and bridge

Use the existing analyzed project. The compatibility wrapper selects the
shared generic exporter when available, retains the local exporter as a
fallback, and publishes the bridge output only after its fail-closed guards:

```bash
GHIDRA_HOME=/path/to/ghidra \
  bash tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh \
  /path/to/project-dir PROJECT_NAME SHIFT.exe \
  /tmp/p1b-helper-setter-ghidra
```

The exact project directory/name should be the already-analyzed project containing the pinned `SHIFT.exe`; this step does not re-import or re-analyze it.

## Run the P1B frontier from the export

```bash
python3 tools/ghidra/run_p1b_manager374_helper_setter_ghidra_frontier.py \
  /tmp/shift-compact-instructions.jsonl.gz \
  --out-dir /tmp/p1b-helper-setter-ghidra
```

Outputs:

```text
ghidra_acquisition.json
frontier.json
direct_call_argument.json
helper_return_immediate.json
helper_return_stack.json
```

The bridge computes two hashes:

- `file_sha256`: streaming SHA-256 of the exported file itself;
- `canonical_instruction_stream_sha256`: SHA-256 over normalized `address|mnemonic|operands` rows, independent of plain-vs-gzip storage.

This makes separate exports directly comparable even when container compression bytes differ.

## Direct call normalization

Ghidra commonly renders a direct call operand as a symbol such as `FUN_00401000`, while the raw `objdump` probes consume a numeric direct target. For a CALL with exactly one non-indirect operand and exactly one Ghidra flow target, the bridge substitutes that exact flow address.

It does **not** perform that substitution for register or memory-indirect forms such as:

```text
CALL EAX
CALL [EAX]
CALL DWORD PTR [EAX + 0x4]
```

Even if a Ghidra database happens to expose a speculative/resolved flow for such an instruction, the operand remains indirect for this proof. This preserves the fail-closed boundary of the merged P1B probes.

## Authority rewrite

The merged #2011 composer is reused unchanged for candidate mechanics, but its raw-retail acquisition flags are rewritten in the Ghidra wrapper:

```text
retail_helper_setter_probe_bundle_execution_complete = false
retail_helper_setter_candidate_frontier_composed = false

ghidra_helper_setter_probe_bundle_execution_complete = true
ghidra_helper_setter_candidate_frontier_composed = true
```

All semantic/final gates remain false, including:

```text
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Tests

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_ghidra_helper_setter_acquisition.py
```

Regressions cover:

- all three #2011 transport classes through Ghidra-style symbol operands and flow targets;
- plain and gzip streams producing the same canonical instruction digest;
- misleading flow metadata on a memory-indirect CALL remaining indirect;
- wrong executable MD5 rejection;
- duplicate/non-monotonic instruction address rejection;
- direct symbol / register / memory-call normalization rules;
- exporter identity fields, whole-program iteration, flow export and gzip support;
- fail-closed raw-retail and final semantic gates.

## Next step

Run this exporter/bridge against the pinned analyzed PC retail project. If a Ghidra frontier is obtained, preserve it as corroborating acquisition evidence and compare candidate/open-boundary sets against a raw `SHIFT.exe` #2011 bundle run when raw bytes are available. Only fully adjudicated authoritative candidates may change the broader helper/non-vtable setter or final P1.3 identity gates.
