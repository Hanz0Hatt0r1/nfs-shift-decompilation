from shift_importer import build_parser


def test_phase144_cli_exposes_real_bmw_material_extractor():
    parser=build_parser()
    args=parser.parse_args([
        'bmw-material-from-bff',
        'BMW_M3_E36.bff',
        'material-binding.json',
        '--supplemental-bff',
        'BMW_M3_E36_Cockpit.bff',
    ])
    assert args.cmd=='bmw-material-from-bff'
    assert args.input=='BMW_M3_E36.bff'
    assert args.output=='material-binding.json'
    assert args.supplemental_bff==['BMW_M3_E36_Cockpit.bff']