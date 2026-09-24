from shift_importer import build_parser


def test_phase151_cli_exposes_bmw_bff_intake():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-bff-intake",
        "BMW_M3_E36.bff",
        "bff-intake.json",
    ])
    assert args.cmd == "bmw-bff-intake"
    assert args.input == "BMW_M3_E36.bff"
    assert args.output == "bff-intake.json"
