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


def test_resource_identity_fields_separate_decoded_and_raw_hashes():
    class Entry:
        type = 2
        index = 7
        compressed_size = 5
        uncompressed_size = 3

    class FakeBFF:
        def raw_payload(self, entry):
            assert entry.index == 7
            return b"packed"

    result = shift_importer._resource_identity_fields(
        FakeBFF(),
        Entry(),
        b"decoded",
    )
    import hashlib
    assert result["sha256"] == hashlib.sha256(b"decoded").hexdigest()
    assert result["decoded_sha256"] == result["sha256"]
    assert result["raw_sha256"] == hashlib.sha256(b"packed").hexdigest()
    assert result["type"] == 2
    assert result["entry_index"] == 7
    assert result["compressed_size"] == 5
    assert result["uncompressed_size"] == 3
