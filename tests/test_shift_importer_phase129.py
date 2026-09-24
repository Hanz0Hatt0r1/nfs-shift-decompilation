from shift_importer import build_parser


def test_phase129_cli_exposes_runtime_trace_integrity_inputs():
    parser = build_parser()
    args = parser.parse_args([
        'source-d3d9-shader-constant-bind', 'SHIFT.exe.c', 'constants.json'
    ])
    assert args.cmd == 'source-d3d9-shader-constant-bind'
    assert args.input == 'SHIFT.exe.c'
    assert args.output == 'constants.json'