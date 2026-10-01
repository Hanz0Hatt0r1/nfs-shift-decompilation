# Native Linux runtime status

## Milestone

The initial offline Linux runtime shell is now implemented as `native_runtime/`.

The runtime is merged on main. Linux CI exercises the material-mode frame loop under Xvfb/lavapipe, including three rendered frames, three fixed simulation steps, one 2D bundle texture, the cube resource, and the admitted 40-scalar physics workspace. The merge also fixes two Vulkan create-info lifetime bugs that previously left queue-family and descriptor-set-layout pointers referring to expired stack arrays.

Current slice:

```
MGEO
  ↓
native_ir
  ↓
XCB window
  ↓
Vulkan surface / swapchain
  ↓
indexed geometry submission
  ↓
bounded frame loop
```

The executable emits `SHIFT.NativeRuntimeBootstrap/1` and `SHIFT.NativeRuntimeFrameLoop/1` records. Bundle mode now consumes the prepared `SHIFT.BMWVulkanBundle/1` end-to-end for the supported interface slice: native-submission/SPIR-V/interface gates, full vertex packet layout, bundle SPIR-V modules, `SVCP` constants, `SVTP` 2D textures, optional cube, descriptor sets and indexed submission. The frame loop has a fixed 60 Hz simulation boundary and neutral `SHIFT.NativeRuntimeInput/1` keyboard state. The new `SHIFT.NativeRuntimeState/1` layer carries evidence-shaped camera double-buffer state, vehicle control intent, and a physics participant/tick boundary. Native runtime can also consume the repository's real `SHIFT.BMWM3VehiclePhysicsResourceManifest/1` and prepare the proven 40-scalar SDF workspace (matrix-pool and row-pointer sizing), while intentionally stopping before inventing unresolved retail force integration/provider semantics.

## Deliberate exclusions

The Linux target does not require EA services, online functionality, DRM, login/profile/cloud services, matchmaking or Bink/video playback for the test build.

## Next integration gates

1. Close real BMW per-draw state differences that are not yet represented by the current Vulkan child pipeline (blend/cull/depth and remaining renderer-global resources).
2. Phase 599 connects the six-word CameraManager snapshot and guarded double-buffer swap to the native fixed-step scheduler. Phase 600 adds fail-closed recovered scalar evidence input through SHIFT.NativeCameraStateBridge/1 and --camera-state. Remaining camera work is retail timestamp/update scheduling, camera-source/controller behavior, gameplay view selection/attachment and exact render/view integration.
3. Phase 602 connects the source-backed PhysicsParticipantManager registry ABI and separate selector context to native state through `SHIFT.NativePhysicsParticipantBoundary/1`. Concrete selected participant instance/index/mode and provider identity remain capture-gated.
4. Phases 603–610 supply the provider-absent native reset→solve→post-solve chain, including exact participant evidence and fixed-step joins. Phase 611 adds explicit continuity for the six opaque BODY accumulator channels across fixed steps while keeping persistent vehicle motion false. Remaining physics evidence gates are authentic matrix/RHS/reset/constraint assembly, provider-present dispatch and rigid-body/vehicle integration.
5. Connect scene/track resource loading. Phases 581–585 close SVWT transport, semantic-aware SVGP v3, affine execution and neutral scene-set preparation. Phase 586 adds direct `SHIFT.NativeSceneVulkanSetPrepare/1` ingestion through `native_runtime --scene-set`. Authentic runtime-proven Silverstone draws, unresolved renderer-owned scene resources, streaming/LOD and per-instance transform history remain.
6. Live keyboard vehicle controls already feed the neutral intent layer. Phase 601 adds a deterministic fixed-step input script and physics-boundary activity telemetry for CI. Gamepad/analog normalization and retail filtering remain.
7. Replace the bounded frame loop with the native game loop/state machine after render/state contracts stabilize.

The renderer remains downstream of normalized IR; original BFF parsing stays outside the native executable.


## Phase 526 multi-draw boundary

The runtime accepts `--bundle-set DIR` only when both
`SHIFT.BMWVulkanBundleSet/1` and
`SHIFT.BMWVulkanBundleSetPrepare/1` are ready. The ordered
`bundle_set.paths` sidecar is checked against both draw counts and cannot
contain absolute or parent-traversal paths.

Each prepared child owns independent Vulkan state:

