from pathlib import Path


def test_native_runtime_contract():
    cmake = Path("native_runtime/CMakeLists.txt").read_text(encoding="utf-8")
    readme = Path("native_runtime/README.md").read_text(encoding="utf-8")
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "project(shift_native_runtime" in cmake
    assert "PkgConfig::XCB" in cmake
    assert "Vulkan::Vulkan" in cmake
    assert "shift_ir" in cmake
    assert "VK_KHR_XCB_SURFACE_EXTENSION_NAME" in source
    assert "SHIFT.NativeRuntimeBootstrap/1" in source
    assert "SHIFT.NativeRuntimeFrameLoop/1" in source
    assert "offline-only" in readme
    assert "EA services" in readme
    assert "DRM" in readme


def test_native_runtime_consumes_bmw_bundle_geometry():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    shader = Path("native_runtime/shaders/runtime.vert").read_text(encoding="utf-8")

    assert "SHIFT.BMWVulkanBundle/1" in source
    assert "SHIFT.NativeSubmissionGate/1" in source
    assert "out_first_index = geometry.first_index" in source
    assert "first_index, 0, 0" in source
    assert "layout(location = 0) in vec3 inPosition;" in shader
    assert "inNormal" not in shader

def test_native_runtime_has_fixed_clock_and_input_layer():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    assert "XCB_EVENT_MASK_KEY_RELEASE" in source
    assert "struct InputState" in source
    assert "constexpr double kFixedDt = 1.0 / 60.0;" in source
    assert "SHIFT.NativeRuntimeInput/1" in source
    assert "simulation_steps" in source

def test_native_runtime_bundle_executes_material_interface():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "struct BundleAssets" in source
    assert "SHIFT.BMWVulkanInterfaceGate/1" in source
    assert "SHIFT.VulkanBundleSPIRV/1" in source
    assert "bundle.vertex_shader_path" in source
    assert "bundle.fragment_shader_path" in source
    assert "create_material_resources" in source
    assert "upload_material_resources" in source
    assert "VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER" in source
    assert "VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "load_bundle_cull_mode" in source
    assert "SHIFT.MaterialCullState/1" in source
    assert "SHIFT.MaterialPipelineState/1" in source
    assert "load_bundle_pipeline_state" in source
    assert "BundlePipelineState" in source
    assert "bundle.pipeline_state" in source
    assert "geometry.vertex_bytes.empty()" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "if (material_mode)" in source

def test_native_runtime_state_boundary_is_evidence_backed():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(encoding="utf-8")
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert 'SHIFT.NativeRuntimeState/1' in header
    assert "CameraBufferRuntime" in header
    assert "active_index = 0" in header
    assert "update_in_progress" in header
    assert "VehicleControlIntent" in header
    assert "PhysicsTickBoundary" in header
    assert "fixed_dt = 1.0 / 60.0" in header
    assert "participant_ready = false" in header
    assert "participant_index = -1" in header
    assert 'runtime_state.hpp' in source
    assert "native_state.fixed_step(intent)" in source
    assert "state_layer" in source
    assert "SHIFT.NativeRuntimeState/1" in source

def test_native_runtime_accepts_bmw_physics_manifest():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/linux-vulkan.yml").read_text(encoding="utf-8")

    assert "SHIFT.BMWM3VehiclePhysicsResourceManifest/1" in source
    assert "--physics-manifest" in source
    assert "load_physics_manifest" in source
    assert "scalar_count != 40u" in source
    assert "evidence/bmw_m3_vehicle_physics_manifest.json" in workflow
    assert "physics_workspace_scalars" in source

