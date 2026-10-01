from shift_importer import build_parser


def test_phase553_cli_exposes_sgb_render_binding_bridge():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-render-binding-bridge",
        "scene-render-admission.json",
        "out/ir",
        "scene-render-binding.json",
    ])
    assert args.cmd == "sgb-render-binding-bridge"
    assert args.admission == "scene-render-admission.json"
    assert args.ir_root == "out/ir"
    assert args.output == "scene-render-binding.json"
    assert args.runtime_shader_admission is None


def test_phase576_cli_accepts_runtime_shader_admission():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-render-binding-bridge",
        "scene-render-admission.json",
        "out/ir",
        "scene-render-binding.json",
        "--runtime-shader-admission",
        "runtime-shader-admission.json",
    ])
    assert (
        args.runtime_shader_admission
        == "runtime-shader-admission.json"
    )


def test_phase578_cli_accepts_native_scene_bundle_command():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-bundle",
        "scene-render-binding.json",
        "native-scene-bundle.json",
    ])
    assert args.scene_bridge == "scene-render-binding.json"
    assert args.output == "native-scene-bundle.json"
    assert args.fn.__name__ == "cmd_native_scene_bundle"


def test_phase579_cli_accepts_neutral_vulkan_draw_bundle_command():
    parser = build_parser()
    args = parser.parse_args([
        "vulkan-draw-bundle",
        "render-command.json",
        "neutral-mesh.json",
        "out/vulkan-draw",
        "--submesh-index",
        "2",
    ])
    assert args.render_command == "render-command.json"
    assert args.mesh == "neutral-mesh.json"
    assert args.output_dir == "out/vulkan-draw"
    assert args.command_index == 0
    assert args.submesh_index == 2
    assert args.allow_static is False
    assert args.external_textures is None
    assert args.fn.__name__ == "cmd_vulkan_draw_bundle"


def test_phase588_cli_accepts_external_sampler2d_snapshot_map():
    parser = build_parser()
    args = parser.parse_args([
        "vulkan-draw-bundle",
        "render-command.json",
        "neutral-mesh.json",
        "out/vulkan-draw",
        "--external-textures",
        "external-textures.json",
    ])
    assert args.external_textures == "external-textures.json"
    assert args.fn.__name__ == "cmd_vulkan_draw_bundle"


def test_phase580_cli_accepts_native_scene_vulkan_set_command():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-vulkan-set",
        "native-scene-bundle.json",
        "scene-render-binding.json",
        "out/ir",
        "out/native-scene-vulkan",
    ])
    assert args.native_scene_bundle == "native-scene-bundle.json"
    assert args.scene_bridge == "scene-render-binding.json"
    assert args.ir_root == "out/ir"
    assert args.output_dir == "out/native-scene-vulkan"
    assert args.environment_cube_dds is None
    assert args.external_sampler_snapshots is None
    assert args.fn.__name__ == "cmd_native_scene_vulkan_set"


def test_phase591_cli_accepts_scene_instance_transform_match():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-instance-transform-match",
        "native-scene-bundle.json",
        "silverstone-runtime-attribution.json",
        "out/scene-instance-transform-match.json",
    ])

    assert args.native_scene_bundle == "native-scene-bundle.json"
    assert args.capture_pipeline == (
        "silverstone-runtime-attribution.json"
    )
    assert args.output == "out/scene-instance-transform-match.json"
    assert args.fn.__name__ == (
        "cmd_native_scene_instance_transform_match"
    )


def test_phase590_cli_accepts_capture_to_scene_snapshot_adapter():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-external-capture",
        "native-scene-bundle.json",
        "scene-render-binding.json",
        "silverstone-runtime-attribution.json",
        "out/scene-external-capture.json",
        "--capture-root",
        "capture",
        "--snapshot-output",
        "out/scene-external-snapshots.json",
        "--cube-snapshot-output",
        "out/scene-external-cube-snapshots.json",
        "--instance-transform-match",
        "out/scene-instance-transform-match.json",
    ])

    assert args.native_scene_bundle == "native-scene-bundle.json"
    assert args.scene_bridge == "scene-render-binding.json"
    assert args.capture_pipeline == (
        "silverstone-runtime-attribution.json"
    )
    assert args.capture_root == "capture"
    assert args.snapshot_output == (
        "out/scene-external-snapshots.json"
    )
    assert args.cube_snapshot_output == (
        "out/scene-external-cube-snapshots.json"
    )
    assert args.instance_transform_match == (
        "out/scene-instance-transform-match.json"
    )
    assert args.fn.__name__ == (
        "cmd_native_scene_external_capture"
    )


def test_phase592_cli_accepts_scene_external_sampler_cube_snapshots():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-vulkan-set",
        "native-scene-bundle.json",
        "scene-render-binding.json",
        "out/ir",
        "out/native-scene-vulkan",
        "--external-sampler-cube-snapshots",
        "scene-external-cube-snapshots.json",
    ])

    assert args.external_sampler_cube_snapshots == (
        "scene-external-cube-snapshots.json"
    )
    assert args.fn.__name__ == "cmd_native_scene_vulkan_set"


def test_phase589_cli_accepts_scene_external_sampler_snapshots():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-vulkan-set",
        "native-scene-bundle.json",
        "scene-render-binding.json",
        "out/ir",
        "out/native-scene-vulkan",
        "--external-sampler-snapshots",
        "scene-external-snapshots.json",
    ])

    assert args.external_sampler_snapshots == (
        "scene-external-snapshots.json"
    )
    assert args.fn.__name__ == "cmd_native_scene_vulkan_set"


