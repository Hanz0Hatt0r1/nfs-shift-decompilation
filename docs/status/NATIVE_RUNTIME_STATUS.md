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
7. Phase 709 removes the interactive INT32_MAX surrogate and adds an explicit native continuous-until-window-quit loop policy. Deterministic/scripted runs remain frame-bounded. The current continuous schedule is still one native fixed step per rendered frame and is explicitly non-retail; retail outer-update cadence/game-loop ownership remains evidence-gated.

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
records through runtime `relation+0x70 & 1`; Phase 604 does not infer that bit
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


## Phase 627 generated BODY constraint frame

The native physics path now has a contribution-free prepared input packet for
BODY contribution generation.

`SHIFT.NativeGeneratedBodyConstraintFramePacket/1` (GBCF) carries BODY
state, canonical builtin row indices and ordered JOINT/HINGE/BAR sample values.
It does not carry solver-vector/matrix contribution values.

The C++ loader independently parses and validates GBCF, then
`execute_prepared_generated_body_constraint_frame()` invokes the Phase 626
generation/export path for every BODY and accumulates the resulting global
matrix/RHS.

The deterministic six-scalar fixture reproduces the Phase 624/626 global
vector/matrix with zero error while reporting
`contribution_values_stored_in_packet=false`.

This remains downstream of authentic `FUN_007b3ed0` sample refresh.

## Phase 628 generated BODY fixed-step join

The native runtime now accepts `--generated-body-constraint-frame FILE.gbcf`
together with an admitted `--solver-frame`.

Before every builtin solve it independently regenerates the global matrix/RHS
through `FUN_007bc680 → FUN_007bb8d0 → FUN_007ba570` and requires exact
equality with the prepared SBFR before `FUN_007b2210` reset and
`FUN_007b0f20` solve. GBCF and prepared SBEX are mutually exclusive pre-solve
evidence sources.

Phase 628 fixed-step admission currently requires its synthetic GBCF sample
counts to match the workspace relation counts. Linux CI retains the nonzero
six-scalar Phase 627 oracle and the 11-BODY / 4-JOINT / 4-HINGE / 20-BAR /
40-scalar scheduler regression.

Phase 630 proves that this count equality is not the authentic ownership shape:
each retail top-level relation constructs two BODY-owned endpoint samples.
Phase 631 now admits CSRF on fixed steps and uses relation-aware cardinality in
that mode. The Phase 628 count equality remains only as a backward-compatible
prepared-fixture shortcut when CSRF is absent. Telemetry exposes generated
join/generation steps and maximum matrix/RHS join error.


## Phase 629 FUN_007b3ed0 constraint sample refresh

The native physics library now contains the source-backed numerical refresh
stage that retail executes immediately before per-BODY contribution assembly.

`refresh_fun_007b3ed0_constraints()` preserves the exact top-level array order
and record strides:

- JOINT relation records: stride 0xA0 → `FUN_007b2da0`;
- HINGE relation records: stride 0xA0 → `FUN_007b2de0`;
- BAR relation records: stride 0xB8 → `FUN_007b2f70`.

The implementation also ports both float-boundary frame transforms used by
retail: `FUN_007aefb0` and transposed-order `FUN_007af0a0`.

The refreshed outputs line up with the already-native Phase 617–624 sample
fields: JOINT +0x18 position, HINGE +0x48/+0x60 angular/linear rows, and BAR
+0x18 point plus shared normalized +0x40/+0x48/+0x50 direction.

`shift_runtime_constraint_sample_refresh_check` freezes nontrivial JOINT,
HINGE and BAR oracles, zero-length BAR behavior, non-finite rejection and the
JOINT→HINGE→BAR frame order at ≤1e-12 parity tolerance.

This phase deliberately does not claim a complete runtime refresh packet.
Top-level relation ownership/body-sample pointer transport, exact per-frame raw
inputs and GBCF regeneration remain the next integration boundary.


## Phase 630 constraint relation ownership and GBCF refresh join

