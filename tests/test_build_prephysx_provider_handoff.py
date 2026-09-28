import json
from pathlib import Path

import tools.build_prephysx_provider_handoff as tool


def test_parser_requires_input():
    parser = tool.build_parser()
    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("input argument was not required")


def test_cli_writes_handoff_manifest(monkeypatch, tmp_path: Path, capsys):
    source = tmp_path / "sdf_report.json"
    output = tmp_path / "handoff.json"
    source.write_text(json.dumps({"records": []}), encoding="utf-8")

    monkeypatch.setattr(
        tool,
        "build_prephysx_provider_handoff_contract",
        lambda report: {
            "format": "SHIFT.PrePhysXProviderHandoffRuntime/1",
            "status": "ready",
            "ready": True,
            "selection": {
                "solver_scalar_count": 40,
                "same_dimension_candidates": [0],
                "generic_fallback_available": True,
            },
            "errors": [],
        },
    )

    result = tool.main([str(source), "-o", str(output)])

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.PrePhysXProviderHandoffRuntime/1"
    assert payload["selection"]["same_dimension_candidates"] == [0]
    assert "solver_scalar_count" in capsys.readouterr().out
