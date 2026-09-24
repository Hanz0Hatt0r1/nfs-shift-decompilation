import shift_importer


def test_render_bff_evidence_cli_is_registered():
    parser = shift_importer.build_parser()
    args = parser.parse_args([
        "render-bff-evidence",
        "BMW_M3_E36.bff",
        "RENDER.bff",
        "out.json",
    ])
    assert args.cmd == "render-bff-evidence"
    assert callable(args.fn)
    assert args.supplemental_bff == []


def test_render_bff_evidence_cli_accepts_multiple_supplemental_archives():
    parser = shift_importer.build_parser()
    args = parser.parse_args([
        "render-bff-evidence",
        "BMW_M3_E36.bff",
        "RENDER.bff",
        "out.json",
        "--supplemental-bff",
        "BMW_M3_E36_Cockpit.bff",
        "--supplemental-bff",
        "other.bff",
    ])
    assert args.supplemental_bff == ["BMW_M3_E36_Cockpit.bff", "other.bff"]
