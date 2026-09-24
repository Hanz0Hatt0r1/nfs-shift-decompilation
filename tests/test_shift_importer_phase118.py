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

def test_phase120_cli_exposes_bmw_render_slice():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-render-slice",
        "golden.json",
        "render-bindings.json",
        "slice.json",
    ])
    assert args.cmd == "bmw-render-slice"
    assert args.golden == "golden.json"
    assert args.render_binding == "render-bindings.json"
    assert args.output == "slice.json"


def test_phase122_cli_exposes_bmw_reference_render():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-reference-render", "slice.json", "mesh.json", "body.ppm",
        "--width", "64", "--height", "32", "--shader-reference",
        "--texture-json", "texture.json",
    ])
    assert args.cmd == "bmw-reference-render"
    assert args.slice == "slice.json"
    assert args.mesh == "mesh.json"
    assert args.output == "body.ppm"
    assert args.width == 64
    assert args.height == 32
    assert args.shader_reference is True
    assert args.texture_json == "texture.json"
