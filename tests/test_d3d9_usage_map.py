from d3d9_usage_map import build_d3d9_usage_map


def test_usage_map_requires_all_nine_ordinals():
    report = build_d3d9_usage_map({
        "format": "SHIFT.PEImageEvidence/1",
        "decoded_tables": {
            "usage": [{"ordinal": i, "value": 100 + i} for i in range(9)]
        },
        "conclusions": {"usage_table_status": "decoded"},
    })
    assert report["ready"] is True
    assert report["entry_count"] == 9
    assert report["usage_map"]["6"] == 106
    assert report["evidence_policy"]["allows_inference"] is False


def test_usage_map_blocks_missing_ordinal():
    report = build_d3d9_usage_map({
        "format": "SHIFT.PEImageEvidence/1",
        "decoded_tables": {
            "usage": [{"ordinal": i, "value": 100 + i} for i in range(9) if i != 6]
        },
        "conclusions": {"usage_table_status": "partial"},
    })
    assert report["ready"] is False
    assert report["status"] == "partial"
    assert "usage-map:missing-ordinal:6" in report["blocking_reasons"]


def test_usage_map_rejects_wrong_pe_evidence_format():
    try:
        build_d3d9_usage_map({"format": "SHIFT.D3D9RuntimeBindingEvidence/1"})
    except ValueError as exc:
        assert "SHIFT.PEImageEvidence/1" in str(exc)
    else:
        raise AssertionError("wrong evidence format was accepted")


def test_usage_map_cli_writes_ready_map(tmp_path):
    import json
    import subprocess
    import sys

    source = tmp_path / "pe.json"
    output = tmp_path / "usage.json"
    source.write_text(
        json.dumps({
            "format": "SHIFT.PEImageEvidence/1",
            "decoded_tables": {
                "usage": [{"ordinal": i, "value": 200 + i} for i in range(9)]
            },
            "conclusions": {"usage_table_status": "decoded"},
        }),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "d3d9_usage_map.py", str(source), str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ready"] is True
    assert report["usage_map"]["6"] == 206


def test_usage_map_cli_returns_blocked_for_partial_map(tmp_path):
    import json
    import subprocess
    import sys

    source = tmp_path / "pe.json"
    output = tmp_path / "usage.json"
    source.write_text(
        json.dumps({
            "format": "SHIFT.PEImageEvidence/1",
            "decoded_tables": {
                "usage": [{"ordinal": 0, "value": 200}]
            },
        }),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "d3d9_usage_map.py", str(source), str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ready"] is False
    assert "usage-map:missing-ordinal:6" in report["blocking_reasons"]
