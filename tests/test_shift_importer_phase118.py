from shift_importer import build_parser


def test_phase118_cli_exposes_bmw_golden_gate():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-golden-gate",
        "golden.json",
        "packet.json",
        "--material-binding",
        "material.json",
    ])
    assert args.cmd == "bmw-golden-gate"
    assert args.golden == "golden.json"
    assert args.draw_packet == "packet.json"
    assert args.material_binding == "material.json"


def test_phase118_cli_exposes_d3d9_runtime_trace():
    parser = build_parser()
    args = parser.parse_args([
        "d3d9-runtime-trace",
        "capture.jsonl",
        "runtime.json",
        "--meb-resource",
        "body.json",
        "--usage-map",
        "usage.json",
    ])
    assert args.cmd == "d3d9-runtime-trace"
    assert args.trace == "capture.jsonl"
    assert args.output == "runtime.json"
    assert args.meb_resource == "body.json"
    assert args.usage_map == "usage.json"