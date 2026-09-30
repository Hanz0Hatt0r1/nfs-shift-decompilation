from shift_importer import build_parser


def test_phase549_cli_exposes_sgb_multimatrix_world():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-multimatrix-world",
        "sgb-runtime.json",
        "multimatrix-world.json",
    ])
    assert args.cmd == "sgb-multimatrix-world"
    assert args.input == "sgb-runtime.json"
    assert args.output == "multimatrix-world.json"
