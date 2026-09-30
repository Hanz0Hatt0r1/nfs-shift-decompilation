from shift_importer import build_parser


def test_phase542_cli_exposes_runtime_register_filter():
    parser = build_parser()
    args = parser.parse_args([
        "bmw-runtime-register-filter",
        "admission.json",
        "runtime-witness.json",
        "register-filter.json",
    ])
    assert args.cmd == "bmw-runtime-register-filter"
    assert args.material_input == "admission.json"
    assert args.runtime_witness == "runtime-witness.json"
    assert args.output == "register-filter.json"
