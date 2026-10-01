# SHIFT native Linux runtime

This is the first integrated offline runtime shell for the Linux build target.

## Scope

The executable is intentionally offline-only. It does not provide or depend on:

- EA services;
- DRM;
- login/profile/cloud services;
- matchmaking or online networking;
- Bink/video playback.

## Current vertical slice

```
MGEO → native IR → XCB window → Vulkan swapchain → indexed draw → frame loop
```

The renderer consumes normalized native IR. Original BFF parsing remains upstream in the existing Python importer/resource pipeline.

The runtime accepts a single MGEO mesh, a prepared `SHIFT.BMWVulkanBundle/1`, the historical BMW bundle set, or a Phase 586 prepared `SHIFT.NativeSceneVulkanSet/1` via `--scene-set`. Bundle mode validates the native-submission, SPIR-V and Vulkan-interface gates, preserves the packet vertex layout, loads semantic-aware SVGP v3 geometry (while retaining v1/v2 compatibility), loads the bundle vertex/pixel SPIR-V, uploads the `SVCP` constant buffers plus `SVTP` 2D textures and optional cube, creates descriptor sets 0/1, and submits the prepared shader/material path directly. The frame loop also exposes a fixed 60 Hz simulation boundary through `SHIFT.NativeRuntimeState/1`. Phase 599 executes the recovered CameraManager six-word snapshot plus guarded double-buffer flip/copy on that native boundary; Phase 600 can seed it from recovered camera scalar evidence. Phase 601 adds deterministic `SHIFT.NativeRuntimeInputScript/1` control snapshots that traverse the same vehicle-intent/physics-tick boundary as live keyboard input. Phase 602 additionally accepts `SHIFT.NativePhysicsParticipantBoundary/1` via `--participant-boundary`, admitting only the proven registry/selector ABI while keeping the concrete participant unresolved. Phase 603 adds the native `FUN_007b0f20` builtin sparse numerical backend as `shift_runtime_physics`; it is parity-tested separately and is not yet invoked as a complete vehicle frame. The state layer deliberately does not synthesize unknown retail force/integration semantics. `Esc` or `Q` exits the harness.

## Build

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
```

## Run

```bash
native_runtime/build/shift_runtime \
  --bundle out/example-bundle \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --camera-state out/native-camera.json \
  --frames 120
```

On CI or a headless workstation, run it through Xvfb.

## Design boundary

This target is deliberately small. Prepared neutral scene scheduling is available through `--scene-set`; retail streaming/LOD, authentic runtime-proven Silverstone inputs and unresolved renderer-owned resources remain separate gates. The current native state boundary already accepts the real BMW physics manifest and sizes the proven SDF workspace; numerical force/integration semantics remain a separate evidence-backed backend task.


## Phase 530 per-draw cull state

Prepared BMW bundles can contain `pipeline_state.json` with
`SHIFT.MaterialCullState/1`. The native runtime validates that sidecar and
selects `VK_CULL_MODE_NONE`, `VK_CULL_MODE_BACK_BIT` or
`VK_CULL_MODE_FRONT_BIT` independently for each material draw. The mapping is
source-backed by the retail BMT enum/string table and the retail D3D9 cull
lookup. Missing sidecars retain the legacy no-cull material path for old
fixtures; malformed or blocked sidecars fail closed.


## Phase 532 depth/blend state

`SHIFT.MaterialPipelineState/1` extends the per-bundle sidecar with proven
retail depth-test/write/compare and ordinary alpha-blend factors/operations.
The native runtime consumes these values independently for every prepared draw.
Enabled alpha-test and unmapped/bias state are rejected by bundle preparation
rather than approximated.


## Vulkan validation on Linux

Install `vulkan-validationlayers` (Ubuntu/Debian), then add `--validation` to
`shift_runtime`. The runtime requires `VK_LAYER_KHRONOS_validation` and
`VK_EXT_debug_utils` when requested; missing support fails startup. Validation
errors, including resource destruction errors, produce a nonzero exit status.
The final frame-loop report includes `validation_enabled` and
`validation_errors`; warnings are written to stderr without failing the run.

A software Vulkan smoke run, from the repository root:

```bash
python3 tools/run_linux_vulkan_smoke.py out/vulkan/bundle --validation
xvfb-run -a native_runtime/build/shift_runtime \
  --bundle-set out/vulkan/bundle/bundle_set \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --frames 120 --validation
