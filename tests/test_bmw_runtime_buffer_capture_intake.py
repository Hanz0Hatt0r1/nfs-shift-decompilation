from pathlib import Path

from bmw_runtime_buffer_capture_intake import normalize_payload_paths


def test_normalize_payload_paths_resolves_relative_payloads(tmp_path: Path):
    events = [
        {"event": "buffer_payload", "payload_path": "vb.bin"},
        {"event": "buffer_payload", "payload_path": "nested/ib.bin"},
        {"event": "buffer_payload", "payload_path": str(tmp_path / "abs.bin")},
        {"event": "draw_indexed_primitive", "payload_path": "not-a-payload"},
    ]
    result = normalize_payload_paths(events, tmp_path / "payloads")
    assert result[0]["payload_path"] == str(tmp_path / "payloads" / "vb.bin")
    assert result[1]["payload_path"] == str(tmp_path / "payloads" / "nested" / "ib.bin")
    assert result[2]["payload_path"] == str(tmp_path / "abs.bin")
    assert result[3]["payload_path"] == "not-a-payload"


def test_normalize_payload_paths_preserves_missing_and_non_string_values(tmp_path: Path):
    events = [
        {"event": "buffer_payload"},
        {"event": "buffer_payload", "payload_path": None},
        {"event": "buffer_payload", "payload_path": 7},
    ]
    result = normalize_payload_paths(events, tmp_path)
    assert [row.get("payload_path") for row in result] == [None, None, 7]