- vertex/index buffers and draw range;
- VS/PS constant buffers;
- sampled 2D/cube images and samplers;
- descriptor set layouts/pool/sets;
- SPIR-V shader modules;
- pipeline layout and graphics pipeline.

All child draws share the swapchain, render pass, depth attachments and frame
synchronization and are submitted in recorded draw order inside one render
pass. The original `--bundle` mode uses the same path with one material draw.


## Phase 527 material-slice multi-draw boundary

The BMW material adapter can now emit
`SHIFT.BMWMaterialSliceVulkanSet/1`. Each selected RenderCommand submesh is
bridged independently into its canonical
`draws/submesh_NNN/SHIFT.BMWVulkanBundle/1` child before the top-level set is
indexed.

This ordering matters for real data: exact DDS extraction, SHA-256 provenance,
decoded texture packets, optional environment-cube resources, constants and
shader identity remain child-local. The set index reads the finalized child
manifests rather than rebuilding them, so per-material evidence is not lost.

A blocked submesh does not erase ready siblings, but the complete set remains
fail-closed until every selected child is ready. The existing single-submesh
adapter and CLI remain available; `--all-submeshes` selects the Phase 527
set path.


## Phase 586 neutral scene-set execution

The runtime now accepts `--scene-set DIR` only for a ready
`SHIFT.NativeSceneVulkanSet/1` with a ready
`SHIFT.NativeSceneVulkanSetPrepare/1` in `bundle_set_prepare.json`.

Neutral children must be `SHIFT.VulkanDrawBundle/1` with ready
`SHIFT.VulkanDrawBundlePrepare/1`, native-submission, SPIR-V and
`SHIFT.VulkanInterfaceGate/1` artifacts.

Before upload, `world_transform.svwt` is applied with the Phase 584 semantic
affine rules. BMW `--bundle-set` remains a separate compatible path.

Linux Vulkan CI executes a validated three-frame neutral scene-set smoke.


## Phase 587 scene transform execution telemetry

`SHIFT.NativeRuntimeBootstrap/1` now reports
`world_transform_draws` and `affine_world_transform_draws`.

The first counter increments only after a child SVWT has passed the existing
fail-closed runtime transform path and mutated the native geometry before GPU
upload. The second excludes translation-only matrices, so the Phase 586
non-singular affine smoke must prove that the semantic-aware affine branch
actually ran.

Linux Vulkan CI requires both counters to equal one for the neutral one-child
scene-set fixture.


## Phase 588 external sampler2D transport boundary

The native runtime binary ABI does not change in Phase 588. Explicit external
`sampler2D` snapshots are serialized as ordinary SVTP descriptor-set-1
records at their original D3D9 register, so the existing native texture upload
path consumes them without a special renderer-side resource class.

The upstream bundle metadata preserves whether each SVTP record came from a
material texture or an external runtime snapshot. Missing external resources
remain unresolved and are not synthesized by `native_runtime`.


## Phase 589 exact external sampler2D scene admission

Phase 589 does not change the native binary texture ABI. An exact scene-bound
external `sampler2D` snapshot is admitted upstream into the existing SVTP
descriptor-set-1 packet only after draw/resource/primitive/register/type/hash
and provenance revalidation. `native_runtime` consumes the resulting record
through its existing 2D texture upload path.

Unsupplied or mismatched external resources remain fail-closed, and other
renderer-owned resource types are not promoted by this phase.


## Phase 599 camera state boundary

`SHIFT.NativeRuntimeState/1` now executes the recovered CameraManager snapshot
and guarded two-buffer transition on the native fixed-step boundary. Each
native update records the six-word manager snapshot, copies/flips the camera
buffer, and clears the update guard before the step completes.

The frame-loop report exposes `camera_snapshot_count`,
`camera_native_updates`, final `camera_active_buffer`,
`camera_update_in_progress` and the explicit schedule label
`native-fixed-step-non-retail-timing`.

This is a native integration boundary only. It does not map the retail
`FUN_0080c920` timestamp source, 0x14 suppression window, absolute time unit,
or `FUN_0080c510` controller semantics onto the 60 Hz native clock.


## Phase 600 recovered camera evidence input

The Phase 599 native camera scheduler can now be initialized from a ready
`SHIFT.NativeCameraStateBridge/1` through `--camera-state`.

The bridge validates the existing CameraManager snapshot plus ordered
swap/completion reports and transports only numeric manager/buffer state:
active index/guard, mode, sub-index/flag, camera id, active group and restore
group. The opaque camera/source word is deliberately not transported; the
native token remains zero.

