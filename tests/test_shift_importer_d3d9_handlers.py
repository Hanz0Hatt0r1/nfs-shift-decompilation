import shift_importer


def test_d3d9_evidence_cli_handlers_are_registered():
    parser = shift_importer.build_parser()
    handlers = [
        "source-d3d9-declaration-lifecycle",
        "source-d3d9-declaration-sentinel-evidence",
        "source-d3d9-declaration-count-evidence",
        "source-d3d9-declaration-create-evidence",
        "source-d3d9-render-api-boundary",
        "source-d3d9-api-bind-evidence",
    ]

    for command in handlers:
        action = parser.parse_args(
            [command, "SHIFT.exe.c", "out.json"]
        )
        assert action.cmd == command
        assert callable(action.fn)