`SHIFT.NativeConstraintSampleRelationFramePacket/1` (`CSRF`) now carries the
missing source-order relation ownership for the Phase 629 refresh stage.

Each JOINT/HINGE/BAR relation identifies exact positive and negative GBCF
`(body_index, sample_index)` endpoints. Direct `SHIFT.exe.c` audit confirms
that the +0x78/positive constructor call uses side flag 1 and the
+0x80/negative call uses side flag 0 for `FUN_007ba8b0`,
`FUN_007ba900` and `FUN_007ba990`.

The packet keeps only the raw local rows needed by `FUN_007b3ed0`; BODY
frames/positions, scalar bases, side flags, BAR side bias and generated
matrix/RHS values are not duplicated.

`refresh_generated_body_constraint_frame()` fails closed unless every
BODY-owned sample is covered exactly once, endpoint side identity matches the
retail constructor calls, paired scalar bases match and BAR endpoint bias
matches. It then runs the Phase 629 numerical kernels and writes refreshed
sample fields into a copied GBCF.

The native checker freezes the critical cardinality:

```text
1 relation → 2 BODY-owned endpoint samples
```

for JOINT, HINGE and BAR, and verifies duplicate/incomplete ownership,
side mismatch and scalar mismatch rejection.

Phase 630 does not yet load CSRF through `shift_runtime`. The next boundary is
fixed-step `CSRF → refreshed GBCF → FUN_007bc680/FUN_007bb8d0/FUN_007ba570`
execution with relation-aware endpoint cardinality.


## Phase 631 fixed-step constraint refresh

The native runtime now accepts `--constraint-sample-relation-frame FILE.csrf`
together with `--generated-body-constraint-frame FILE.gbcf`.

CSRF mode separates workspace relation cardinality from BODY-owned sample
cardinality. For the BMW structural shape, startup requires 4 JOINT, 4 HINGE
and 20 BAR relations, while the Phase 630 ownership join must cover 8 JOINT,
8 HINGE and 40 BAR endpoint samples.

On every admitted fixed step the runtime refreshes a copy of GBCF from CSRF
through `FUN_007b3ed0`, generates BODY contributions through
`FUN_007bc680 → FUN_007bb8d0 → FUN_007ba570`, and requires exact matrix/RHS
equality with SBFR before reset/solve.

The legacy GBCF-only Phase 628 path remains available and unchanged.

Linux Vulkan CI now carries a separate 11-BODY / 4-JOINT / 4-HINGE / 20-BAR
relation fixture with 8/8/40 endpoint samples and three fixed steps. Zero
prepared numerical state makes the pre-reset matrix/RHS exactly zero, so the
regression isolates ownership/cardinality/scheduling rather than inventing
vehicle dynamics.

Remaining blockers are authentic per-frame BODY/raw relation inputs, retail
reset-node selection, provider-present execution and persistent vehicle motion.


## Phase 632 relation-state reset selection

The provider-absent fixed-step path now independently reconstructs the rows
selected for `FUN_007b2210`.

Direct `SHIFT.exe.c` audit corrects an older project label:
`FUN_007b3f40` tests `relation+0x70 & 1`, not a BODY-owned sample
`+0x70` field. For a set bit it follows the positive endpoint pointer at
relation `+0x7c` and reads the scalar base from JOINT/BAR sample `+0x30`
or HINGE sample `+0x94`; reset widths are 3, 2 and 1 respectively.

`SHIFT.NativeConstraintRelationResetFramePacket/1` (CRRF) transports only
those source-order relation low bits. The native selector joins them to
GBCF+CSRF, validates endpoint identity, paired scalar bases and in-range
type-specific spans, and preserves the retail reset-call sequence. Repeated
calls are preserved and the selector does not impose an unsupported
whole-domain coverage constraint.

The exact call sequence is normalized to a reset-node set and must match
`SBFR.reset_nodes` before the solve is admitted. The same join is repeated on
every fixed step. SBFR remains the executed reset/solve oracle; CRRF proves
that the recovered retail relation state selects the same reset set rather
than replacing SBFR with a second oracle.