After admission, the ordinary Phase 599 fixed-step snapshot/copy/flip path runs
unchanged. Linux Vulkan CI verifies that 12 native updates preserve the loaded
mode/id/group/sub-state and that the Phase 599 snapshot telemetry observes the
same recovered values.


## Phase 601 deterministic control-intent boundary

`native_runtime` accepts `--input-script FILE` with
`SHIFT.NativeRuntimeInputScript/1`. Each row supplies the complete
throttle/brake/left/right state for one contiguous native fixed step.

Without the option, the existing X11 keyboard mapping remains active. With it,
the script supplies vehicle intent while X11 continues to handle quit/window
events. `--camera-state` remains compatible and can be loaded in the same run.

`PhysicsTickBoundary::tick()` counts active throttle, brake, left, right and
fully-neutral steps. The final frame-loop telemetry exposes those counters plus
the last control state and `input_source`, proving the deterministic input
crossed `SHIFT.NativeRuntimeState/1` rather than merely being parsed.

Linux Vulkan CI runs a five-step script and verifies the exact activity counts.
No retail controller dead-zone, analog curve, filtering, or vehicle-force
semantics are assigned.


## Phase 602 participant structural boundary

The native runtime optionally accepts `--participant-boundary` with
`SHIFT.NativePhysicsParticipantBoundary/1`. The contract preserves the
proven distinction between the `DAT_00c109e0` PhysicsParticipantManager
registry and the `DAT_00bbc600` IGPhaseVehicle selector context, validates
the `0x1fa0` registry-slot stride and descriptor type `3`, and carries only
that structural ABI into `PhysicsTickBoundary`.

Structural admission never promotes static evidence into a retail participant:
`participant_ready=false`, `participant_index=-1`, and
`participant_mode=-1` remain mandatory until independent runtime-instance
evidence exists. Linux Vulkan CI verifies this boundary alongside the Phase 600
camera evidence input and Phase 601 deterministic input path.


## Phase 603 native builtin sparse solver

The native runtime build now contains `shift_runtime_physics`, whose
`solve_builtin_sparse()` mirrors the recovered retail builtin solver
`FUN_007b0f20`.

The backend preserves the recovered sparse factorization and
forward/back-substitution traversal and validates the same `n+1` forward /
`n` reverse record cardinality.

`shift_runtime_builtin_solver_check` covers two deterministic numeric systems,
invalid graph cardinality and zero-pivot rejection. Linux CI runs that check
through CTest and retains its JSON report.

This is not yet a complete native BMW physics step. The frame loop still does
not synthesize matrix/RHS assembly, diagonal-reset selection flags, provider
dispatch, post-solve body application or a concrete runtime participant.


## Phase 604 native builtin diagonal reset

`shift_runtime_physics` now also exposes
`apply_builtin_diagonal_reset()`, mirroring recovered `FUN_007b2210`.

For every explicitly supplied scalar node it zeroes the matrix row and column,
sets the diagonal to `1.0`, and zeroes the RHS entry. Duplicate nodes are
normalized; out-of-range nodes fail closed.

The native regression reports both `FUN_007b0f20` and `FUN_007b2210` and
covers four solve cases plus two reset cases.

Reset-node **selection** remains separate. The retail frame selects reset
records through runtime `sample+0x70 & 1`; Phase 604 does not infer that bit
from static data and does not yet invoke a complete BMW frame.


## Phase 606 prepared builtin solver-frame boundary

The native physics library now consumes
`SHIFT.NativeBuiltinSolverFramePacket/1` (`SBFR`) through the standalone
`shift_runtime_builtin_solver_frame_check`.

A frame is executable only when the packet carries all four explicit proof
bits:

- provider absent;
- matrix/RHS ready;
- reset-node selection ready;
- sparse graph ready.

The execution order is the recovered builtin path:

`FUN_007b2210 → FUN_007b0f20`.

Python preparation executes the same source-backed reset/solve sequence first
and stores the expected solution in the packet. Native execution compares its
result against that oracle and fails closed on mismatch.

Linux Vulkan CI prepares a synthetic 3-scalar regression frame, verifies
native/Python parity, then clears one proof bit and requires the native loader
to reject the packet.

This is not fixed-step BMW integration. Retail matrix/RHS assembly, runtime
reset selection, participant/provider identity, provider-present dispatch and
`FUN_007b4110` body-state application remain separate evidence gates.


