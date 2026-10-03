# Phase 649 — native playable vertical-slice launch contract

The native Linux runtime already accepts the renderer, camera, input and
provider-absent physics boundaries needed for a first integrated vertical slice,
but until this phase those inputs had to be assembled as a long list of
independent command-line options. That made it easy to start a run with one
missing or structurally incompatible evidence artifact.

Phase 649 adds a fail-closed orchestration layer without assigning any new
retail semantics.

## New runner

`tools/run_native_vertical_slice.py` consumes:

```text
SHIFT.NativeVerticalSliceProfile/1
```

and emits:

```text
SHIFT.NativeVerticalSliceLaunchPlan/1
```

The runner validates the existing native boundaries before executing
`native_runtime/build/shift_runtime`:

- prepared `SHIFT.NativeSceneVulkanSet/1` plus ready
  `SHIFT.NativeSceneVulkanSetPrepare/1`;
- ready `SHIFT.NativeCameraStateBridge/1`;
- `SHIFT.BMWM3VehiclePhysicsResourceManifest/1`;
- ready `SHIFT.NativePhysicsParticipantRuntimeEvidence/1` with the independent
  registry/selector identity join and concrete participant instance already
  proven;
- `SBFR` / `SHIFT.NativeBuiltinSolverFramePacket/1`;
- `GBCF` / `SHIFT.NativeGeneratedBodyConstraintFramePacket/1`;
- `CSRF` / `SHIFT.NativeConstraintSampleRelationFramePacket/1`;
- `CRRF` / `SHIFT.NativeConstraintRelationResetFramePacket/1`;
- `SBPS` / `SHIFT.NativePostSolveBodyProjectionPacket/1`;
- optional `SHIFT.NativeRuntimeInputScript/1`.

Binary packets are checked for their exact four-byte magic and version 1 before
the native executable is invoked. JSON contracts are checked for exact format
identity and readiness where the existing native boundary requires it.

## Profile

Example interactive profile:

```json
{
  "format": "SHIFT.NativeVerticalSliceProfile/1",
  "version": 1,
  "workspace_root": "../..",
  "scene_set": "out/native-scene-vulkan",
  "camera_state": "out/native-camera-state.json",
  "physics_manifest": "evidence/bmw_m3_vehicle_physics_manifest.json",
  "participant_boundary": "out/native_physics_participant_runtime_evidence.json",
  "solver_frame": "out/native-solver-frame/solver_frame.sbfr",
  "generated_body_constraint_frame": "out/native-generated/generated_body_constraints.gbcf",
  "constraint_sample_relation_frame": "out/native-relations/constraint_sample_relations.csrf",
  "constraint_relation_reset_frame": "out/native-reset/constraint_relation_reset.crrf",
  "post_solve_projection": "out/native-post-solve/post_solve.sbps",
  "persist_post_solve_body_state": true,
  "frames": 36000
}
```

`workspace_root` is resolved relative to the profile. Every referenced artifact
must remain inside that workspace root; absolute paths and path traversal beyond
it are rejected.

For deterministic CI/replay, add:

```json
"input_script": "out/native_input.script"
```

When an input script is present, `frames` must exactly match its contiguous
fixed-step row count, preserving the existing native runtime contract.

## Usage

Validate without launching:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json \
  --dry-run \
  --json-out out/vertical_slice/launch_plan.json
```

Launch:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json
```

Vulkan validation can be forwarded explicitly with `--validation`.

## Evidence boundary

A ready launch plan proves only that the already-implemented scene, camera,
participant, provider-absent solver, constraint refresh/reset and post-solve
BODY-accumulator boundaries are present together and can be passed to the
native runtime in one deterministic invocation.

It deliberately does **not** claim:

- persistent vehicle transform or velocity integration;
- provider-present dispatch;
- retail camera scheduling/controller semantics;
- retail game-loop/state-machine behavior;
- full gameplay readiness.

Those remain the next integration gates toward the first drivable Linux vertical
slice. The launch contract exists so future work can close those gates against a
single reproducible runtime profile rather than a manually assembled command.
