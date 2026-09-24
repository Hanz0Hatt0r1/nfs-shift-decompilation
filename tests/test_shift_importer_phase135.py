from shift_importer import build_parser


def test_phase135_cli_exposes_render_command_constant_parity():
    parser=build_parser()
    args=parser.parse_args(['render-command-constant-parity','command.json','parity.json'])
    assert args.cmd == 'render-command-constant-parity'
    assert args.input == 'command.json'
    assert args.output == 'parity.json'