## Phase 607 participant runtime identity evidence

The existing `--participant-boundary FILE` input now accepts either the
structural `SHIFT.NativePhysicsParticipantBoundary/1` contract or a ready
`SHIFT.NativePhysicsParticipantRuntimeEvidence/1`.

Runtime evidence promotes a participant only when one observed 32-bit pointer
token independently appears in both the PhysicsParticipantManager registry
observation and the selected `IGPhaseVehicle+0x450` pointer slot. The native
runtime never dereferences that token.

The promoted state transports three separate values:

- PhysicsParticipantManager registry index;
- IGPhaseVehicle selector ordinal;
- IGPhaseVehicle participant process state.

Registry index and selector ordinal are deliberately not equated. The Phase 602
legacy `participant_index/mode` aliases remain `-1`.

Linux Vulkan CI preserves both boundaries: the structural scene smoke remains
unresolved for all three steps, while a synthetic runtime observation drives
five ready participant steps with registry index 7 and selector ordinal 2.

Provider identity, provider selection and numerical physics equivalence remain
unassigned.


## Phase 608 fixed-step prepared solver-frame execution

The native runtime accepts an optional `--solver-frame FILE` containing the
Phase 606 `SBFR` packet.

Admission requires a ready physics workspace, a Phase 607 participant-ready
identity join and exact solver/workspace scalar-count equality. The packet's
provider-absent/matrix-RHS/reset-selection/sparse-graph proof mask is still
validated by the Phase 606 native loader.

When admitted, every native fixed step executes
`FUN_007b2210 → FUN_007b0f20` and verifies the result against the Python oracle.
Telemetry records solver-frame steps, scalar/reset counts and maximum oracle
error while explicitly reporting provider-present=false and
post-solve-body-state-applied=false.

Linux Vulkan CI replays a synthetic 40-scalar frame for five deterministic
steps. This proves scheduler integration only; it does not claim retail
matrix/RHS assembly or `FUN_007b4110` body-state semantics.


## Phase 609 native post-solve BODY projection

The native physics library now also consumes
`SHIFT.NativePostSolveBodyProjectionPacket/1` (`SBPS`) through
`shift_runtime_post_solve_projection_check`.

Admission requires explicit proof for the solved vector, initial BODY
accumulator state and complete JOINT/HINGE/BAR rows. The executor ports
`FUN_007b4110` exactly: JOINT uses the recovered positive/negative body
accumulator helpers, HINGE updates only angular channels from its two solved
scalars, and BAR scales its direction before the same body helpers. Execution
order remains JOINT → HINGE → BAR.

Python preparation uses the existing source-backed post-solve runtime module as
the oracle; native execution compares all six channels of every BODY and fails
closed on mismatch. Linux CI also clears one proof bit and requires native
rejection.

Phase 609 is deliberately standalone. The Phase 608 fixed-step scheduler does
not yet feed its solved vector into SBPS, and runtime BODY/constraint rows are
not derived from static assets.


## Phase 610 fixed-step solve → post-solve join

The native fixed-step scheduler now accepts `--post-solve-projection FILE`
only together with the Phase 608 `--solver-frame` path.

Admission requires:

- a ready Phase 607 runtime participant identity;
- a ready physics workspace;
- solver-frame/workspace scalar equality;
- SBPS scalar count equal to the Phase 608 solver frame;
- SBPS BODY count equal to the workspace BODY count;
- SBPS JOINT and HINGE counts each equal to `joint_hinge_count`;
- SBPS BAR count equal to `bar_count`;
- complete Phase 609 proof bits.

On every admitted fixed step the runtime executes
`FUN_007b2210 → FUN_007b0f20`, passes the actual native
`solver_result.solution` into the Phase 609 projection, requires it to match
the prepared SBPS vector, then executes `FUN_007b4110`.

Telemetry records post-solve counts, steps, maximum solved-vector join error and
maximum BODY oracle error. `physics_solver_post_solve_body_state_applied=true`
means the prepared BODY projection completed after every solver step.

`physics_solver_persistent_vehicle_state_applied=false` remains explicit:
the prepared initial BODY state is replayed for evidence/parity and the result
is not yet integrated into persistent vehicle motion.