def test_phase581_cli_accepts_vulkan_world_transform_packet_command():
    parser = build_parser()
    args = parser.parse_args([
        "vulkan-world-transform-packet",
        "render-command.json",
        "world_transform.svwt",
    ])
    assert args.input == "render-command.json"
    assert args.output == "world_transform.svwt"
    assert args.fn.__name__ == "cmd_vulkan_world_transform_packet"


def test_phase585_cli_accepts_native_scene_vulkan_prepare_command():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-vulkan-prepare",
        "out/native-scene-vulkan",
        "--validator",
        "glslangValidator",
        "--output",
        "out/native-scene-vulkan/prepare.json",
    ])
    assert args.bundle_set_dir == "out/native-scene-vulkan"
    assert args.validator == "glslangValidator"
    assert args.output == "out/native-scene-vulkan/prepare.json"
    assert args.fn.__name__ == "cmd_native_scene_vulkan_prepare"


def test_phase594_cli_accepts_multimatrix_runtime_root_solve():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-multimatrix-root-solve",
        "owner.json",
        "2",
        "observed-world.json",
        "root-solve.json",
        "--tolerance",
        "1e-6",
    ])

    assert args.owner == "owner.json"
    assert args.selected_slot == 2
    assert args.observed_world == "observed-world.json"
    assert args.output == "root-solve.json"
    assert args.tolerance == 1.0e-6
    assert args.fn.__name__ == "cmd_sgb_multimatrix_root_solve"


def test_phase595_cli_accepts_runtime_object_candidate_join():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-runtime-object-candidate-join",
        "scene-placement.json",
        "object-handoffs.json",
        "runtime-capture.json",
        "out/ir",
        "runtime-object-candidates.json",
    ])

    assert args.scene_placement == "scene-placement.json"
    assert args.object_handoffs == "object-handoffs.json"
    assert args.capture_pipeline == "runtime-capture.json"
    assert args.ir_root == "out/ir"
    assert args.output == "runtime-object-candidates.json"
    assert args.fn.__name__ == (
        "cmd_sgb_runtime_object_candidate_join"
    )


def test_phase596_cli_accepts_multimatrix_root_consensus():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-multimatrix-root-consensus",
        "sgb-runtime.json",
        "runtime-object-candidates.json",
        "runtime-capture.json",
        "root-consensus.json",
    ])

    assert args.sgb_runtime == "sgb-runtime.json"
    assert args.candidate_join == "runtime-object-candidates.json"
    assert args.capture_pipeline == "runtime-capture.json"
    assert args.output == "root-consensus.json"
    assert args.fn.__name__ == "cmd_sgb_multimatrix_root_consensus"


def test_phase597_cli_applies_multimatrix_root_consensus_to_handoffs():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-object-render-handoff",
        "sgb-runtime.json",
        "object-handoffs.json",
        "--root-consensus",
        "root-consensus.json",
    ])

    assert args.input == "sgb-runtime.json"
    assert args.output == "object-handoffs.json"
    assert args.root_consensus == "root-consensus.json"
    assert args.fn.__name__ == "cmd_sgb_object_render_handoff"


def test_phase598_cli_accepts_multimatrix_runtime_coverage():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-multimatrix-runtime-coverage",
        "scene-placement.json",
        "sgb-runtime.json",
        "runtime-capture.json",
        "out/ir",
        "matrix-coverage.json",
    ])

    assert args.scene_placement == "scene-placement.json"
    assert args.sgb_runtime == "sgb-runtime.json"
    assert args.capture_pipeline == "runtime-capture.json"
    assert args.ir_root == "out/ir"
    assert args.output == "matrix-coverage.json"
    assert args.fn.__name__ == "cmd_sgb_multimatrix_runtime_coverage"


def test_phase600_cli_accepts_native_camera_state_bridge():
    parser = build_parser()
    args = parser.parse_args([
        "native-camera-state-bridge",
        "camera-snapshot.json",
        "native-camera.json",
        "--transition",
        "camera-swap.json",
        "--transition",
        "camera-complete.json",
    ])

    assert args.snapshot == "camera-snapshot.json"
    assert args.output == "native-camera.json"
    assert args.transition == [
        "camera-swap.json",
        "camera-complete.json",
    ]
    assert args.fn.__name__ == "cmd_native_camera_state_bridge"


def test_phase606_cli_accepts_native_builtin_solver_frame():
    parser = build_parser()
    args = parser.parse_args([
        "native-builtin-solver-frame",
        "solver-frame-input.json",
        "out/native-solver-frame",
    ])

    assert args.input == "solver-frame-input.json"
    assert args.output_dir == "out/native-solver-frame"
    assert args.fn.__name__ == "cmd_native_builtin_solver_frame"


def test_phase607_cli_accepts_runtime_participant_evidence_join():
    parser = build_parser()
    args = parser.parse_args([
        "native-participant-runtime-evidence",
        "participant-boundary.json",
        "participant-observation.json",
        "participant-runtime-evidence.json",
    ])

    assert args.boundary == "participant-boundary.json"
    assert args.observation == "participant-observation.json"
    assert args.output == "participant-runtime-evidence.json"
    assert args.fn.__name__ == "cmd_native_participant_runtime_evidence"


def test_phase609_cli_accepts_native_post_solve_projection():
    parser = build_parser()
    args = parser.parse_args([
        "native-post-solve-projection",
        "post-solve-input.json",
        "out/native-post-solve",
    ])

    assert args.input == "post-solve-input.json"
    assert args.output_dir == "out/native-post-solve"
    assert args.fn.__name__ == "cmd_native_post_solve_projection"
