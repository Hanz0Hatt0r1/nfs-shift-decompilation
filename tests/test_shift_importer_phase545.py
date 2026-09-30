from shift_importer import build_parser


def test_phase545_cli_exposes_sgb_placement_join():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-placement-join",
        "sgb-runtime.json",
        "placement.json",
    ])
    assert args.cmd == "sgb-placement-join"
    assert args.input == "sgb-runtime.json"
    assert args.output == "placement.json"
