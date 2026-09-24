from shift_importer import build_parser


def test_phase145_cli_exposes_real_material_slice():
    parser=build_parser()
    args=parser.parse_args([
        'bmw-real-material-slice',
        'BMW_M3_E36.bff',
        'bmw-golden.json',
        'bmw-material-slice.json',
        '--primitive-index','1',
        '--supplemental-bff','BMW_M3_E36_Cockpit.bff',
    ])
    assert args.cmd=='bmw-real-material-slice'
    assert args.input=='BMW_M3_E36.bff'
    assert args.golden=='bmw-golden.json'
    assert args.output=='bmw-material-slice.json'
    assert args.primitive_index==1
    assert args.supplemental_bff==['BMW_M3_E36_Cockpit.bff']