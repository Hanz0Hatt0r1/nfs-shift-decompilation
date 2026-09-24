from shift_importer import build_parser


def test_phase147_cli_exposes_bmw_material_slice_golden_gate():
    parser=build_parser()
    args=parser.parse_args([
        "bmw-material-slice-golden-gate",
        "golden.json",
        "slice.json",
        "gate.json",
        "--primitive-index",
        "1",
    ])
    assert args.cmd=="bmw-material-slice-golden-gate"
    assert args.golden=="golden.json"
    assert args.slice=="slice.json"
    assert args.output=="gate.json"
    assert args.primitive_index==1
