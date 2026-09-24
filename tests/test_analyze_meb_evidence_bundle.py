import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.analyze_meb_evidence_bundle import analyze_bundle


def _row(resource_id: str, properties: list[tuple[str, list[int]]]) -> dict:
    descriptors = []
    color_reports = {}
    found = []
    for pid, words in properties:
        found.append(pid)
        descriptors.append({
            "id": pid,
            "offset": 100,
            "words": words,
            "raw_hex": b"".join(int(x).to_bytes(4, "little") for x in words).hex(),
        })
        color_reports[pid] = {
            "source": {
                "descriptor_range_status": "observed",
                "payload_range_status": "observed",
                "decoded_stream_matches_payload_status": "observed",
                "payload_range": {"length": 4},
            }
        }
    return {
        "id": resource_id,
        "source": {"archive": "test.bff"},
        "color_properties_found": found,
        "mesh": {"property_descriptors": descriptors},
        "color_reports": color_reports,
    }


def _bundle(path: Path, rows: list[dict]) -> None:
    summary = {
        "format": "SHIFT.MEBEvidenceBundle/1",
        "collector_version": "115.0",
        "created_utc": "20260924T000000Z",
        "source_evidence": {"supplied": True},
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("summary.json", json.dumps(summary))
        zf.writestr("resources.jsonl", "".join(json.dumps(row) + "\n" for row in rows))
        zf.writestr("errors.json", "[]")


def test_analyzer_proves_uniform_460_and_reports_missing_461(tmp_path):
    bundle = tmp_path / "evidence.zip"
    _bundle(bundle, [
        _row("a", [("460", [4, 6, 0])]),
        _row("b", [("460", [4, 6, 0])]),
    ])

    report = analyze_bundle(bundle)

    assert report["scan"]["resources"] == 2
    assert report["properties"]["460"]["exact_expected_descriptors"] == 2
    assert report["properties"]["460"]["decoded_stream_matches_payload"] == 2
    assert report["conclusions"]["color0_460_exact_descriptor_corpus"] == "proven"
    assert report["conclusions"]["color1_461_corpus_presence"] == "not-observed"


def test_analyzer_does_not_hide_mixed_descriptor_values(tmp_path):
    bundle = tmp_path / "mixed.zip"
    _bundle(bundle, [
        _row("a", [("460", [4, 6, 0])]),
        _row("b", [("460", [8, 6, 0])]),
    ])

    report = analyze_bundle(bundle)

    assert report["properties"]["460"]["exact_expected_descriptors"] == 1
    assert report["properties"]["460"]["descriptor_exactness"] == "mixed"
    assert report["conclusions"]["color0_460_exact_descriptor_corpus"] == "not-proven"
    assert len(report["examples"]["descriptor_mismatch"]) == 1