Linux CI executes five synthetic 40-scalar steps with the exact BMW workspace
cardinalities 11 BODY / 4 JOINT / 4 HINGE / 20 BAR, then independently rebuilds
a valid SBPS packet with one mismatched scalar and requires the runtime to
reject the solve→projection join.


## Phase 611 persistent BODY accumulator boundary

The Phase 610 solver→projection chain now has an optional native continuity
mode, `--persist-post-solve-body-state`.

When enabled, the first fixed step starts from the SBPS prepared BODY state and
every later step starts from the previous native `FUN_007b4110` output.
The executor checks the prepared one-step BODY delta on every step, so state
continuity does not disable the Phase 609 numerical oracle.

Telemetry distinguishes this from vehicle integration:

- `physics_solver_persistent_body_accumulator_state_applied` may become true;
- `physics_solver_persistent_vehicle_state_applied` remains false.

Linux Vulkan CI preserves the old Phase 610 non-persistent run and adds a
five-step persistent BODY run plus a deterministic standalone accumulation
checker.


## Phase 612 native BODY solver export

`shift_runtime_physics` now contains the exact source-backed
`FUN_007ba570` additive export from BODY-local solver-vector/matrix
contributions into caller-owned global solver destinations.

The native checker covers sequential multi-BODY accumulation and short-buffer
rejection with zero numerical error.

This closes only the export primitive. BODY contribution generation,
`FUN_007bc680`, runtime sampled-state refresh, reset selection and complete
retail matrix/RHS assembly remain separate gates.


## Phase 613 prepared BODY solver export frame

The native runtime physics library can now load and execute a proof-gated SBEX
packet containing exact ordered per-BODY solver-vector/matrix contribution
arrays.

The executor starts complete global destinations at zero, invokes the Phase 612
`FUN_007ba570` primitive for each BODY and requires exact Python-oracle parity.
Linux CI also rejects a packet with an incomplete proof mask.

Contribution generation itself remains outside this contract. Phase 613 does
not derive `FUN_007bc680`, reset flags or retail matrix/RHS state and does not
yet feed its result into the prepared builtin solver frame.


## Phase 614 BODY export / solver-frame join

The native physics library can now require exact equality between a prepared
Phase 613 `FUN_007ba570` export and the pre-reset matrix/RHS stored in a
Phase 606 solver frame.

The join compares all N RHS values and all N² matrix doubles before allowing the
existing `FUN_007b2210 → FUN_007b0f20` executor to run. Linux CI includes a
matching fixture and a separately valid SBEX that is rejected because its RHS
does not match SBFR.

This is still an evidence join. BODY contribution generation and runtime reset
selection remain external inputs.


## Phase 615 fixed-step BODY export gate

The fixed-step runtime now accepts `--body-solver-export-frame FILE` only
alongside `--solver-frame FILE`.

Before every prepared builtin solve, the runtime replays the supplied
proof-gated `FUN_007ba570` BODY contributions and requires exact equality with
the SBFR pre-reset RHS and complete N×N matrix. Only then may the existing
`FUN_007b2210 → FUN_007b0f20` path execute.

Telemetry reports BODY export join-step count plus maximum RHS/matrix error.
Linux CI runs five matching 40-scalar runtime steps and requires five zero-error
SBEX→SBFR joins. The deterministic Phase 614 join regression independently
keeps a valid-but-mismatched SBEX fail-closed.

This remains an evidence gate: `FUN_007bc680` contribution generation,
runtime reset selection and provider-present dispatch are still external.


## Phase 616 native FUN_007bc680 preprojection seed

The native physics library now executes the deterministic front of
`FUN_007bc680` before any constraint projection helper is called.

It reproduces the three double residual expressions from BODY offsets
+0x18..+0x58, passes them through the exact `FUN_007aefb0` float-matrix /
float-input boundary, and prepares the +0x60/+0x68/+0x70 channels scaled by
+0x90.

`shift_runtime_body_preprojection_check` covers identity, nontrivial matrix,
zero-state and non-finite rejection cases and reports
`full_constraint_projection_executed=false`.

Native JOINT/HINGE/BAR projection and matrix coupling remain separate gates;
Phase 616 does not synthesize sampled constraint state or complete
`FUN_007bc680`.


## Phase 617 native FUN_007bac60 JOINT projection

The native physics library now executes one source-backed JOINT sample through
`FUN_007bac60`: exact Q/L scale preparation, three corrected cross terms,
three double scalar lanes, side-flag sign selection and bounded writes into a
neutral solver-vector destination.

