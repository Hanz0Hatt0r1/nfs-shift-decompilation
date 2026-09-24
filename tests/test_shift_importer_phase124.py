from shift_importer import build_parser


def test_phase124_cli_exposes_source_shader_lifecycle():
    parser = build_parser()
    args = parser.parse_args([
        "source-d3d9-shader-lifecycle", "SHIFT.exe.c", "shader-lifecycle.json",
    ])
    assert args.cmd == "source-d3d9-shader-lifecycle"
    assert args.input == "SHIFT.exe.c"
    assert args.output == "shader-lifecycle.json"