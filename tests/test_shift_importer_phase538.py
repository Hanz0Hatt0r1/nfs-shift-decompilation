from shift_importer import build_parser


def test_phase538_cli_exposes_runtime_shader_target_set():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-shader-target-set",
        "admission.json",
        "targets.json",
    ])
    assert args.cmd == "bmw-runtime-shader-target-set"
    assert args.admission == "admission.json"
    assert args.output == "targets.json"