```

Build `native_vulkan` first for bundle preparation. Select Mesa lavapipe using
`VK_ICD_FILENAMES` if the machine has multiple Vulkan drivers; the ICD JSON path
varies by distribution. An existing X11 display can be used without `xvfb-run`.
The generated fixture exercises indexed draws, constants, a 2D texture and a
cubemap; it is synthetic test geometry, not a playable game scene.

Command buffers and acquire semaphores follow the frame fence. Presentation
semaphores follow the acquired swapchain image so they are not reused while
presentation still owns them, as described in the
[Khronos Vulkan guide](https://docs.vulkan.org/guide/latest/swapchain_semaphore_reuse.html).
Linux CI validates both single-draw and multi-draw runs across 12 frames.


## Phase 586 neutral scene-set mode

Prepare the Phase 585 set first:

```bash
python shift_importer.py native-scene-vulkan-prepare \
  out/native-scene-vulkan \
  --validator glslangValidator
```

Then run:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --frames 120 --validation
```

This mode requires neutral child prepare/interface gates and applies each
`world_transform.svwt` before GPU upload with the Phase 584 semantic affine
rules. The BMW `--bundle-set` ABI remains supported independently.


## Phase 600 camera evidence input

The live Phase 599 CameraManager snapshot/double-buffer scheduler accepts an
optional ready `SHIFT.NativeCameraStateBridge/1` through `--camera-state`.

The bridge can seed the recovered numeric mode/sub-index/camera-id/group state
before the fixed-step loop. It never transports or dereferences the opaque
retail camera/source reference; that native token remains zero.

The Phase 599 scheduler then snapshots, copies and flips the loaded state on the
existing native fixed-step boundary, retaining its explicit
`native-fixed-step-non-retail-timing` label.


## Phase 601 deterministic input scripts

Live X11 keyboard input still feeds the neutral `VehicleControlIntent`
boundary. For deterministic testing, the runtime additionally accepts:

```text
SHIFT.NativeRuntimeInputScript/1
0 1 0 0 0
1 1 0 0 1
2 0 1 1 0
3 0 0 1 1
4 0 0 0 0
```

Run it with:

```bash
xvfb-run -a native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --camera-state out/native-camera.json \
  --input-script out/native_input.script \
  --validation
```

If `--frames` is omitted, the script row count becomes the run length. If
`--frames N` is provided, `N` must match the row count exactly.

The script is native test/control infrastructure only. It does not claim retail
gamepad dead zones, analog response curves, filtering or vehicle-force
semantics.


## Phase 602 participant structural boundary

Generate the structural participant contract:

```bash
python3 src/physics/native_physics_participant_boundary.py \
  -o out/native_physics_participant_boundary.json
```

Then pass it to the runtime:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_boundary.json \
  --frames 120
```

The loader verifies the exact manager/selector separation and structural ABI.
It deliberately leaves `participant_ready=false`,
`participant_index=-1` and `participant_mode=-1`. A concrete retail
participant/provider still requires independent runtime evidence.


## Phase 603 native builtin sparse solver

The native build exposes a source-backed numerical backend for retail
`FUN_007b0f20`:

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
ctest --test-dir native_runtime/build --output-on-failure \
  -R shift_runtime_builtin_sparse_solver
native_runtime/build/shift_runtime_builtin_solver_check
```

The check covers deterministic 3×3 and 4×4 systems plus fail-closed invalid
graph and zero-pivot cases.

The backend is not a replacement for the provider path and is not yet called
from the vehicle fixed-step loop. Full-frame use still requires exact
matrix/RHS/reset evidence and provider-absent dispatch proof.


## Phase 604 native builtin diagonal reset

The same `shift_runtime_physics` backend now contains
`apply_builtin_diagonal_reset()`, the exact recovered `FUN_007b2210`
matrix/RHS mutation.

The parity check now covers six cases and reports both retail source functions:

```bash
ctest --test-dir native_runtime/build --output-on-failure \
  -R shift_runtime_builtin_sparse_solver
native_runtime/build/shift_runtime_builtin_solver_check
```

The API accepts already-selected scalar nodes only. Retail reset-node selection
depends on the runtime constraint-sample low bit at `+0x70` and remains an
external evidence gate. The native fixed-step loop still does not fabricate
that selection or a complete BMW solver frame.


## Phase 606 prepared builtin solver frames

Prepare a frame only after the input already contains exact runtime evidence
for provider absence, matrix/RHS, reset selection and the sparse graph:

```bash
python shift_importer.py native-builtin-solver-frame \
  solver-frame-input.json \
  out/native-solver-frame
```