The deterministic six-scalar checker selects `[0,1,2,5]` for
JOINT=true/HINGE=false/BAR=true and rejects a mismatched SBFR reset set. Linux
CI also exercises the 11-BODY BMW structural shape with 4/4/20 relations,
40 selected reset calls/nodes and three successful fixed steps.

Remaining blockers are authentic per-frame BODY/raw-relation/reset-state
production, provider-present execution and persistent vehicle transform/motion
integration.


## Phase 633 relation-state bit0 mutation

The recovered runtime state writer immediately upstream of the Phase 632
selector is now ported as a separate source-backed native kernel.

The relation `+0x70` field is temporally reused: `FUN_007b1b60` first uses
it as the setup scalar base, and `FUN_007b3820` clears it after endpoint
sample allocation. Runtime `FUN_00757d2c` later mutates bit0 with set-only
`| 1` stores.

The zero-selector branch compares an unordered BODY pointer pair and sets bit0
on matching JOINT and HINGE relations. The nonzero-selector branch compares
one BODY pointer against both BAR endpoints and sets every matching BAR bit.
Phase 633 normalizes those pointer comparisons through the already-established
CSRF BODY-index identity domain.

The native checker covers reversed pair order, unmatched no-op behavior,
multiple BAR matches, self-endpoint BARs, preservation of pre-existing bits,
and fail-closed cardinality/domain errors.

This kernel is not scheduled by `shift_runtime`. Raw executable disassembly proves that `FUN_00757d20(index)` routes a
0..3 component index through `FUN_00469736`, which multiplies it by the
0xA80 component stride before `FUN_00757d2c`. The same setup resolves the slots to FL/FR/RL/RR wheel/spindle BODY names and
`rear_axle`. Retail event identity and dispatch timing remain unresolved, so
Phase 633 does not fabricate a fixed-step trigger.

Remaining blockers are authentic per-frame BODY/raw relation state, mutation
event provenance/timing, provider-present execution and persistent vehicle
transform/motion integration.

## Phase 634 named vehicle-slot relation-state dispatch

The Phase 633 mutation kernel now has a source-backed four-slot dispatcher for
the recovered vehicle component layout.

The dispatcher preserves the exact component geometry recovered from the retail
binary: base `0x400`, stride `0xA80`, slots 0..3 = FL/FR/RL/RR, wheel BODY
field `+0x420`, spindle BODY field `+0x424`, and named `rear_axle` BODY at
vehicle `+0x2E00`.

A `VehicleConstraintBodyIdentityMap` translates those names into the existing
CSRF BODY-index domain. For a caller-supplied spindle-presence state, the
dispatcher follows the exact `FUN_00757d2c` branch:

- spindle absent: JOINT/HINGE set-only mutation for
  `slot.wheel ↔ rear_axle`;
- spindle present: BAR set-only mutation for every relation touching
  `slot.spindle`.

All named BODY indices are checked against the CSRF BODY domain, and slots
outside 0..3 fail closed. The native checker executes all four component
offsets and verifies that a repeated BAR match does not clear or re-toggle an
already-set bit.

The dispatcher is still not referenced by `shift_runtime`. Phase 634 does
not assign the semantic identity of the triggering event, synthesize spindle
presence, or place the call on the fixed-step timeline. The next physics
evidence gate is a retail runtime observation of slot trigger, spindle
presence, and call ordering relative to the solver frame before CRRF mutation
can be scheduled.

Remaining blockers are authentic per-frame BODY/raw relation state, mutation
event provenance/timing, provider-present execution and persistent vehicle
transform/motion integration.

## Phase 635 retail relation-state mutation capture

The retail GDB SDF probe now includes a full-mode observer at
`FUN_00757d2c` (`0x00757d2c`) for the event provenance still missing from
the Phase 634 native dispatcher.

Raw retail disassembly fixes the observer ABI before the first instruction:
`ECX` is the vehicle pointer and `EAX` is `slot * 0xA80`. The probe records
the exact 0..3 FL/FR/RL/RR slot, component block, wheel/spindle/rear-axle BODY
pointers, spindle-presence branch and caller return address into
`relation_state_mutation_events.jsonl`.

