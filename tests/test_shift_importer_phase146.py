from shift_importer import build_parser


def test_phase146_cli_exposes_bmw_meb_evidence_parity():
    parser=build_parser()
    args=parser.parse_args([
        "bmw-meb-evidence-parity",
        "meb-evidence.json",
        "bmw-golden.json",
        "parity.json",
    ])
    assert args.cmd=="bmw-meb-evidence-parity"
    assert args.evidence=="meb-evidence.json"
    assert args.golden=="bmw-golden.json"
    assert args.output=="parity.json"