Then execute the source-backed native reset/solve path and compare it to the
Python oracle:

```bash
native_runtime/build/shift_runtime_builtin_solver_frame_check \
  out/native-solver-frame/solver_frame.sbfr
```

The native loader independently verifies the packet proof mask. This executable
does not derive a BMW frame and is not yet called by the fixed-step vehicle
scheduler. Provider-present dispatch and post-solve body-state application stay
outside this contract.


## Phase 607 participant runtime evidence

The `--participant-boundary` option also accepts a ready
`SHIFT.NativePhysicsParticipantRuntimeEvidence/1` produced by:

```bash
python shift_importer.py native-participant-runtime-evidence \
  out/native_physics_participant_boundary.json \
  participant-observation.json \
  out/native_physics_participant_runtime_evidence.json
```

The observation must independently join the manager-registry participant and
the selected IGPhaseVehicle participant through the same pointer token. Native
code treats that token only as evidence; it is never dereferenced.

A successful join sets `participant_ready=true` and transports registry index,
selector ordinal and process state as separate fields. It does not assign a
provider or imply that registry index equals selector ordinal.


## Phase 608 fixed-step solver-frame mode

After preparing a Phase 606 frame and supplying a ready Phase 607 participant
evidence file, the offline runtime can execute the prepared builtin frame on
each fixed step:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_runtime_evidence.json \
  --solver-frame out/native-solver-frame/solver_frame.sbfr \
  --frames 120
```

The solver-frame scalar count must exactly match the physics workspace. The
runtime rechecks participant readiness on every step and executes only the
provider-absent Phase 606 reset/solve path. It does not feed the solved vector
into retail body state.


## Phase 609 prepared post-solve BODY projection

Prepare explicit solved-vector/BODY/constraint evidence:

```bash
python shift_importer.py native-post-solve-projection \
  post-solve-input.json \
  out/native-post-solve
```

Then execute the recovered `FUN_007b4110` projection and compare every BODY
accumulator channel with the Python oracle:

```bash
native_runtime/build/shift_runtime_post_solve_projection_check \
  out/native-post-solve/post_solve.sbps
```

The packet requires explicit proof for the solved vector, initial BODY state and
JOINT/HINGE/BAR rows. It does not derive those values from static SDF assets and
is not yet wired to the Phase 608 fixed-step solver-frame path.


## Phase 610 fixed-step post-solve mode

After preparing both the Phase 606 solver frame and Phase 609 post-solve packet,
the offline runtime can join them on every fixed step:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_runtime_evidence.json \
  --solver-frame out/native-solver-frame/solver_frame.sbfr \
  --post-solve-projection out/native-post-solve/post_solve.sbps \
  --frames 120
```

The runtime uses the actual native solver result as the `FUN_007b4110` input.
The solved vector stored inside SBPS is only a join witness and must match the
runtime solution. BODY and constraint counts must also match the admitted
physics workspace.

This completes prepared reset→solve→BODY-projection scheduling. It does not
persist the projected accumulators into vehicle motion, and it does not derive
retail matrix/RHS/reset/constraint rows.


## Phase 611 persistent post-solve BODY state

Phase 610 remains the default behavior: each fixed step replays the BODY input
embedded in the prepared SBPS packet.

To carry only the opaque BODY accumulator channels between fixed steps:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_runtime_evidence.json \
  --solver-frame out/native-solver-frame/solver_frame.sbfr \
  --post-solve-projection out/native-post-solve/post_solve.sbps \
  --persist-post-solve-body-state \
  --frames 120
```

The stateful executor requires the same solved-vector join and verifies the
prepared one-step `FUN_007b4110` BODY delta on every step. This is native
accumulator continuity only; vehicle transform/motion state is still not
integrated.

A deterministic packet-only check is also available:

```bash
native_runtime/build/shift_runtime_post_solve_persistence_check \
  out/native-post-solve/post_solve.sbps 5
```


## Phase 612 native BODY solver export

The native physics library also exposes the source-backed
`FUN_007ba570` additive BODY contribution transfer.

Run its deterministic regression with:

```bash
native_runtime/build/shift_runtime_body_solver_export_check
```

This primitive accepts already-prepared BODY solver-vector and solver-matrix
contributions and adds them into caller-owned destinations. It does not derive
those contributions or claim complete retail matrix/RHS assembly.


## Phase 613 prepared BODY solver export frame

Prepare explicit per-BODY `FUN_007ba570` contribution evidence:

```bash
python shift_importer.py native-body-solver-export-frame \
  body-export-input.json \
  out/native-body-export