A shared monotonic `runtime_event_sequence` is also attached to frame-entry,
builtin/provider solve, scalar-reset, post-solve and mutation observations.
This supplies a capture-time ordering key without assigning a Linux scheduler
event in advance.

The observer is intentionally omitted by `--provider-only`, because that mode
does not install the `FUN_007b3f40` frame-entry anchor. The launcher and
preflight contracts expect the new event stream only in full mode.

No native scheduler integration is enabled by this phase. The next gate is an
authentic retail capture followed by a fail-closed offline correlation of slot,
spindle presence, BODY identity and mutation ordering relative to the solver
frame.



## Phase 636 exact relation-state mutation caller classification

The Phase 635 observer already records the return address of every
`FUN_00757d2c` event. Phase 636 maps that value against the complete static
set of direct `FUN_00757d20` callers recovered from raw `SHIFT.exe`
disassembly.

There are exactly five direct calls:

- `0x76EE91 → 0x76EE96`: `FUN_0076ed60`, fixed slot 0 / FL;
- `0x76EEA3 → 0x76EEA8`: `FUN_0076ed60`, fixed slot 1 / FR;
- `0x76EEB5 → 0x76EEBA`: `FUN_0076ed60`, fixed slot 2 / RL;
- `0x76EEC7 → 0x76EECC`: `FUN_0076ed60`, fixed slot 3 / RR;
- `0x79A5BC → 0x79A5C1`: `FUN_0079a050`, slot-dynamic runtime threshold path.

`classify_relation_state_mutation_callsite` emits
`SHIFT.ConstraintRelationStateMutationCallsite/1`. The four setup callers
must agree with the captured slot, while the runtime caller accepts any valid
0..3 slot. Unknown return addresses remain in the raw capture stream but have
`callsite_ready=false`.

This closes static caller provenance without assigning native scheduling.
Authentic capture and offline timeline correlation are still required before
either caller family can authorize a native relation-state mutation.


## Phase 637 relation-state mutation timeline correlation

The Phase 635 shared `runtime_event_sequence` and Phase 636 exact caller
classification are now joined offline by
`relation_state_mutation_timeline_correlation_runtime.py`.

The correlator consumes the full-mode mutation JSONL stream plus captured
frame-entry, scalar-reset, builtin/provider-solve and post-solve artifacts.
Every mutation keeps its exact slot/branch/caller identity and receives the
nearest preceding/following timeline anchors.

Readiness fails closed on missing/empty mutation input, missing timeline
anchors, duplicate event sequences, invalid slots, unready Phase 636 callers,
missing frame entries, frame-entry sequence disagreement, or a no-frame event
that appears after frame processing has begun.

A setup mutation may be proven `before-first-frame-entry` only from strict
sequence ordering. A mutation carrying a frame index is accepted only when its
captured frame-entry sequence exactly matches that frame artifact and the
mutation occurs later in the shared sequence.

The output format is
`SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1`. It explicitly
keeps `native_scheduler_admission=false` and
`semantic_event_inference=false`. An authentic retail capture producing a
ready report remains the next evidence gate.


## Phase 638 automatic mutation-capture finalization

The explicit-PID full-mode launcher now runs the Phase 637 timeline correlator
automatically after the GDB session returns. A successful capture writes
`relation_state_mutation_timeline.json` and the launcher exits successfully
only when both the GDB return code and the correlation report are ready.

Provider-only mode deliberately skips this step because it does not install
the relation-state mutation observer or frame-entry anchor.

`probe_manifest.json` now records whether automatic timeline correlation is
applicable and the expected post-capture output path/format. The GDB probe and
launcher also add `src/physics` explicitly to their import path so embedded
GDB Python does not depend on project-root `sitecustomize.py` startup.

This removes a manual post-processing step without changing the evidence
boundary: missing or inconsistent runtime capture data still blocks Phase 637,
and no native mutation scheduling is authorized.


