# BODY writer bridge candidates from p-code access evidence

`tools/ghidra/build_body_writer_bridge_candidates.py` narrows the two unresolved
Process B state-evolution arrows without inventing a chassis integrator.

Input format:

```text
SHIFT.GhidraRegisterRelativeAccesses/1
```

Output format:

```text
SHIFT.BodyWriterBridgeCandidates/1
```

The input already requires `SHIFT.GhidraFunctionInstructions/2` p-code and only
admits register-relative operands whose machine instruction has a Ghidra `LOAD`
and/or `STORE`. The bridge classifier adds a second, deliberately conservative
condition: participating reads and writes must occur in the same function and
use the same syntactic x86 base register.

## Existing BODY lane contract

The classifier reuses only lane offsets already frozen by
`SHIFT.BodyPersistentStateABI/1`:

- accumulator A: `+0x48/+0x50/+0x58`;
- accumulator B: `+0x60/+0x68/+0x70`;
- cross vector: `+0x18/+0x20/+0x28`;
- motion triplet: `+0x78/+0x80/+0x88`;
- origin: `+0x00/+0x08/+0x10`;
- basis: `+0xd4..+0xf4` at 4-byte spacing.

No additional field name or offset is introduced by this layer.

## Candidate classes

### `accumulator-to-motion`

A function/base-register group must contain both:

1. a p-code-backed read (or read-write) from `+0x48..+0x70`; and
2. a p-code-backed write (or read-write) to `+0x18..+0x28` or
   `+0x78..+0x88`.

This is a candidate for the currently missing accumulator-to-motion bridge. It
is **not** promoted to a BODY writer until the base register is independently
proven to carry the same BODY object.

### `motion-to-pose`

A function/base-register group must contain both:

1. a p-code-backed read (or read-write) from `+0x18..+0x28` or
   `+0x78..+0x88`; and
2. a p-code-backed write (or read-write) to origin `+0x00/+0x08/+0x10`
   or basis `+0xd4..+0xf4`.

This is a candidate for the currently missing pose-integration boundary. It does
not prove Euler/quaternion/matrix integration semantics or timestep ordering.

### Combined bridge

A combined bridge is reported only when **both** candidate classes occur in the
same function **and the same base register**. Two different registers in one
function are never merged into one object candidate.

## Suggested Process B flow

Build a proven physics/vehicle callgraph frontier and export targeted p-code:

```bash
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
```

`--fail-on-empty` may be used when a CI/manual investigation explicitly expects
at least one candidate. `--fail-on-malformed` rejects malformed access rows while
still keeping them visible in the normal report.

## Evidence boundary

A candidate proves only a same-function/same-register offset-access pattern on
instructions already classified by p-code. It does **not** prove:

- that the base register is `this` or BODY;
- pointer provenance from vehicle/wheel/spindle/axle objects;
- aliasing between registers or across calls;
- that accumulator and motion lanes belong to the same runtime allocation;
- persistence between frames;
- update/scheduling order;
- timestep use;
- physical units;
- position/orientation integration semantics.

The intended next promotion step is caller/ABI pointer provenance for each
candidate, followed by exact ordering around `FUN_00770e80`, `FUN_0076d100` and
the SDF/contact frame. Until then every candidate remains `promoted=false` and
`persistent_writer_proven=false`.
