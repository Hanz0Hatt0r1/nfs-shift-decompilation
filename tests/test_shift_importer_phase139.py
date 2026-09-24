from shift_importer import build_parser


def test_phase139_cli_still_builds_after_shader_gate_extension():
    parser=build_parser()
    args=parser.parse_args(['bmw-paint-contract','binding.json','contract.json'])
    assert args.cmd == 'bmw-paint-contract'
    assert args.input == 'binding.json'
    assert args.output == 'contract.json'