During the port the older Python Phase 397 oracle was corrected: all JOINT
cross and axis-coupling terms now use BODY +0x18/+0x20/+0x28 exactly as the
retail function does, rather than the unrelated BODY position triplet.

The phase remains a single-sample primitive. BODY-owned JOINT iteration,
HINGE/BAR projection and all matrix-coupling kernels are still separate gates.


## Phase 618 native FUN_007bae40 HINGE projection

The native physics library now executes the complete source-backed two-lane
equations for one HINGE sample through `FUN_007bae40`.

The zero-side branch evaluates the recovered axis/residual projection
directly. The nonzero-side branch requires the BODY frame, preserves the
`FUN_007aefb0` float boundary, computes the recovered
`sample_frame_offset × transformed_sample_position` helper result and applies
the quadratic scale before evaluating both lanes. The exact zero/add versus
nonzero/subtract rule is retained.

`shift_runtime_hinge_projection_check` covers both existing Python-oracle
fixtures, a nontrivial body-frame transform/cross case, exact two-lane solver
vector application, invalid range, missing frame and non-finite rejection.

This is still an independent primitive. Phase 618 does not synthesize HINGE
sample arrays, run the BAR helper, assemble matrix coupling or claim a complete
`FUN_007bc680` BODY contribution.


## Phase 619 native FUN_007bb090 BAR projection

The native physics library now executes one exact source-backed BAR sample
through `FUN_007bb090`.

The helper reproduces the inline three-component BODY/sample basis already seen
algebraically in the JOINT projection, then reduces it with the BAR
`+0x40/+0x48/+0x50` weight vector to one solver lane. The nonzero-side branch
retains the distinct retail correction:

`destination -= raw_lane - sample[+0x38] * Q`.

`shift_runtime_bar_projection_check` verifies the source-backed 0x60 record
stride, one-lane bounded write, both side branches, finite-input rejection and
Python/native parity within `1e-12`.

With Phases 617–619, all three independent JOINT/HINGE/BAR projection
primitives used by the `FUN_007bc680` contribution path now have native
source-backed implementations. BODY-owned sample iteration and
`FUN_007bbb80/FUN_007bb250/FUN_007bb6c0` matrix-coupling orchestration remain
separate gates.


## Phase 620 native FUN_007bbb80 JOINT matrix coupling

The native physics library now evaluates the exact source-backed JOINT-owned
matrix block algebra from `FUN_007bbb80`.

The port covers:

- JOINT self 3×3 lower-triangle block;
- JOINT↔JOINT 3×3 block;
- JOINT↔HINGE 3×2 block;
- JOINT↔BAR 3×1 block;
- exact equal-side add / differing-side subtract behavior;
- exact lower-triangle orientation from scalar-base ordering.

The `d15` intermediate remains explicitly sourced as
`m00*y - m01*x`, preserving the earlier correction that rejected an
accidental `m02` substitution.

`shift_runtime_joint_matrix_coupling_check` verifies all frozen Python
oracle blocks, both storage orientations, a non-degenerate off-diagonal tensor,
bounded matrix writes and fail-closed range/non-finite handling at `1e-12`
parity tolerance.

This closes block algebra only. BODY-owned JOINT iteration, sparse row-pointer
writes, `FUN_007bb250` HINGE coupling and `FUN_007bb6c0` BAR coupling remain
separate.


## Phase 621 native FUN_007bb250 HINGE/HINGE matrix coupling

The native physics library now evaluates the exact source-backed HINGE/HINGE
block algebra from `FUN_007bb250`.

Both HINGE angular/linear rows cross the retail `FUN_007aefb0` float transform
boundary before dot products are formed. The native port covers the self 2×2
lower triangle and pair 2×2 block, including scalar-base transpose orientation
and equal-side add / differing-side subtract behavior.

`shift_runtime_hinge_matrix_coupling_check` freezes the existing Python
oracles, verifies bounded block application and rejects range/non-finite input
at `1e-12` parity tolerance.

HINGE↔BAR coupling inside the same retail function, complete HINGE iteration and
sparse row-pointer writes remain separate gates.


## Phase 622 native FUN_007bb250 HINGE↔BAR matrix coupling

The native physics library now executes the remaining source-backed mixed block
inside `FUN_007bb250`: HINGE↔BAR 2×1/1×2 coupling.

