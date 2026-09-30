from shift_importer import build_parser


def test_phase547_cli_exposes_sgb_scene_placement():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-scene-placement",
        "placement-join.json",
        "scene-placement.json",
    ])
    assert args.cmd == "sgb-scene-placement"
    assert args.input == "placement-join.json"
    assert args.output == "scene-placement.json"