## Phase 639 portable SDF capture evidence bundle

Full-mode retail capture output can now be reduced to one deterministic
`sdf_capture_evidence.zip` carrying
`SHIFT.SDFRuntimeProbeEvidenceBundle/1`.

The archive includes only relation-mutation/timeline, frame-entry,
builtin/provider solve, scalar-reset/provider-reset-effect and post-solve
evidence. `SHIFT.exe`, `attach.gdb`, launcher manifest and preflight
manifest are excluded.

Every evidence file is recorded in `evidence_manifest.json` with byte size
and SHA-256. ZIP entry ordering, timestamps, permissions and storage mode are
fixed so identical capture bytes produce identical archive bytes.

Packaging readiness is kept separate from Phase 637 `capture_ready`; a
blocked timeline remains blocked even when it is packaged successfully for
inspection.

The full explicit-PID launcher now automatically creates the archive after
timeline finalization and reports archive path, size and SHA-256. Provider-only
mode remains unchanged. No native mutation scheduling is enabled.


## Phase 640 portable SDF evidence bundle verification

Portable Phase 639 capture archives are now independently verified as untrusted
input before use. `SHIFT.SDFRuntimeProbeEvidenceBundleVerification/1`
checks safe root-only names, duplicate/extra/missing entries, deterministic ZIP
metadata, manifest structure, every declared byte size/SHA-256 and exact
readiness agreement with the embedded Phase 637 timeline.

Integrity readiness, package readiness and capture readiness remain distinct.
A blocked retail capture can be structurally authentic without becoming
evidence-ready.

The full explicit-PID launcher now self-verifies the archive it creates and
requires successful verification before reporting success. No native mutation
scheduling is enabled.


## Phase 641 portable SDF evidence bundle replay

Verified Phase 639 archives can now be independently replayed through the
Phase 637 correlator. The verifier materializes only already-validated
root-level evidence files into a temporary directory, recomputes the complete
relation-state mutation timeline and requires exact equality with the embedded
timeline.

Phase 637 timeline artifacts no longer contain the host-local absolute
capture-directory path, making replay independent of extraction location and
preventing that local path from entering the portable archive.

The output format is
`SHIFT.SDFRuntimeProbeEvidenceBundleReplay/1`. Integrity/package/capture
readiness remain distinct; an exactly reproducible blocked retail capture stays
`evidence_ready=false`.

The full explicit-PID launcher now requires Phase 641 replay in addition to
GDB, Phase 637, Phase 639 and Phase 640. This is a reproducibility check rather
than an external authenticity signature, and it does not enable native
mutation scheduling.


## Phase 642 bounded full-mode GDB capture

The explicit-PID launcher now supports an optional positive
`--capture-frames N` budget in full mode. The Nth
`FUN_007b4110` post-solve breakpoint writes its normal snapshot and then
returns a terminal stop. The generated GDB command file subsequently executes
`detach` and `quit`, so detach is performed by normal GDB commands rather
than from inside the Python breakpoint callback.

Provider-only bounded capture is rejected because that mode omits the full
frame/post-solve anchor path. The probe manifest records the requested frame
budget and whether automatic detach is enabled.

If attachment occurs mid-frame, incomplete evidence remains fail-closed through
the existing Phase 637–641 correlation/verification/replay chain. No mutation
or scheduler semantics change in this phase.


## Phase 643 capture-session identity and hygiene

The retail SDF capture path now isolates each prepared run with a fresh
`SHIFT.SDFRuntimeProbeCaptureSession/1` identifier. Known generated evidence
from a previous run is removed only after the retail executable passes the
existing validation gate; unrelated files and host-local launcher inputs are
preserved.

The generated GDB command receives the same session id. All JSON/JSONL evidence
writers stamp `capture_session_id`, and the GDB command independently rejects a
directory that still contains stale generated capture artifacts. Reinstalling
the probe also resets the shared runtime-event sequence, scalar-reset counter and
last-frame state.

