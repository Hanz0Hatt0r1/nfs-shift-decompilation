# Process 1 — BMW BODY0 bind callsite register provenance

## Playable-slice blocker reduced

`SHIFT.BMWBody0BindInitializationFrontier/1` narrows the missing BODY0 bind
matrix to exact direct callers/callsites around the broad pose-writer candidate
`FUN_007b7840`.  The next static prerequisite is to stop treating source-level
parameter names or lexical register positions as proof and instead recover the
physical values reaching each exact callsite.

This layer adds that prerequisite without claiming a bind initializer, BODY0
pointer identity, stack-argument semantics, origin/basis semantics, or a bind
matrix.

Machine-readable format:

```text
SHIFT.BMWBody0BindCallsiteRegisterProvenance/1
```

Tool:

```text
tools/ghidra/analyze_bmw_body0_bind_callsite_register_provenance.py
```

No original game execution and no new runtime capture are used.

## Inputs

The analyzer consumes:

```text
SHIFT.BMWBody0BindInitializationFrontier/1
SHIFT.GhidraFunctionInstructions/2 JSONL
```

The instruction export must contain every direct caller function listed by the
frontier.  Missing callers, duplicate rows, drifted callsites, non-CALL rows,
wrong direct targets, malformed instruction order, and unreachable callsites are
fail-closed errors.

The intended retail sequence is:

```bash
python3 tools/ghidra/build_bmw_body0_bind_initialization_frontier.py \
  out/shift_ghidra_database \
  --json-out out/bmw_body0_bind_initialization_frontier.json \
  --targets-out out/bmw_body0_bind_instruction_targets.txt \
  --callsites-out out/bmw_body0_bind_callsites.txt

mapfile -t TARGETS < out/bmw_body0_bind_instruction_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/bmw_body0_bind_instructions.jsonl \
  "${TARGETS[@]}"

python3 tools/ghidra/analyze_bmw_body0_bind_callsite_register_provenance.py \
  out/bmw_body0_bind_initialization_frontier.json \
  out/bmw_body0_bind_instructions.jsonl \
  --json-out out/bmw_body0_bind_callsite_register_provenance.json
```

The first two steps are existing generic exporters.  This phase adds only the
consumer of their static evidence.

## All-path register provenance

The analyzer reuses the finite IA-32 register provenance engine already used by
the `FUN_00765470` BODY-owner receiver proof.  For each exact `FUN_007b7840`
callsite it computes the fixed-point incoming state over the caller CFG and
records every tracked physical register as an origin set.

Examples of retained origins include:

```text
entry:ECX
memory:dword ptr [eax + 0x10]
unknown:ECX@...:call-clobber
```

Caller-saved clobbers remain unknown unless a later instruction restores a
proven value.  Multiple control-flow origins are merged rather than selecting a
convenient predecessor.

For each callsite the report also records:

- exact aliases of entry registers when a register has one unique entry origin;
- unresolved/ambiguous register names;
- reachable and total instruction counts;
- fixed-point iteration count;
- a small lexical pre-call window for discovery only.

The lexical window is explicitly marked `lexical_window_is_path_proof=false`.

## What this closes

Given a complete targeted instruction export, this layer can close exactly:

```text
pose_writer_callsite_register_provenance_ready = true
```

That means the physical register values reaching every frontier callsite are
represented by all-path provenance instead of a lexical guess.

It does **not** mean any physical register has been assigned a retail semantic
role.

## Remaining blockers

The report deliberately keeps these blockers separate:

```text
pose-writer-physical-ABI-semantic-binding-unproven
BODY0-pointer-at-bind-callsite-unproven
bind-origin-basis-value-provenance-unproven
stack-argument-value-provenance-unmodeled
```

The next proof must bind the recovered physical values to source-backed
`FUN_007b7840` parameter semantics.  If a relevant parameter is stack-passed,
exact stack-value provenance must be added; the lexical window is not a
substitute.

Only after the physical ABI is established can a value be joined to exact BMW
BODY index 0 pointer provenance and then to bind origin/basis value provenance.

## Relationship to the vehicle world-transform chain

Process 1 #1199 and Process 2 Phases 704–706 already provide the exact dynamic
composition and persistent runtime transport:

```text
M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime
```

This analyzer does not change that equation.  It advances the one still-missing
static witness, `M_BODY0_bind`, by making its candidate initialization callsites
value-provenance-ready.

Until a later contract emits a positive source-backed
`SHIFT.BMWBody0BindFrameProof/1`:

```text
BODY0_pointer_identity_proven = false
BODY0_bind_matrix_proven      = false
BODY0_bind_frame_proof_ready  = false
```

## Current retail status

The repository currently does not commit the targeted instruction JSONL needed
to run this analysis over the retail caller set.  Therefore synthetic regression
fixtures validate the analyzer itself, but they are not retail evidence.

No positive bind claim is emitted from the absence of that artifact.

## Fail-closed policy

This layer never infers that:

- `FUN_007b7840` is the bind initializer merely because it is on a construction path;
- ECX is a BODY pointer merely because the function is `__thiscall`;
- a physical register position names a source parameter;
- a lexical instruction window proves path-wide value provenance;
- a memory-origin expression identifies BODY0 without an independent pointer join;
- a source field name proves the final D3D bind matrix;
- stack arguments may be ignored when the ABI requires them.

The result is reusable static infrastructure for the nearest playable-slice
blocker, not a synthetic completion of that blocker.
