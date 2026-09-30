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
    assert args.fn.__name__ == "cmd_native_scene_vulkan_set"
