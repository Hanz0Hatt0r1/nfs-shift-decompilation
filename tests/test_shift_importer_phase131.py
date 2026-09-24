from shift_importer import build_parser


def test_phase131_cli_exposes_bmw_vertex_input_parity():
    parser=build_parser()
    args=parser.parse_args([
        'bmw-vertex-input-parity', 'material.json', 'runtime.json', 'vertex.json',
        '--usage-map', 'usage.json'
    ])
    assert args.cmd == 'bmw-vertex-input-parity'
    assert args.material_slice == 'material.json'
    assert args.runtime_report == 'runtime.json'
    assert args.output == 'vertex.json'
    assert args.usage_map == 'usage.json'