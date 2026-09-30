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


def test_phase577_cli_exposes_silverstone_native_scene_bundle():
    parser = build_parser()
    args = parser.parse_args([
        "silverstone-native-scene-bundle",
        "scene-render-binding.json",
        "out/ir",
        "out/silverstone-native",
        "--environment-cube",
        "environment-cube.json",
        "--prepare",
        "--validator",
        "glslangValidator",
    ])

    assert args.bridge == "scene-render-binding.json"
    assert args.ir_root == "out/ir"
    assert args.output_dir == "out/silverstone-native"
    assert args.environment_cube == "environment-cube.json"
    assert args.prepare is True
    assert args.validator == "glslangValidator"