The implementation reuses the Phase 621 HINGE `FUN_007aefb0` row-transform
boundary, evaluates the exact d5/d6 BAR point/direction expressions, then
stores them with the retail scalar-base orientation and equal/different-side
sign rule.

`shift_runtime_hinge_bar_matrix_coupling_check` freezes the existing Python
oracle `d5=3, d6=-6`, both orientation/sign branches, bounded writes and
range/non-finite rejection at `1e-12` parity tolerance.

All currently recovered block algebra in `FUN_007bb250` is now native.
Complete HINGE iteration/sparse writes and BAR/BAR `FUN_007bb6c0` remain.


## Phase 623 native FUN_007bb6c0 BAR/BAR matrix coupling

The native physics library now executes the source-backed BAR/BAR matrix
coefficient algebra from `FUN_007bb6c0`.

The port preserves the BAR point×direction cross product, exact
`FUN_007aefb0` float transform boundary, inverse-scalar direction terms,
self coefficient, pair coefficient, equal/different-side sign rule and
max-base/min-base lower-triangle cell selection.

`shift_runtime_bar_matrix_coupling_check` freezes self=262 and pair=388
oracles, verifies lower-triangle addressing and bounded scalar writes, and
rejects range/non-finite inputs at `1e-12` parity tolerance.

With Phases 620–623, all currently recovered JOINT/HINGE/BAR matrix block
algebra is native. Full BODY-owned sample iteration and sparse row-pointer
orchestration remain the next contribution-builder boundary.


## Phase 624 prepared BODY constraint orchestration

The native physics library now joins the Phase 616–623 source-backed primitives
into one prepared per-BODY `FUN_007bc680` contribution build.

`assemble_fun_007bc680_body_constraints()` consumes explicit refreshed sample
values, validates non-overlapping JOINT/HINGE/BAR scalar ranges, executes the
recovered JOINT→HINGE→BAR projection order, then executes JOINT-owned,
HINGE-owned and BAR-owned matrix passes without duplicate pair writes.

The deterministic mixed fixture produces:

- solver vector `[7.125, 15, 20.3125, 9.125, 20.75, 52.5]`;
- a six-scalar lower-triangle matrix with all JOINT/HINGE/BAR self and mixed
  blocks;
- exact source-order stage counts at `1e-12` tolerance.

This closes prepared sample-array orchestration only. Runtime
`FUN_007b3ed0` sampled-state refresh, exact `BODY+0x158` sparse row-pointer
execution and fixed-step generated-contribution→SBEX integration remain
separate gates.


## Phase 625 BODY sparse row storage

The Phase 624 logical lower-triangle BODY matrix can now be materialized through
the exact prepared `FUN_007bb8d0` row-index contract:

`BODY+0x15c row_indices → BODY+0x158 row offsets → BODY+0x154 matrix pool`.

The native helper accepts noncanonical row order, reports byte offsets from the
pool base, rejects aliased/out-of-range row spans, and rejects any upper-
triangle source write. The deterministic six-scalar fixture verifies all 21
lower-domain cells through a permuted row mapping with zero readback error.

Authentic `FUN_007b3ed0` sample production and the fixed-step
generated-contribution→`FUN_007ba570` export join remain separate gates.


## Phase 626 generated BODY export join

The native physics library now connects the prepared contribution generator to
the existing retail export primitive in the provider-absent builtin layout.

`generate_and_export_fun_007bc680_body()` executes the Phase 624 prepared
`FUN_007bc680` BODY contribution, materializes its lower matrix through the
Phase 625 `FUN_007bb8d0` row-index storage, then supplies the resulting
`BODY+0x150/+0x154` payloads directly to Phase 612 `FUN_007ba570`.

The exact retail audit at `SHIFT.exe.c:818768` confirms that
`FUN_007ba570` linearly adds `BODY+0xa4` vector doubles and
`BODY+0xa8` matrix doubles; it performs no additional row-pointer remap.

Phase 626 therefore requires canonical builtin row indices `row*N` and N²
matrix storage. Provider-present and noncanonical layouts remain fail-closed.
The deterministic six-scalar mixed fixture exports the exact Phase 624 vector
and Phase 625 canonical matrix pool with zero error.

The remaining fixed-step gate is replacing prepared SBEX contribution evidence
with this generated contribution while retaining the existing exact SBEX/SBFR
matrix/RHS verification boundary. Authentic `FUN_007b3ed0` sampled-state
production remains independent.
