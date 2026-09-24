from shift_importer import build_parser


def test_phase147_cli_exposes_material_slice_golden_gate():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-material-slice-golden-gate",
        "bmw-golden.json",
        "bmw-slice.json",
        "slice-gate.json",
        "--primitive-index",
        "1",
    ])
    assert args.cmd == "bmw-material-slice-golden-gate"
    assert args.golden == "bmw-golden.json"
    assert args.slice == "bmw-slice.json"
    assert args.output == "slice-gate.json"
    assert args.primitive_index == 1
