# Process 1 — BMW BODY0 bind-initialization frontier

## Blocker removed by this layer

`SHIFT.BMWBody0VHFBindFrameFrontier/1` freezes the dynamic transform equation:

```text
M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime
```

but deliberately leaves `M_BODY0_bind` unknown.  The nearest static task is to
prove the bind-time relationship between BMW chassis BODY index 0 and the VHF
vehicle-root frame.

The repository already has generic BODY lane/pointer-provenance tooling.  What it
did not have was a finite initialization-specific callsite worklist around:

```text
FUN_007b6900  SDF loader anchor
FUN_007b3670  0x170-byte BODY builder anchor
FUN_007b7840  verified broad pose-writer candidate
```

This block adds that worklist without promoting callgraph adjacency to semantics.

Machine-readable format:

```text
SHIFT.BMWBody0BindInitializationFrontier/1
```

Tool:

```text
tools/ghidra/build_bmw_body0_bind_initialization_frontier.py
```

No original game execution and no new runtime capture are used.

## Inputs

The tool consumes the ordinary saved Ghidra export directory and requires:

```text
binary.json
functions.jsonl
callgraph.jsonl
```

It fails closed unless the binary identity is the current retail snapshot:

```text
program = SHIFT.exe
MD5    = 705af8b420e5eb1e3834ac43d5533c6b
```

and all three static anchors are present.

Only callgraph rows with:

```text
indirect == false
```

participate in reachability or caller classification.

## What the frontier computes

### Exact direct caller set of `FUN_007b7840`

Every direct edge into the pose-writer candidate is preserved with its exact
callsite address.  Each caller is classified only as one of:

```text
builder-reachable-pose-writer-caller
loader-reachable-pose-writer-caller
unjoined-direct-pose-writer-caller
```

The labels describe graph reachability, not method semantics.

In particular:

```text
builder-reachable != bind initializer proven
```

A caller becomes useful only because it is a higher-priority target for exact
instruction/value provenance.

### Directed construction paths

The report records bounded shortest direct-call paths for:

```text
FUN_007b6900 -> FUN_007b3670
FUN_007b3670 -> FUN_007b7840
FUN_007b6900 -> FUN_007b7840
```

The default search bound is eight direct-call edges and can be changed with
`--max-depth`.

Absence of a path is retained as `reachable=false`; it is not converted into an
ownership conclusion.

### Minimal targeted instruction worklist

The output includes the union of:

- the three anchors;
- every direct caller of `FUN_007b7840`;
- every function on the selected bounded paths.

External/thunk entries are retained in metadata but excluded from the exportable
instruction target list.

All direct callsites involved in the caller set or selected paths are emitted as
a separate exact callsite list.

## Run

Given the existing static export:

```bash
python3 tools/ghidra/build_bmw_body0_bind_initialization_frontier.py \
  out/shift_ghidra_database \
  --json-out out/bmw_body0_bind_initialization_frontier.json \
  --targets-out out/bmw_body0_bind_instruction_targets.txt \
  --callsites-out out/bmw_body0_bind_callsites.txt
```

Then reuse the existing generic instruction exporter rather than introducing a
second exporter:

```bash
mapfile -t TARGETS < out/bmw_body0_bind_instruction_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/bmw_body0_bind_instructions.jsonl \
  "${TARGETS[@]}"
```

This opens the Ghidra project read-only through the existing headless export
path. It does not execute the retail game.

## Relationship to existing BODY writer tooling

The existing chain:

```text
analyze_register_relative_accesses.py
  -> build_body_writer_bridge_candidates.py
  -> join_body_writer_candidates_to_frontier.py
  -> build_body_pointer_provenance_worklist.py
  -> promote_body_writer_bridge_provenance.py
```

remains useful and is not replaced.

That chain answers questions such as:

```text
Does this instruction access a known BODY lane?
Is the syntactic base register independently proven to be BODY here?
```

The new initialization frontier answers a different prerequisite:

```text
Which exact callers/callsites can connect construction to the broad pose writer,
and therefore which functions need targeted value-provenance analysis?
```

The future bind proof should reuse `SHIFT.GhidraBodyPointerProvenance/1` semantics
where applicable instead of defining a competing BODY pointer identity format.

## Promotion requirement

This report itself can never emit `SHIFT.BMWBody0BindFrameProof/1`.

A positive bind proof still requires all of the following:

1. exact BODY index-0 pointer identity on the initialization path;
2. exact origin and basis value provenance into the persistent 0x170 BODY record;
3. proof that those values define `BODY0-local -> VHF-vehicle-root` at bind time;
4. a finite non-singular D3D row-vector affine matrix;
5. static/source-backed provenance for every promoted relationship.

If `FUN_007b7840` turns out not to own bind initialization, it is rejected as the
initializer and the proof follows the actual writer instead.

## Current fail-closed status

Until targeted instruction evidence is supplied:

```text
pose_writer_candidate_bind_role_unproven      = true
BODY0_pointer_identity_proven                 = false
origin_basis_value_provenance_proven          = false
BODY0_bind_matrix_proven                      = false
```

The frontier therefore reduces the blocker from an open-ended search over BODY
writers to a deterministic caller/callsite export set, but makes no positive
retail transform claim by itself.

## Fail-closed rules

The implementation deliberately does not claim that:

- a direct caller is an initializer;
- a shortest path is execution scheduling;
- `pos`/`ori` field names equal the persistent runtime pose layout;
- a matching BODY offset establishes object identity;
- `FUN_007b7840` is a constructor or bind method;
- absence of direct callers proves a root function;
- an indirect edge may be treated as a resolved direct edge.

If the direct caller set is empty, the report adds an explicit blocker requiring
reference/dispatch investigation rather than silently declaring the writer
unreachable.
