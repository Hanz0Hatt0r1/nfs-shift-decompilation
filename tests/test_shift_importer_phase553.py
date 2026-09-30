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
    assert args.external_texture_snapshots is None
    assert args.fn.__name__ == "cmd_native_scene_vulkan_set"


def test_phase589_cli_accepts_scene_external_texture_snapshot_set():
    parser = build_parser()
    args = parser.parse_args([
        "native-scene-vulkan-set",
        "native-scene-bundle.json",
        "scene-render-binding.json",
        "out/ir",
        "out/native-scene-vulkan",
        "--external-texture-snapshots",
        "external-snapshots.json",
    ])
    assert args.external_texture_snapshots == "external-snapshots.json"
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