def test_phase602_native_runtime_admits_structural_participant_boundary():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(
        encoding="utf-8"
    )
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "participant_contract_ready = false" in header
    assert "participant_registry_ready = false" in header
    assert "selector_context_separate = false" in header
    assert "registry_slot_stride = 0" in header
    assert "participant_descriptor_type = 0" in header
    assert "participant_ready = false" in header
    assert "participant_index = -1" in header
    assert "participant_mode = -1" in header

    assert '"--participant-boundary"' in source
    assert "args.participant_boundary = value" in source
    assert "load_participant_boundary" in source
    assert "SHIFT.NativePhysicsParticipantBoundary/1" in source
    assert "DAT_00c109e0" in source
    assert "DAT_00bbc600" in source
    assert "slot_stride != 0x1fa0u" in source
    assert "descriptor_type != 3u" in source
    assert "participant boundary overclaims runtime instance" in source
    assert "\\\"physics_participant_contract_ready\\\":" in source
    assert "\\\"physics_participant_registry_ready\\\":" in source
    assert "\\\"physics_selector_context_separate\\\":" in source
    assert "\\\"physics_registry_slot_stride\\\":" in source
    assert "\\\"physics_participant_descriptor_type\\\":" in source


def test_native_camera_defaults_match_recovered_view_constructor():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(encoding="utf-8")

    assert "0x3F490FDBu" in header
    assert "0x3FAAAAABu" in header
    assert "0x3DCCCCCDu" in header
    assert "0x443B8000u" in header
    assert "manager_mode = 0" in header
    assert "buffer_sub_index = -1" in header
    assert "camera_id = -1" in header
    assert "active_group = -1" in header
    assert "group_restore_value = -1" in header
    assert "buffer_count = 2" in header

def test_phase599_native_camera_snapshot_and_swap_boundary():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(
        encoding="utf-8"
    )
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "struct CameraManagerSnapshot" in header
    assert "camera_source_token" in header
    assert "snapshot_active() const" in header
    assert "last_snapshot = snapshot_active()" in header
    assert "++snapshot_count" in header
    assert "++native_update_count" in header
    assert "begin_camera_update()" in header
    assert "complete_camera_update()" in header
    assert "native-fixed-step-non-retail-timing" in source
    assert "\\\"camera_snapshot_count\\\":" in source
    assert "\\\"camera_native_updates\\\":" in source
    assert "\\\"camera_update_in_progress\\\":" in source




def test_phase600_native_runtime_accepts_camera_evidence_input():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(
        encoding="utf-8"
    )
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "apply_evidence_snapshot" in header
    assert "state.camera_source_token = 0" in header
    assert "const CameraState& active() const" in header
    assert '"--camera-state"' in source
    assert "SHIFT.NativeCameraStateBridge/1" in source
    assert "load_camera_state_bridge" in source
    assert "native_active_index" in source
    assert "native_update_in_progress" in source
    assert "native_manager_mode" in source
    assert "native_group_restore_value" in source
    assert '\\"camera_state_bridge_loaded\\": ' in source
    assert '\\"camera_manager_mode\\": ' in source
    assert '\\"camera_active_group\\": ' in source


def test_native_index_draw_count_respects_first_index():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "geometry.indices.size() - out_first_index" in source
    assert "index_count == 0" in source


def test_native_runtime_uses_per_swapchain_depth_buffers():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "std::vector<Image> depth_images" in source
    assert "create_depth_resources()" in source
    assert "VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT" in source
    assert "VK_IMAGE_ASPECT_DEPTH_BIT" in source
    assert "VK_FORMAT_D32_SFLOAT depth attachment unsupported" in source
    assert "pDepthStencilAttachment = &depth_ref" in source
    assert "depth_state.depthTestEnable =" in source
    assert "material_pipeline_state.depth_test_enable" in source
    assert "depth_state.depthWriteEnable =" in source
    assert "material_pipeline_state.depth_write_enable" in source
    assert "material_pipeline_state.depth_compare_op" in source
    assert "clear[1].depthStencil.depth = 1.0f" in source
    assert '\\"depth_test\\": true' in source


def test_native_runtime_consumes_prepared_multi_draw_bundle_sets():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "struct MaterialDraw" in source
    assert "std::vector<MaterialDraw> material_draws" in source
    assert "load_bundle_set_paths" in source
    assert '"--bundle-set"' in source
    assert "SHIFT.BMWVulkanBundleSetPrepare/1" in source
    assert "bundle set prepare gate is missing or not ready" in source
    assert "for (const MaterialDraw& draw : material_draws)" in source
    assert "draw.pipeline_layout" in source
    assert "draw.vertex_constants" in source
    assert "draw.texture_images" in source
    assert '\\"material_draws\\": ' in source
    assert '\\"bundle_set_mode\\": ' in source



