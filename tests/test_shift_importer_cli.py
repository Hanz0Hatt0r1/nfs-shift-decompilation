import shift_importer


def test_importer_registers_native_submission_gate():
    parser = shift_importer.build_parser()
    args = parser.parse_args([
        "validate-native-submission",
        "command.json",
        "gate.json",
    ])
    assert args.fn is shift_importer.cmd_validate_native_submission
    assert args.input == "command.json"
    assert args.output == "gate.json"
