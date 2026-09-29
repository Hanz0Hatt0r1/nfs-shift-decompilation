from shift_importer import build_parser


def test_phase540_cli_exposes_raw_capture_shader_prefilter():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-raw-capture-shader-prefilter",
        "targets.json",
        "shift_d3d9_capture.jsonl",
        "prefilter.json",
    ])
    assert args.cmd == "bmw-raw-capture-shader-prefilter"
    assert args.target_set == "targets.json"
    assert args.capture_jsonl == "shift_d3d9_capture.jsonl"
    assert args.output == "prefilter.json"
