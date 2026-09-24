from shift_importer import build_parser


def test_phase143_cli_exposes_source_bmw_identity():
    parser=build_parser()
    args=parser.parse_args(['source-bmw-vehicle-identity','SHIFT.exe.c','identity.json'])
    assert args.cmd=='source-bmw-vehicle-identity'
    assert args.input=='SHIFT.exe.c'
    assert args.output=='identity.json'