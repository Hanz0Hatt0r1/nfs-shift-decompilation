# Phase 680 — `FUN_007afdd0` exact static freeze

Phase 679 closes the native raw-state chain from solver/post-solve feedback into
`FUN_007b2270` / `FUN_007bab70` persistent BODY integration. The remaining
arithmetic hole inside that chain is the basis writer:

```text
cross_vector * dt
  -> FUN_007afdd0(BODY + 0xd4, rotation_increment)
  -> updated 3x3 f32 basis
```

The call boundary is already source/static-backed, but the repository does not
yet contain a targeted instruction/p-code export for `FUN_007afdd0`. Phase 680
therefore freezes the evidence pipeline instead of substituting a guessed
Rodrigues/quaternion implementation.

## What changed

### Structured p-code varnodes

`tools/ghidra/ShiftFunctionInstructionExporter.java` still emits the compatible
format:

```text
SHIFT.GhidraFunctionInstructions/2
```

Each p-code operation now additionally carries structured `output` and `inputs`
varnodes with:

- address space;
- offset;
- byte size;
- constant/register/unique classification;
- the original Ghidra varnode text.

Existing v2 consumers continue to use `opcode` and `text`; the new fields are
additive. The extra structure is required to reconstruct x87/SSE data flow
without scraping display strings.

### Targeted runner

The new runner:

```text
tools/ghidra/run_fun_007afdd0_basis_rotation.sh
```

exports only `FUN_007afdd0` from an already analyzed Ghidra project and creates:

```text
fun_007afdd0_instructions.jsonl
fun_007afdd0_basis_rotation_static.json
```

It does not run `SHIFT.exe`.

Example:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_fun_007afdd0_basis_rotation.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/fun_007afdd0_basis_rotation
```

### Fail-closed analyzer

`tools/ghidra/analyze_fun_007afdd0_basis_rotation.py` accepts exactly one
`SHIFT.GhidraFunctionInstructions/2` row at `0x007afdd0` and freezes:

- complete instruction order;
- exact instruction bytes and aggregate SHA-256;
- complete raw p-code order;
- structured p-code varnodes when present;
- x87 instruction order;
- scalar-SSE instruction order;
- x87 control-word instructions;
- explicit memory operand widths;
- p-code LOAD/STORE classification;
- calls and call references;
- conditional branches and flow targets.

Output format:

```text
SHIFT.Fun007afdd0BasisRotationStatic/1
```

The report distinguishes two states:

```text
instruction_freeze_ready
native_port_ready
```

A valid targeted export can make `instruction_freeze_ready=true`. It does not
make the native port ready merely because the instruction bytes are known.

## Why the analyzer is deliberately conservative

A standard rotation formula is not evidence-equivalent to retail x86. The exact
native replacement must preserve every material precision/order boundary,
including any of the following that appear in the real function:

- x87 stack evaluation order;
- f32 stores/reloads that force rounding between operations;
- x87 control-word precision/rounding state;
- scalar-SSE/MXCSR rounding state;
- conditional small-angle or normalization paths;
- helper calls and their side effects;
- basis/increment pointer aliasing;
- exact read/write ordering of the nine f32 basis elements.

Phase 680 reports blockers for these conditions instead of assigning unproved
semantics.

Typical blocker IDs include:

```text
x87-stack-dataflow-unreconstructed
ambient-x87-control-word-unfrozen
x87-control-word-provenance-unresolved
mxcsr-rounding-state-unfrozen
callee-semantics-unfrozen
floating-control-flow-paths-unproven
memory-aliasing-and-field-identity-unresolved
unsized-memory-operands
unclassified-floating-mnemonics
structured-pcode-varnodes-missing
```

`--require-native-ready` turns any remaining blocker into a non-zero analyzer
exit code. Normal evidence collection does not use that flag, because the point
of the first real run is to enumerate the exact blockers.

## What Phase 680 does not claim

This phase does **not**:

- implement `FUN_007afdd0` in C++;
- assume Rodrigues rotation;
- assume quaternion integration;
- assume orthonormalization or normalization;
- assign physical units to the rotation increment;
- claim complete `FUN_00765470` parity;
- claim rendered-frame cadence;
- require a new runtime capture.

## Regression coverage

`tests/test_ghidra_fun_007afdd0_basis_rotation.py` uses synthetic v2 instruction
slices to verify:

- deterministic aggregate machine-code hashing;
- strict target/address and instruction-order validation;
- x87 classification;
- explicit memory-width preservation;
- structured p-code varnode completeness;
- call/branch blocker generation;
- rejection of legacy v1 exports;
- no promotion of Rodrigues/quaternion/normalization semantics.

The dedicated `native-physics-phase680` workflow also parses the shell runner
with `bash -n` and runs the Phase 680 Python regression.

## Next native gate

After the targeted runner is executed against the existing Ghidra project, the
resulting static report becomes the input to the next phase. Only after its
blockers are closed should the external basis callback used by Phases 674, 676,
677 and 679 be replaced by an exact native `FUN_007afdd0` implementation.

Until then the callback remains the correct fail-closed boundary.
