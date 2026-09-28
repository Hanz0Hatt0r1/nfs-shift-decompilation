import json
from pathlib import Path

import tools.build_vehicle_physics_handoff as tool


def test_parser_requires_bff_and_output():
    parser = tool.build_parser()
    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("bff and output arguments were not required")


def test_cli_prints_summary_and_delegates(monkeypatch, tmp_path: Path, capsys):
    bff = tmp_path / "vehicle.bff"
    out = tmp_path / "out"
    bff.write_bytes(b"fixture")

    monkeypatch.setattr(
        tool,
        "build_vehicle_physics_handoff",
        lambda bff_path, output_dir, *, strict=False: {
            "format": "SHIFT.VehiclePhysicsPrePhysXHandoff/1",
            "status": "ready",
            "ready": True,
            "summary": {
                "solver_scalar_count": 40,
                "same_dimension_provider_candidates": [0],
            },
            "errors": [],
        },
    )

    result = tool.main([str(bff), str(out)])

    assert result == 0
    text = capsys.readouterr().out
    assert "solver_scalar_count" in text
    assert "same_dimension_provider_candidates" in text
