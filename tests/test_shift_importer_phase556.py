from shift_importer import build_parser


def test_phase556_cli_exposes_imb_binary_schema():
    parser = build_parser()
    args = parser.parse_args([
        "imb-binary-schema",
        "mesh.imb",
        "imb-schema.json",
        "--header-offset",
        "0x40",
        "--has-bone-block",
    ])
    assert args.cmd == "imb-binary-schema"
    assert args.input == "mesh.imb"
    assert args.output == "imb-schema.json"
    assert args.header_offset == 0x40
    assert args.has_bone_block is True