```

Then verify the exact ordered native accumulation:

```bash
native_runtime/build/shift_runtime_body_solver_export_frame_check \
  out/native-body-export/body_solver_export.sbex
```

The packet carries contribution values and BODY order as evidence. Native code
does not derive `FUN_007bc680` output or runtime reset selection.


## Phase 614 BODY export / solver-frame join

After preparing both contracts, verify that the ordered BODY export is exactly
the matrix/RHS consumed by the builtin solver frame:

```bash
native_runtime/build/shift_runtime_body_export_solver_join_check \
  out/native-body-export/body_solver_export.sbex \
  out/native-solver-frame/solver_frame.sbfr
```

The join is pre-reset and fail-closed. It then runs the existing reset/solve
oracle only after the full vector and N×N matrix match.


## Phase 615 fixed-step BODY export evidence

A prepared solver frame can now be guarded by an explicit BODY export frame:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_runtime_evidence.json \
  --solver-frame out/native-solver-frame/solver_frame.sbfr \
  --body-solver-export-frame out/native-body-export/body_solver_export.sbex \
  --frames 120
```

On every fixed step the runtime replays `FUN_007ba570`, verifies the complete
pre-reset RHS/matrix against SBFR, and only then executes the prepared builtin
reset/solve path. A supplied mismatch is fail-closed.


## Phase 616 native FUN_007bc680 preprojection seed

The native physics library exposes the source-backed deterministic seed that
precedes JOINT/HINGE/BAR projection:

```bash
native_runtime/build/shift_runtime_body_preprojection_check
```

The checker reproduces the retail residual expressions, the exact
`FUN_007aefb0` float boundary and +0x90 linear scaling. It intentionally does
not execute the downstream constraint helpers yet.


## Phase 617 native JOINT projection

Run the deterministic source-backed JOINT kernel regression:

```bash
native_runtime/build/shift_runtime_joint_projection_check
```

It validates `FUN_007bac60` Q/L scales, exact BODY +0x18/+0x20/+0x28
cross/coupling terms, signed three-lane output, bounded solver-vector
application and fail-closed invalid inputs. It does not yet iterate runtime JOINT samples or execute
HINGE/BAR contributions.


## Phase 618 native HINGE projection

Run the deterministic source-backed HINGE kernel regression:

```bash
native_runtime/build/shift_runtime_hinge_projection_check
```

The checker covers both `sample+0x98` branches, including the nonzero-side
`FUN_007aefb0` body-frame transform and `FUN_007b1320` cross product, plus the
two-lane BODY solver-vector write and fail-closed range/frame/finite checks.
Authentic sample iteration, BAR projection and matrix coupling remain separate
gates.


## Phase 619 native BAR projection

Run the deterministic source-backed BAR kernel regression:

```bash
native_runtime/build/shift_runtime_bar_projection_check
```

The checker covers `FUN_007bb090`'s 0x60-byte sample contract, exact
three-component inline basis, `+0x40/+0x48/+0x50` weighted one-lane
reduction, nonzero-side `+0x38 * Q` correction, bounded solver-vector
application and fail-closed range/finite checks.

JOINT/HINGE/BAR projection primitives are now independently native. Authentic
BODY sample iteration and the matrix-coupling stages remain separate.


## Phase 620 native JOINT matrix coupling

Run the deterministic source-backed JOINT matrix regression:

```bash
native_runtime/build/shift_runtime_joint_matrix_coupling_check
```

The checker validates `FUN_007bbb80` JOINT self, JOINT↔JOINT,
JOINT↔HINGE and JOINT↔BAR blocks, including lower-triangle transpose/sign
behavior, the corrected `d15 = m00*y - m01*x` source term and bounded block
application.

The outer retail JOINT sample loop and sparse runtime row-pointer writes are not
yet executed by this checker. HINGE/HINGE, HINGE/BAR and BAR/BAR coupling stay
in their dedicated source-backed stages.


## Phase 621 native HINGE matrix coupling

Run the deterministic source-backed HINGE/HINGE matrix regression:

```bash
native_runtime/build/shift_runtime_hinge_matrix_coupling_check
```

The checker validates `FUN_007bb250` row transforms, self lower-triangle
entries, both pair storage orientations/sign paths and bounded 2×2 matrix
application.

The checker does not execute the mixed HINGE↔BAR portion or the complete retail
HINGE array loop.


## Phase 622 native HINGE↔BAR matrix coupling

