from shift_importer import build_parser


def test_phase548_cli_exposes_sgb_object_render_handoff():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-object-render-handoff",
        "sgb-runtime.json",
        "object-render-handoff.json",
    ])
    assert args.cmd == "sgb-object-render-handoff"
    assert args.input == "sgb-runtime.json"
    assert args.output == "object-render-handoff.json"