def test_native_runtime_maps_bundle_cull_sidecar_to_vulkan():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    assert "VK_CULL_MODE_NONE" in source
    assert "VK_CULL_MODE_BACK_BIT" in source
    assert "VK_CULL_MODE_FRONT_BIT" in source
    assert "raster.cullMode =" in source



def test_native_runtime_executes_bundle_depth_and_blend_state():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    assert "material_pipeline_state.depth_test_enable" in source
    assert "material_pipeline_state.depth_write_enable" in source
    assert "material_pipeline_state.depth_compare_op" in source
    assert "material_pipeline_state.blend_enable" in source
    assert "material_pipeline_state.src_color_blend_factor" in source
    assert "material_pipeline_state.dst_color_blend_factor" in source
    assert "material_pipeline_state.color_blend_op" in source
    assert "material_pipeline_state.src_alpha_blend_factor" in source
    assert "material_pipeline_state.dst_alpha_blend_factor" in source
    assert "material_pipeline_state.alpha_blend_op" in source


def test_native_runtime_accepts_svgp_v3_semantics_and_legacy_packets():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    assert "struct LegacyGeometryAttribute" in source
    assert "uint32_t property_id;" in source
    assert "header.version != 3" in source
    assert "legacy.location == 0u ? 200u : 0u" in source
    assert "invalid version-1 SVGP geometry attribute" in source
    assert "position->property_id != 200u" in source


def test_phase586_native_runtime_accepts_neutral_scene_sets():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert '"--scene-set"' in source
    assert "SHIFT.NativeSceneVulkanSet/1" in source
    assert "SHIFT.NativeSceneVulkanSetPrepare/1" in source
    assert "SHIFT.VulkanDrawBundle/1" in source
    assert "SHIFT.VulkanDrawBundlePrepare/1" in source
    assert "SHIFT.VulkanInterfaceGate/1" in source
    assert "apply_bundle_world_transform" in source
    assert "SVWT affine linear transform is singular" in source
    assert "SVWT NORMAL property 220 must be FLOAT3" in source
    assert "SVWT TANGENT property 240 must be FLOAT3" in source
    assert "SVWT TANGENT2 property 250 must be FLOAT3" in source
    assert "scene_set_mode" in source
    assert "world_transform_draws" in source
    assert "affine_world_transform_draws" in source
    assert "world_transform_applied = true" in source
    assert 'world_transform_mode != "translation"' in source


def test_phase586_keeps_bmw_bundle_set_abi():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "SHIFT.BMWVulkanBundleSet/1" in source
    assert "SHIFT.BMWVulkanBundleSetPrepare/1" in source
    assert "SHIFT.BMWVulkanInterfaceGate/1" in source
    assert '"--bundle-set"' in source


def test_phase601_native_input_script_reaches_physics_tick_boundary():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path("native_runtime/src/runtime_state.hpp").read_text(
        encoding="utf-8"
    )

    assert "SHIFT.NativeRuntimeInputScript/1" in source
    assert '"--input-script"' in source
    assert "load_input_script" in source
    assert "steps must be contiguous from zero" in source
    assert "--frames must equal native input script step count" in (
        source
        + Path("native_runtime/src/runtime_loop_policy.hpp").read_text(encoding="utf-8")
    )
    assert "input_script_mode" in source
    assert '"script" : "keyboard"' in source
    assert "vehicle_control_throttle_steps" in source
    assert "vehicle_control_brake_steps" in source
    assert "vehicle_control_steer_left_steps" in source
    assert "vehicle_control_steer_right_steps" in source
    assert "vehicle_control_neutral_steps" in source

    assert "throttle_steps" in header
    assert "brake_steps" in header
    assert "steer_left_steps" in header
    assert "steer_right_steps" in header
    assert "neutral_input_steps" in header
    assert "if (input.throttle) ++throttle_steps" in header
    assert "if (input.brake) ++brake_steps" in header


