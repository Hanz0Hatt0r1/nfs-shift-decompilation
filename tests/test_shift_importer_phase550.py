from shift_importer import build_parser


def test_phase550_cli_exposes_multimatrix_evaluation():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-multimatrix-evaluation",
        "sgb-runtime.json",
        "multimatrix.json",
        "--base-matrices",
        "bases.json",
    ])
    assert args.cmd == "sgb-multimatrix-evaluation"
    assert args.input == "sgb-runtime.json"
    assert args.output == "multimatrix.json"
    assert args.base_matrices == "bases.json"
