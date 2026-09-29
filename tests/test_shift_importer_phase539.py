from shift_importer import build_parser


def test_phase539_cli_exposes_runtime_shader_target_match():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-shader-target-match",
        "targets.json",
        "runtime.json",
        "match.json",
    ])
    assert args.cmd == "bmw-runtime-shader-target-match"
    assert args.target_set == "targets.json"
    assert args.runtime_report == "runtime.json"
    assert args.output == "match.json"
