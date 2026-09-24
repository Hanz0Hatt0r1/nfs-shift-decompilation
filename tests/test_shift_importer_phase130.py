from shift_importer import build_parser


def test_phase130_cli_exposes_bmw_runtime_draw_correlation():
    parser=build_parser()
    args=parser.parse_args([
        'bmw-runtime-draw-correlation', 'material.json', 'runtime.json', 'draw.json'
    ])
    assert args.cmd == 'bmw-runtime-draw-correlation'
    assert args.material_slice == 'material.json'
    assert args.runtime_report == 'runtime.json'
    assert args.output == 'draw.json'