from shift_importer import build_parser


def test_phase557_cli_defaults_to_automatic_imb_prefix():
    parser = build_parser()
    args = parser.parse_args([
        "imb-binary-schema",
        "mesh.imb",
        "imb-schema.json",
    ])
    assert args.cmd == "imb-binary-schema"
    assert args.header_offset is None
    assert args.has_bone_block is False