Run the mixed HINGE/BAR regression:

```bash
native_runtime/build/shift_runtime_hinge_bar_matrix_coupling_check
```

It validates `FUN_007bb250` d5/d6 mixed-block equations, both lower-triangle
storage orientations/sign paths and bounded matrix application. Full HINGE
array iteration remains separate.


## Phase 623 native BAR matrix coupling

Run the deterministic BAR/BAR matrix regression:

```bash
native_runtime/build/shift_runtime_bar_matrix_coupling_check
```

The checker validates `FUN_007bb6c0` cross/frame transformation, self and pair
coefficients, lower-triangle cell selection and bounded scalar application.
Complete BAR array iteration remains separate.


## Phase 624 prepared BODY constraint assembly

Run the source-order BODY contribution regression:

```bash
native_runtime/build/shift_runtime_body_constraint_assembly_check
```

The checker supplies one explicit prepared JOINT, HINGE and BAR sample, runs
the native `FUN_007bc680` preprojection/projection/matrix sequence and freezes
the resulting six-lane BODY-local solver vector plus six-by-six lower-triangle
matrix.

The input is intentionally downstream of `FUN_007b3ed0`: Phase 624 does not
derive refreshed runtime sample values. It also retains a dense logical matrix
view rather than claiming exact `BODY+0x158` sparse row-pointer execution.


## Phase 625 BODY sparse row storage

Run:

```bash
native_runtime/build/shift_runtime_body_sparse_matrix_storage_check
```

The checker remaps the Phase 624 six-scalar lower matrix through an explicit
noncanonical `BODY+0x15c` row-index vector, verifies the corresponding
`BODY+0x158` byte-offset view and reads every logical cell back from the
`BODY+0x154` pool. Aliased/out-of-range rows and upper-triangle writes are
fail-closed.


## Phase 626 generated BODY export join

Run:

```bash
native_runtime/build/shift_runtime_generated_body_solver_export_check
```

The checker reuses the Phase 624 mixed prepared BODY fixture, materializes its
matrix through the Phase 625 canonical builtin row layout and feeds the exact
result to `FUN_007ba570`. The generated solver vector and 36-double matrix
must match the exported global destinations with zero error.

This stage is provider-absent only. Provider-shaped noncanonical row storage is
rejected rather than reinterpreted, and runtime `FUN_007b3ed0` sample refresh
is still outside the generated input boundary.


## Phase 627 prepared generated BODY frame

Prepare BODY state/sample input without embedding generated contribution values:

```bash
python shift_importer.py native-generated-body-constraint-frame \
  generated-body-input.json \
  out/generated-body

native_runtime/build/shift_runtime_generated_body_constraint_frame_check \
  out/generated-body/generated_body_constraints.gbcf
```

The GBCF packet contains prepared BODY state plus JOINT/HINGE/BAR samples and
canonical row indices. Native execution derives the contribution through
Phases 624–626 and aggregates it globally. The packet does not contain solver
matrix/RHS contribution arrays.

Phase 628 admits this packet directly on native fixed steps. The runtime
regenerates the global matrix/RHS and requires exact equality with the supplied
SBFR before reset/solve. Authentic `FUN_007b3ed0` sample refresh remains a
separate gate.

## Phase 628 generated BODY fixed-step join

Verify the nonzero GBCF→SBFR equality gate directly:

```bash
native_runtime/build/shift_runtime_generated_body_solver_frame_join_check \
  out/generated-body/generated_body_constraints.gbcf \
  out/generated-body-solver/solver_frame.sbfr
```

Run the same generated contribution path on every admitted fixed step with:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/runtime-participant.json \
  --solver-frame out/solver/solver_frame.sbfr \
  --generated-body-constraint-frame out/generated-body/generated_body_constraints.gbcf \
  --frames 3
```

`--generated-body-constraint-frame` and `--body-solver-export-frame` are
mutually exclusive. GBCF stores prepared BODY/sample inputs only; generated
solver-vector/matrix contribution arrays are never read from the packet.


## Phase 629 constraint sample refresh

Run the source-backed `FUN_007b3ed0` numerical refresh regression:

```bash
native_runtime/build/shift_runtime_constraint_sample_refresh_check
```

The checker covers the exact JOINT/HINGE/BAR helper sequence
`FUN_007b2da0 → FUN_007b2de0 → FUN_007b2f70`, the shared
`FUN_007aefb0` forward transform, the HINGE `FUN_007af0a0` transpose
transport, HINGE negative-side basis rebuild and BAR normalized endpoint
direction.

Phase 629 refreshes prepared endpoint/sample state only. It does not yet
serialize the retail 0xA0/0xA0/0xB8 top-level relation ownership into a packet
or replace GBCF's prepared sample fields on fixed steps.


## Phase 630 constraint relation ownership

Prepare the source-order ownership packet with:

```bash
python shift_importer.py native-constraint-sample-relation-frame \
  constraint-relations.json \
  out/constraint-relations
