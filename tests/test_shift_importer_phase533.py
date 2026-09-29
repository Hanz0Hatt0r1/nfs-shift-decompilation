from shift_importer import build_parser


def test_phase533_cli_wires_retail_body_material_admission():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-body-material-admission",
        "BMW_M3_E36.bff",
        "out/bmw-body-admission",
        "--supplemental-bff",
        "BMW_M3_E36_Cockpit.bff",
        "--supplemental-bff",
        "RENDER.bff",
        "--vulkan-output-dir",
        "out/bmw-body-vulkan",
    ])

    assert args.cmd == "bmw-body-material-admission"
    assert args.input == "BMW_M3_E36.bff"
    assert args.output_dir == "out/bmw-body-admission"
    assert args.golden.endswith(
        "bmw_m3_e36_kit00_body_loda.golden.json"
    )
    assert args.supplemental_bff == [
        "BMW_M3_E36_Cockpit.bff",
        "RENDER.bff",
    ]
    assert args.primitive_index is None
    assert args.vulkan_output_dir == "out/bmw-body-vulkan"


def test_phase533_cli_accepts_explicit_primitive_subset():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-body-material-admission",
        "BMW_M3_E36.bff",
        "out",
        "--primitive-index",
        "1",
        "--primitive-index",
        "3",
    ])
    assert args.primitive_index == [1, 3]