def test_phase602_native_participant_loader_requires_all_source_contracts_ready():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert '"registry_contract_ready\\": true"' in source
    assert '"participant_gate_ready\\": true"' in source
    assert '"participant_process_ready\\": true"' in source
    assert '"selector_context_ready\\": true"' in source
    assert (
        "native physics participant source contracts are not all ready"
        in source
    )


def test_phase603_keeps_registry_index_and_selector_ordinal_distinct():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path("native_runtime/src/runtime_state.hpp").read_text(
        encoding="utf-8"
    )

    assert "participant_identity_join_proven = false" in header
    assert "participant_registry_index = -1" in header
    assert "selector_ordinal = -1" in header
    assert "participant_process_state = -1" in header
    assert "participant_topology_steps" in header
    assert "participant_ready_steps" in header
    assert "participant_unresolved_steps" in header

    assert '"registry_index_source_offset"' in source
    assert '"selector_candidate_ready_offset"' in source
    assert '"registry_selector_identity_join_proven"' in source
    assert '"participant_registry_index"' in source
    assert '"selector_ordinal"' in source
    assert '"participant_process_state"' in source
    assert "physics_participant_identity_join_proven" in source
    assert "physics_participant_registry_index" in source
    assert "physics_selector_ordinal" in source
    assert "physics_participant_process_state" in source
    assert "physics_participant_topology_steps" in source
    assert "physics_participant_ready_steps" in source
    assert "physics_participant_unresolved_steps" in source


def test_phase607_native_runtime_admits_runtime_participant_identity_evidence():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "SHIFT.NativePhysicsParticipantRuntimeEvidence/1" in source
    assert "const bool structural_boundary" in source
    assert "const bool runtime_evidence" in source
    assert "participant_instance_ready" in source
    assert "registry_index_equals_selector_ordinal" in source
    assert "same_participant_pointer_proven" in source
    assert "manager_registry_identity_observed" in source
    assert "igphasevehicle_selection_observed" in source
    assert (
        "physics.participant_ready =\n"
        "        runtime_evidence && participant_instance_ready;"
        in source
    )
    assert "registry_index < 0" in source
    assert "selector_ordinal < 0" in source
    assert "process_state == -1" in source


def test_phase608_fixed_step_solver_frame_requires_ready_runtime_evidence():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert '#include "shift_builtin_solver_frame.hpp"' in source
    assert '"--solver-frame"' in source
    assert "load_prepared_builtin_solver_frame" in source
    assert "execute_prepared_builtin_solver_frame" in source
    assert "--solver-frame requires --physics-manifest" in source
    assert "--solver-frame requires --participant-boundary" in source
    assert "solver frame requires ready runtime participant evidence" in source
    assert "solver frame scalar count does not match physics workspace" in source
    assert "solver frame lost ready participant identity" in source
    assert "physics_solver_frame_loaded" in source
    assert "physics_solver_frame_scalar_count" in source
    assert "physics_solver_frame_steps" in source
    assert "physics_solver_frame_max_oracle_error" in source
    assert "physics_solver_provider_present" in source
    assert "physics_solver_post_solve_body_state_applied" in source
    assert '"physics_solver_provider_present\\": false' in source
    assert "physics_solver_post_solve_body_state_applied" in source
    assert '"physics_solver_persistent_vehicle_state_applied\\": false' in source


def test_phase610_fixed_step_solver_joins_post_solve_projection():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert '#include "shift_post_solve_projection.hpp"' in source
    assert '"--post-solve-projection"' in source
    assert "load_prepared_post_solve_body_projection" in source
    assert "execute_post_solve_body_projection_with_solution" in source
    assert "--post-solve-projection requires --solver-frame" in source
    assert (
        "post-solve projection scalar count does not match solver frame"
        in source
    )
    assert (
        "post-solve projection body count does not match physics workspace"
        in source
    )
    assert (
        "post-solve projection constraint counts do not match physics workspace"
        in source
    )
    assert "physics_post_solve_projection_loaded" in source
    assert "physics_post_solve_projection_steps" in source
    assert "physics_post_solve_projection_max_solver_join_error" in source
    assert "physics_post_solve_projection_max_oracle_error" in source
    assert "physics_solver_persistent_vehicle_state_applied" in source