```

Then verify the relation → BODY-owned sample refresh join against a prepared
GBCF:

```bash
native_runtime/build/shift_runtime_constraint_sample_relation_frame_check \
  out/generated-body/generated_body_constraints.gbcf \
  out/constraint-relations/constraint_sample_relations.csrf
```

The checker enforces exact positive/negative endpoint ownership, source-backed
side flags, common scalar identity and complete non-duplicated coverage before
executing `FUN_007b3ed0`.

One top-level relation owns two BODY samples. Phase 630 therefore keeps
relation counts separate from refreshed endpoint-sample counts rather than
reusing the Phase 628 synthetic one-sample-per-relation scheduler fixture.

CSRF is not yet a `shift_runtime` fixed-step option; that join is the next
native integration boundary.


## Phase 631 fixed-step constraint refresh

Run GBCF through the source-order relation refresh on every native fixed step:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/runtime-participant.json \
  --solver-frame out/solver/solver_frame.sbfr \
  --generated-body-constraint-frame out/generated-body/generated_body_constraints.gbcf \
  --constraint-sample-relation-frame out/constraint-relations/constraint_sample_relations.csrf \
  --frames 3
```

CSRF requires GBCF. The runtime compares CSRF relation counts to the physics
workspace, then requires the refreshed/generated GBCF sample counts to match
the exact Phase 630 endpoint coverage. For BMW this distinguishes 4/4/20
relations from 8/8/40 BODY-owned endpoint samples.

Each fixed step executes `FUN_007b3ed0` before the existing generated
BODY→SBFR equality gate. GBCF and CSRF remain immutable prepared inputs; retail
per-frame BODY motion/raw relation input production is still outside this
boundary.


## Phase 632 relation-state reset selection

Prepare the source-order relation state packet:

```bash
python shift_importer.py native-constraint-relation-reset-frame \
  relation-reset-input.json \
  out/relation-reset
```

Verify a GBCF + CSRF + CRRF identity/reset join:

```bash
native_runtime/build/shift_runtime_constraint_relation_reset_frame_check \
  out/generated-body/generated_body_constraints.gbcf \
  out/constraint-relations/constraint_sample_relations.csrf \
  out/relation-reset/constraint_relation_reset.crrf
```

Run the fixed-step source-derived reset path by adding:

```text
--constraint-relation-reset-frame out/relation-reset/constraint_relation_reset.crrf
```

CRRF carries only the source-order low bit tested at retail
`relation+0x70 & 1`. Scalar bases are recovered from the positive BODY-owned
GBCF sample identified by CSRF, and reset widths are fixed by relation type:
JOINT 3, HINGE 2, BAR 1. The packet never stores reset-node indices.

When CRRF is supplied, `shift_runtime` reconstructs the retail reset-call
sequence, normalizes it to a reset-node set and requires exact equality with
`SBFR.reset_nodes` before every solve. The unchanged SBFR
`FUN_007b2210 → FUN_007b0f20` oracle then executes. Repeated reset calls are
preserved by the selector before set normalization, and no unsupported
whole-domain coverage rule is imposed.


## Phase 633 relation-state mutation kernel

The native physics library now includes the source-backed `FUN_00757d2c`
bit0 mutation semantics for the relation state consumed by Phase 632.

Run the deterministic regression with:

```bash
ctest --test-dir native_runtime/build --output-on-failure \\
  -R shift_runtime_constraint_relation_state_mutation
native_runtime/build/shift_runtime_constraint_relation_state_mutation_check
```

The pair branch uses an unordered pair of CSRF BODY identities and sets matching
JOINT/HINGE bit0 state. The BAR branch uses one BODY identity and sets bit0 for
every BAR relation touching that endpoint. Existing bits are never cleared.

This is intentionally a library/checker boundary only. `shift_runtime` does
not schedule the mutation because raw executable/source evidence proves the 0..3 component index,
0xA80 stride and FL/FR/RL/RR wheel/spindle plus rear-axle BODY mapping, but the
retail event semantics and timing are not yet proven.
