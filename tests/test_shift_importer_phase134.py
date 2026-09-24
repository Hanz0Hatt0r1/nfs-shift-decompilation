from shift_importer import build_parser


def test_phase134_cli_exposes_capture_schema_validator():
    parser=build_parser()
    args=parser.parse_args(['validate-d3d9-capture','trace.jsonl','schema.json'])
    assert args.cmd == 'validate-d3d9-capture'
    assert args.input == 'trace.jsonl'
    assert args.output == 'schema.json'