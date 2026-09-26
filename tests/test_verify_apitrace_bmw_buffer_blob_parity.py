from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import verify_apitrace_bmw_buffer_blob_parity as parity


def test_direct_blob_parity_matches_by_size(tmp_path):
    expected = tmp_path / "expected"
    expected.mkdir()
    sizes = [269800, 300, 12588, 14772, 1224, 1152, 168]
    (expected / "vertex_buffer.meb-order.bin").write_bytes(b"V" * sizes[0])
    for i, size in enumerate(sizes[1:]):
        (expected / f"index_buffer_{i:02d}.uint16.bin").write_bytes(bytes([i]) * size)

    payload = tmp_path / "payloads"
    payload.mkdir()
    records = []
    for i, size in enumerate(sizes):
        name = f"{i}.bin"
        (payload / name).write_bytes(
            (b"V" if i == 0 else bytes([i - 1])) * size
        )
        records.append({
            "buffer_kind": "vertex_buffer" if i == 0 else "index_buffer",
            "blob_size": size,
            "full_buffer_candidate": True,
            "payload_path": str(payload / name),
        })

    evidence = {
        "source": {"geometry_report": str(tmp_path / "geometry.json")},
        "buffers": records,
    }
    result = parity.build_report(evidence, expected)
    assert result["ready"] is True
    assert result["matches"] == 7


def test_direct_blob_parity_resolves_relative_payloads_from_evidence_file(tmp_path):
    expected = tmp_path / "expected"
    expected.mkdir()
    sizes = [269800, 300, 12588, 14772, 1224, 1152, 168]
    (expected / "vertex_buffer.meb-order.bin").write_bytes(b"V" * sizes[0])
    for i, size in enumerate(sizes[1:]):
        (expected / f"index_buffer_{i:02d}.uint16.bin").write_bytes(bytes([i]) * size)

    evidence_dir = tmp_path / "evidence"
    payload = evidence_dir / "buffer_payloads"
    payload.mkdir(parents=True)
    records = []
    for i, size in enumerate(sizes):
        name = f"{i}.bin"
        (payload / name).write_bytes(
            (b"V" if i == 0 else bytes([i - 1])) * size
        )
        records.append({
            "buffer_kind": "vertex_buffer" if i == 0 else "index_buffer",
            "blob_size": size,
            "full_buffer_candidate": True,
            "payload_path": str(Path("buffer_payloads") / name),
        })

    evidence = {
        "source": {"geometry_report": "/unrelated/path/geometry.json"},
        "buffers": records,
    }
    result = parity.build_report(evidence, expected, evidence_dir)
    assert result["ready"] is True
    assert result["matches"] == 7
