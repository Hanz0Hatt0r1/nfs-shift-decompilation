from shift_importer import build_parser


def test_phase126_cli_exposes_bmw_runtime_shader_join():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-shader-join", "material.json", "runtime.json", "join.json"
    ])
    assert args.cmd == "bmw-runtime-shader-join"
    assert args.material_slice == "material.json"
    assert args.runtime_report == "runtime.json"
    assert args.output == "join.json"


def test_phase126_cli_exposes_bmw_runtime_parity():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-parity", "material.json", "runtime.json", "parity.json",
        "--usage-map", "usage.json",
    ])
    assert args.cmd == "bmw-runtime-parity"
    assert args.material_slice == "material.json"
    assert args.runtime_report == "runtime.json"
    assert args.output == "parity.json"
    assert args.usage_map == "usage.json"