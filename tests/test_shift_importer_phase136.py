from shift_importer import build_parser


def test_phase136_cli_exposes_bmw_paint_contract():
    parser=build_parser()
    args=parser.parse_args(['bmw-paint-contract','binding.json','contract.json'])
    assert args.cmd == 'bmw-paint-contract'
    assert args.input == 'binding.json'
    assert args.output == 'contract.json'