def test_phase611_persistent_post_solve_body_state_is_explicit_and_non_vehicle():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path(
        "native_runtime/include/shift_post_solve_projection.hpp"
    ).read_text(encoding="utf-8")

    assert '"--persist-post-solve-body-state"' in source
    assert (
        "--persist-post-solve-body-state requires --post-solve-projection"
        in source
    )
    assert "execute_post_solve_body_projection_with_state" in source
    assert "persistent_post_solve_bodies" in source
    assert "physics_post_solve_persistent_body_state_enabled" in source
    assert "physics_post_solve_persistent_body_state_steps" in source
    assert "physics_post_solve_projection_max_delta_error" in source
    assert (
        "physics_solver_persistent_body_accumulator_state_applied"
        in source
    )
    assert '"physics_solver_persistent_vehicle_state_applied\\": false' in source
    assert "execute_post_solve_body_projection_with_state" in header
    assert "max_delta_error" in header


def test_phase615_fixed_step_solver_requires_body_export_join_when_supplied():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path(
        "native_runtime/include/shift_body_export_solver_join.hpp"
    ).read_text(encoding="utf-8")

    assert '#include "shift_body_export_solver_join.hpp"' in source
    assert '#include "shift_body_solver_export_frame.hpp"' in source
    assert '"--body-solver-export-frame"' in source
    assert (
        "--body-solver-export-frame requires --solver-frame"
        in source
    )
    assert "load_prepared_body_solver_export_frame" in source
    assert "verify_body_export_matches_builtin_solver_frame" in source
    assert "BODY solver export scalar count does not match solver frame" in source
    assert "physics_body_solver_export_frame_loaded" in source
    assert "physics_body_solver_export_join_steps" in source
    assert "physics_body_solver_export_max_rhs_join_error" in source
    assert "physics_body_solver_export_max_matrix_join_error" in source
    assert "verify_body_export_matches_builtin_solver_frame" in header


def test_phase628_fixed_step_solver_accepts_generated_body_frame():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path(
        "native_runtime/include/shift_generated_body_constraint_frame.hpp"
    ).read_text(encoding="utf-8")

    assert '#include "shift_generated_body_constraint_frame.hpp"' in source
    assert '"--generated-body-constraint-frame"' in source
    assert (
        "--generated-body-constraint-frame requires --solver-frame"
        in source
    )
    assert "--generated-body-constraint-frame cannot be combined" in source
    assert "with --body-solver-export-frame" in source
    assert "load_prepared_generated_body_constraint_frame" in source
    assert (
        "verify_generated_body_constraint_frame_matches_builtin_solver_frame"
        in source
    )
    assert (
        "generated BODY scalar count does not match solver frame"
        in source
    )
    assert (
        "generated BODY count does not match physics workspace"
        in source
    )
    assert (
        "generated BODY sample counts do not match physics workspace"
        in source
    )
    assert "physics_generated_body_constraint_frame_loaded" in source
    assert "physics_generated_body_constraint_join_steps" in source
    assert (
        "physics_generated_body_constraint_native_generation_steps"
        in source
    )
    assert "physics_generated_body_constraint_max_rhs_join_error" in source
    assert "physics_generated_body_constraint_max_matrix_join_error" in source
    assert (
        "physics_generated_body_constraint_values_stored_in_packet"
        in source
    )
    assert (
        "verify_generated_body_constraint_frame_matches_builtin_solver_frame"
        in header
    )


