# Process B — BODY writer bridge pointer-provenance gate

The BODY writer bridge candidate classifier in
`tools/ghidra/build_body_writer_bridge_candidates.py` deliberately stops before
assigning object identity. A same-function/same-register p-code access pattern is
not enough to call a function a BODY writer.

This step adds the next evidence gate:

```text
SHIFT.BodyWriterBridgeCandidates/1
        +
SHIFT.GhidraBodyPointerProvenance/1
        |
        v
SHIFT.BodyWriterBridgeProvenance/1
```

`tools/ghidra/promote_body_writer_bridge_provenance.py` promotes a bridge
candidate only when the candidate's exact base register is independently proven
to hold a BODY pointer at **every** participating read/write instruction.

## Pointer provenance manifest

The provenance file is intentionally explicit and instruction-range scoped:

```json
{
  "format": "SHIFT.GhidraBodyPointerProvenance/1",
  "entries": [
    {
      "function": "0x00700000",
      "instruction_start": "0x00700010",
      "instruction_end": "0x00700030",
      "base_register": "ESI",
      "object_identity": "BODY",
      "evidence_level": "callsite-plus-dataflow",
      "sources": [
        "caller ABI proof",
        "register dataflow through the selected instruction range"
      ]
    }
  ]
}
```

A manifest entry must provide:

- exact function address;
- inclusive instruction range;
- exact base register;
- explicit object identity;
- evidence level;
- at least one source reference.

No inference is made from `ECX`, `__thiscall`, a function name, or a matching
offset alone.

## Promotion rule

For one `accumulator-to-motion` or `motion-to-pose` candidate, collect every
instruction from `read_evidence` and `write_evidence`. The candidate is marked
`body_lane_access_pattern_proven=true` only if every participating instruction
is covered by at least one matching provenance record whose
`object_identity` is exactly `BODY`.

Partial coverage fails closed. Provenance for `wheel-BODY-compatible`, vehicle,
wheel, spindle, axle, or any other alias is retained in the report but does not
promote the candidate.

For a combined bridge group, both stages must independently satisfy the BODY
pointer gate before `combined_body_lane_access_pattern_proven=true` is emitted.

## Evidence boundary

This promotion proves only:

1. the p-code-backed read/write lane pattern already established by
   `SHIFT.BodyWriterBridgeCandidates/1`;
2. the exact syntactic base register carries a BODY pointer at all participating
   instructions according to independent range-scoped evidence.

It still does **not** prove:

- that the access pattern is the frame-to-frame persistent integrator;
- timestep semantics;
- accumulator-to-velocity numerical equations;
- velocity-to-position integration;
- orientation integration;
- ordering relative to both `FUN_0076d100` passes or `FUN_007b4110`;
- next-tick persistence.

For that reason every promoted row retains:

```text
persistent_writer_proven = false
integration_semantics_proven = false
frame_ordering_proven = false
native_pose_port_ready = false
```

## Offline pipeline

No original game execution is required.

```bash
cd /home/pes/nfs-shift-decompilation

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

python3 tools/ghidra/promote_body_writer_bridge_provenance.py \
  out/body_writer_bridge_candidates.json \
  evidence/body_pointer_provenance.json \
  --json-out out/body_writer_bridge_provenance.json \
  --require-body-proven-candidate
```

The remaining Process B task after this gate is to derive real
`SHIFT.GhidraBodyPointerProvenance/1` entries from caller ABI/register dataflow
for the finite candidate set, then prove scheduler ordering before any native
pose integration is admitted.
