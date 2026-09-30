from shift_importer import build_parser


def test_phase552_cli_exposes_sgb_render_binding_admission():
    parser = build_parser()
    args = parser.parse_args([
        "sgb-render-binding-admission",
        "scene-placement.json",
        "object-handoffs.json",
        "scene-render-admission.json",
    ])
    assert args.cmd == "sgb-render-binding-admission"
    assert args.scene_placement == "scene-placement.json"
    assert args.object_handoffs == "object-handoffs.json"
    assert args.output == "scene-render-admission.json"
