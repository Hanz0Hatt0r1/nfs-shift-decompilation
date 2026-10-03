# Process B — BODY pointer provenance worklist

The persistent BODY writer search now has three distinct static evidence layers:

```text
p-code register-relative accesses
  -> BODY writer bridge candidates
  -> proven-callgraph frontier context
  -> instruction-level BODY pointer provenance
```

The first three layers identify *where to look*. They still do not prove that the
syntactic base register at a candidate instruction is a BODY pointer.

`tools/ghidra/build_body_pointer_provenance_worklist.py` turns those first three
layers into a finite audit queue. It joins each bridge candidate to its exact
frontier-context row using:

```text
(function address, base register, bridge kind)
```

and then emits one unresolved pointer-provenance task for every unique
participating p-code-backed read/write instruction.

## Why the worklist is instruction-scoped

A register may carry BODY at one point in a function and a different pointer at
another point. A function-wide `ECX == BODY` or `ESI == BODY` assumption is not
accepted.

Every generated task therefore starts with a single-instruction range:

```json
{
  "function": "0x00700000",
  "base_register": "ESI",
  "instruction_start": "0x00700020",
  "instruction_end": "0x00700020",
  "required_object_identity": "BODY",
  "status": "unresolved"
}
```

Adjacent tasks may only be widened into a range after register dataflow proves
that the pointer identity remains stable through that range.

The output format is:

```text
SHIFT.BodyPointerProvenanceWorklist/1
```

It preserves callgraph context such as proven-slice/root relation, shortest
frontier depth, connected subsystems, adjacent proven-slice functions,
slice callers, multi-anchor status and unresolved indirect calls. These fields
help choose the next ABI/dataflow proof, but none of them are pointer proof.

## Offline command chain

No game execution is involved.

```bash
cd /home/pes/nfs-shift-decompilation

git switch main
git pull --ff-only

python3 tools/ghidra/build_proven_callgraph_frontier.py \
  out/shift_ghidra_database \
  --subsystem physics \
  --subsystem vehicle \
  --max-depth 2 \
  --json-out out/physics_vehicle_callgraph_frontier.json \
  --targets-out out/physics_vehicle_instruction_targets.txt

mapfile -t TARGETS < out/physics_vehicle_instruction_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/physics_vehicle_frontier_instructions.jsonl \
  "${TARGETS[@]}"

python3 tools/ghidra/analyze_register_relative_accesses.py \
  out/physics_vehicle_frontier_instructions.jsonl \
  --json-out out/physics_vehicle_register_relative_accesses.json

python3 tools/ghidra/build_body_writer_bridge_candidates.py \
  out/physics_vehicle_register_relative_accesses.json \
  --json-out out/body_writer_bridge_candidates.json

python3 tools/ghidra/join_body_writer_candidates_to_frontier.py \
  out/body_writer_bridge_candidates.json \
  --frontier out/physics_vehicle_callgraph_frontier.json \
  --json-out out/body_writer_bridge_frontier_join.json

python3 tools/ghidra/build_body_pointer_provenance_worklist.py \
  out/body_writer_bridge_candidates.json \
  --frontier-join out/body_writer_bridge_frontier_join.json \
  --json-out out/body_pointer_provenance_worklist.json \
  --targets-out out/body_pointer_provenance_targets.txt \
  --fail-on-unmatched
```

The resulting `body_pointer_provenance_targets.txt` is the minimal function set
that needs detailed caller/ABI/register-dataflow analysis. The JSON worklist
contains the exact instructions that need BODY identity proof.

Once those proofs exist, encode them as
`SHIFT.GhidraBodyPointerProvenance/1` and pass them through:

```bash
python3 tools/ghidra/promote_body_writer_bridge_provenance.py \
  out/body_writer_bridge_candidates.json \
  evidence/body_pointer_provenance.json \
  --json-out out/body_writer_bridge_provenance.json \
  --require-body-proven-candidate
```

## Evidence boundary

A completed worklist alone does not prove persistence or integration. The
remaining gates after BODY identity are:

1. prove the numerical state transition for the candidate;
2. prove update ordering relative to `FUN_007b4110`, both `FUN_0076d100` passes,
   and the next-frame readers;
3. prove that the mutated BODY object is the persistent vehicle/wheel BODY that
   survives into the next simulation tick;
4. only then mark the native pose/motion handoff ready.

Until those gates close, no guessed position or orientation integrator is
admitted to native runtime.
