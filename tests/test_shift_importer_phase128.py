from shift_importer import build_parser


def test_phase128_cli_exposes_bmw_runtime_golden_gate():
    parser = build_parser()
    args = parser.parse_args([
        'bmw-runtime-golden-gate', 'material.json', 'runtime.json', 'gate.json',
        '--usage-map', 'usage.json',
    ])
    assert args.cmd == 'bmw-runtime-golden-gate'
    assert args.material_slice == 'material.json'
    assert args.runtime_report == 'runtime.json'
    assert args.output == 'gate.json'
    assert args.usage_map == 'usage.json'