This does not alter solver, reset, provider or relation-mutation semantics and
does not authorize native scheduler admission.


## Phase 644 capture-session timeline correlation

The offline relation-mutation timeline now enforces the Phase 643 session
boundary. Once any contributing record carries `capture_session_id`, all
relation mutations and frame/reset/solve timeline anchors must carry the same
valid normalized 32-hex identity.

Mixed sessions, malformed ids and partially unstamped session-aware captures
fail closed. Historical captures with no session ids at all retain the previous
Phase 637 output shape for replay compatibility.

This strengthens capture provenance only. The timeline still exposes
`native_scheduler_admission=false` and does not infer mutation gameplay
semantics or fixed-step timing.


## Phase 645 portable evidence session identity

The portable SDF evidence archive now preserves the Phase 643/644 capture
session boundary. For a launcher-declared or otherwise session-stamped capture,
the bundle manifest carries one normalized session id and packaging fails if any
included JSON or JSONL record is missing, malformed or belongs to another
session.

The independent Phase 640 verifier repeats the session scan from ZIP payload
bytes and rejects a missing portable declaration or any per-record mismatch even
when the affected payload hash was recomputed. Phase 641 replay then recomputes
the same session-aware timeline.

Historical archives with no session declaration and no stamped evidence remain
legacy-compatible. Session identity is not a cryptographic signature and native
relation-state scheduler admission remains false.


## Phase 646 lightweight relation timeline capture

The retail capture launcher now exposes `--relation-timeline-only` for the
specific outstanding relation-mutation timing evidence. The GDB session installs
only relation mutation, frame-entry and post-solve anchors. A dedicated
metadata-only post-solve probe avoids scalar/RHS memory reads while preserving
the shared runtime-event sequence and bounded auto-detach behavior.

Provider solve/reset, scalar reset and builtin solver breakpoints are omitted in
this mode. The resulting evidence still passes through the Phase 637–645
timeline/session/bundle/verification/replay gates.

This is an overhead reduction only. Native scheduler admission remains false
until authentic retail evidence supports the missing timing decision.


## Phase 647 first-mutation stop capture

An authentic Phase 646 lightweight capture observed 600 frame-entry anchors and
600 post-solve anchors with one stable physics-system identity and a contiguous
runtime-event sequence from 1 through 1200, but no relation-state mutation.

The retail probe now supports `--stop-after-relation-mutation`. The relation
observer persists the complete event and sets a latch; the first following
post-solve anchor records its timeline position and only then returns a GDB
stop. The launcher detaches and quits automatically. A frame budget may remain active
as a fallback ceiling.

This strengthens evidence acquisition only. The 600-frame no-hit capture is
retained as negative runtime evidence and does not authorize native scheduler
admission.


## Phase 648 WineDbg early-launch capture

The Phase 647 negative long-window result left one acquisition gap: the four
fixed-slot setup callers of `FUN_00757d2c` can execute before a mid-session GDB
attach. The retail launcher now closes that control-flow race with
`--launch-under-winedbg`.

In this mode WineDbg creates the validated retail `SHIFT.exe` behind its GDB
proxy with `--no-start`. GDB connects over loopback with TCP auto-retry,
loads the normal generated `attach.gdb`, installs `sdf-probe`, and only then
executes its first `continue`. `probe_manifest.json` records
`startup_mode=winedbg-gdb-proxy`, the proxy port and the explicit
`debuggee-created-under-winedbg-and-held-before-first-continue` ordering.

A direct executable in the real game directory is required; ZIP input is
rejected for early launch rather than pretending an extracted standalone
`SHIFT.exe` is a valid runtime installation. WineDbg output is retained only
as the host-local `winedbg_gdb_proxy.log` diagnostic and is not added to the
portable evidence bundle.

The existing explicit-PID path remains available. Both paths feed the same
Phase 637–647 correlation, capture-session, deterministic bundle, independent
verification and replay gates. This phase changes capture start ordering only:
it does not claim that setup-time mutation occurs and does not enable native
relation-state scheduler admission.
