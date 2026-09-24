from shift_importer import build_parser


def test_phase125_cli_exposes_bmw_runtime_shader_join():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-shader-join",
        "material.json",
        "runtime.json",
        "join.json",
    ])
    assert args.cmd == "bmw-runtime-shader-join"
    assert args.material_slice == "material.json"
    assert args.runtime_report == "runtime.json"
    assert args.output == "join.json"

def test_phase125_cli_exposes_bmw_runtime_shader_join():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-shader-join",
        "material.json",
        "runtime.json",
        "join.json",
    ])
    assert args.cmd == "bmw-runtime-shader-join"
    assert args.material_slice == "material.json"
    assert args.runtime_report == "runtime.json"
    assert args.output == "join.json"
