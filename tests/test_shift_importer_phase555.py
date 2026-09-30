from shift_importer import build_parser


def test_phase555_cli_exposes_sgb_meshinst_runtime():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-meshinst-runtime",
        "tracks/test/banner.imb",
        "meshinst-runtime.json",
        "--instance-count",
        "4",
    ])
    assert args.cmd == "sgb-meshinst-runtime"
    assert args.resource == "tracks/test/banner.imb"
    assert args.output == "meshinst-runtime.json"
    assert args.instance_count == 4