def test_phase631_fixed_step_generated_body_refreshes_from_constraint_relations():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    header = Path(
        "native_runtime/include/shift_constraint_sample_relation_frame.hpp"
    ).read_text(encoding="utf-8")

    assert '#include "shift_constraint_sample_relation_frame.hpp"' in source
    assert '"--constraint-sample-relation-frame"' in source
    assert "--constraint-sample-relation-frame requires " in source
    assert "--generated-body-constraint-frame" in source
    assert "load_prepared_constraint_sample_relation_frame" in source
    assert "refresh_generated_body_constraint_frame" in source
    assert "constraint relation BODY count does not match " in source
    assert "constraint relation counts do not match " in source
    assert "refreshed generated BODY sample counts do not match " in source
    assert "constraint relation endpoint coverage" in source
    assert "physics_constraint_sample_relation_frame_loaded" in source
    assert "physics_constraint_sample_relation_joint_count" in source
    assert "physics_constraint_sample_relation_hinge_count" in source
    assert "physics_constraint_sample_relation_bar_count" in source
    assert "physics_constraint_sample_relation_refreshed_joint_samples" in source
    assert "physics_constraint_sample_relation_refreshed_hinge_samples" in source
    assert "physics_constraint_sample_relation_refreshed_bar_samples" in source
    assert "physics_constraint_sample_relation_refresh_steps" in source
    assert (
        "physics_constraint_sample_relation_values_stored_in_packet"
        in source
    )
    assert "PreparedConstraintSampleRelationFrame" in header
    assert "RefreshedGeneratedBodyConstraintFrame" in header


def test_phase632_fixed_step_joins_relation_reset_selection_to_solver_frame():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    reset_header = Path(
        "native_runtime/include/shift_constraint_relation_reset_frame.hpp"
    ).read_text(encoding="utf-8")

    assert '#include "shift_constraint_relation_reset_frame.hpp"' in source
    assert '"--constraint-relation-reset-frame"' in source
    assert "--constraint-relation-reset-frame requires " in source
    assert "--constraint-sample-relation-frame" in source
    assert "load_prepared_constraint_relation_reset_frame" in source
    assert "select_fun_007b3f40_reset_nodes" in source
    assert "verify_fun_007b3f40_reset_nodes_match" in source
    assert "execute_prepared_builtin_solver_frame(" in source
    assert "execute_prepared_builtin_solver_frame_with_reset_nodes" not in source
    assert "physics_solver_effective_reset_node_count" in source
    assert "physics_solver_frame_reset_nodes_consumed" in source
    assert "physics_constraint_relation_reset_frame_loaded" in source
    assert "physics_constraint_relation_reset_selected_joint_count" in source
    assert "physics_constraint_relation_reset_selected_hinge_count" in source
    assert "physics_constraint_relation_reset_selected_bar_count" in source
    assert "physics_constraint_relation_reset_call_count" in source
    assert "physics_constraint_relation_reset_node_count" in source
    assert "physics_constraint_relation_reset_matches_solver_frame" in source
    assert "physics_constraint_relation_reset_selection_steps" in source
    assert "physics_constraint_relation_reset_state_offset" in source
    assert "physics_constraint_relation_reset_tested_bit" in source
    assert "physics_constraint_relation_reset_nodes_stored_in_packet" in source

    assert "PreparedConstraintRelationResetFrame" in reset_header
    assert "ConstraintRelationResetSelectionResult" in reset_header
    assert "select_fun_007b3f40_reset_nodes" in reset_header
    assert "normalize_fun_007b3f40_reset_nodes" in reset_header
    assert "verify_fun_007b3f40_reset_nodes_match" in reset_header



def test_phase709_continuous_runtime_loop_is_explicit_and_non_retail():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    policy = Path("native_runtime/src/runtime_loop_policy.hpp").read_text(encoding="utf-8")
    cmake = Path("native_runtime/CMakeLists.txt").read_text(encoding="utf-8")

    assert '#include "runtime_loop_policy.hpp"' in source
    assert 'option == "--continuous"' in source
    assert "loop_policy.should_continue(quit, rendered)" in source
    assert "one-native-fixed-step-per-render-frame-non-retail" in source
    assert "--continuous cannot be combined with --input-script" in policy
    assert "frame_limit_enabled" in policy
    assert "shift_runtime_loop_policy_check" in cmake
    assert "NAME shift_runtime_loop_policy" in cmake
