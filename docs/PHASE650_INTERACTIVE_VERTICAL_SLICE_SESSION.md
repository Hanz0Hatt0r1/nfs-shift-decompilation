# Phase 650 — interactive native vertical-slice session

Phase 649 established one fail-closed launch profile for the existing native
scene, camera, participant and provider-absent physics boundaries. The profile
was still bounded by a short explicit frame count, which is appropriate for CI
but inconvenient for the first human-driven Linux vertical slice.

Phase 650 adds an explicit interactive policy to the same profile without
changing native fixed-step timing, input mapping, rendering, physics or game
semantics.

## Profile switch

Interactive keyboard mode is selected with:

```json
"interactive": true
```

When enabled:

- `input_script` is forbidden because deterministic replay and human-driven
  keyboard control are intentionally separate modes;
- `frames` is forbidden to avoid conflicting termination policies;
- the launch plan passes `--frames 2147483647` to the existing runtime;
- the existing XCB quit/window-close path remains able to terminate the loop
  before that sentinel is reached;
- the launch plan reports `mode = "interactive-keyboard"` and
  `frame_limit_policy = "int32-max-with-window-quit"`.

The sentinel is an orchestration compatibility mechanism for the current
bounded native loop. It is not presented as the recovered retail game loop.
At 60 fixed steps per second the sentinel is effectively unreachable during a
normal interactive session, while preserving the current native executable ABI.

## Example

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
  "interactive": true
}
```

Launch remains:

```bash
python3 tools/run_native_vertical_slice.py out/vertical_slice/profile.json
```

## Evidence boundary

This phase improves session lifetime only. It does not claim that the player can
already drive an authentic retail vehicle. In particular it still leaves:

- persistent vehicle transform/velocity integration unresolved;
- provider-present dispatch unresolved;
- retail camera controller/view attachment unresolved;
- retail state-machine/game-loop behavior unresolved.

The value of Phase 650 is that those remaining gates can now be exercised in a
long-running human-controlled native session instead of only short CI-sized
runs.
