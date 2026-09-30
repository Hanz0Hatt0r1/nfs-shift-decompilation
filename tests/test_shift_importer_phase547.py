from shift_importer import build_parser


def test_phase547_cli_exposes_scene_placement_commands():
    parser = build_parser()

    scene = parser.parse_args([
        "sgb-scene-placement",
        "placement-join.json",
        "scene-placement.json",
    ])
    assert scene.cmd == "sgb-scene-placement"
    assert scene.input == "placement-join.json"
    assert scene.output == "scene-placement.json"

    attach = parser.parse_args([
        "attach-scene-placement",
        "render-binding.json",
        "scene-placement.json",
        "render-with-placement.json",
    ])
    assert attach.cmd == "attach-scene-placement"
    assert attach.render_binding == "render-binding.json"
    assert attach.scene_placement == "scene-placement.json"
    assert attach.output == "render-with-placement.json"
