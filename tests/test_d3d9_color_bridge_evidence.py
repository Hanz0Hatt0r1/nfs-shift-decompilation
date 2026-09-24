import json
import subprocess
import sys
from pathlib import Path

from d3d9_color_bridge_evidence import analyze_meb_d3d9_color_bridge


def _source_report():
    return {
        "format": "SHIFT.D3D9SourceVertexEvidence/1",
        "source": {"sha256": "unused"},
        "observations": [
            {
                "id": "xml-colour-stream-field",
                "status": "observed",
                "function": "FUN_008587e0",
                "address": "0x008587E0",
                "source_line": 100,
                "detail": "Colour stream family",
            },
            {
                "id": "declaration-type-4-packed-color",
                "status": "observed",
                "function": "FUN_00854e70",
                "address": "0x00854E70",
                "source_line": 200,
                "detail": "type 4 calls packed color helper",
            },
            {
                "id": "xml-type-table-chain",
                "status": "observed",
                "function": "FUN_008587e0",
                "address": "0x008587E0",
                "source_line": 300,
                "detail": "XML Type resolves through type table",
            },
            {
                "id": "type-table-accessor",
                "status": "observed",
                "function": "FUN_00853c20",
                "address": "0x00853C20",
                "source_line": 400,
                "detail": "Type ordinal indexes table",
            },
        ],
        "linkage": {
            "xml_colour_to_type_4": {
                "status": "not-proven",
                "reason": "source table contents are opaque",
            },
            "meb_460_461_to_type_4": {
                "status": "not-proven",
                "reason": "no MEB bridge",
            },
        },
    }


def _meb(properties):
    return {
        "format": "SHIFT.MEB",
        "vertex_properties": [row["id"] for row in properties],
        "property_layouts": properties,
    }


def _color(pid, **overrides):
    row = {
        "id": pid,
        "name": "color" if pid == "460" else "color2",
        "payload_offset": 64,
        "stride": 4,
        "bytes": 8,
        "storage": "u8x4",
        "components": 4,
        "normalized": True,
    }
    row.update(overrides)
    return row


def test_bridge_constrains_color_to_two_d3d9_types_without_selecting():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460")]),
        _source_report(),
    )
    prop = result["properties"]["460"]
    assert prop["status"] == "observed"
    assert [row["code"] for row in prop["candidate_types"]] == [4, 8]
    assert [row["name"] for row in prop["candidate_types"]] == ["D3DCOLOR", "UBYTE4N"]
    assert result["meb_property_mapping"]["status"] == "not-proven"
    assert result["selection"] == "not-selected"


def test_bridge_keeps_runtime_type_evidence_separate_from_property_linkage():
    runtime = {
        "format": "SHIFT.D3D9DeclarationInstanceEvidence/1",
        "records": [
            {"stream": 0, "offset": 0, "type": 4, "method": 0, "usage": 10, "usage_index": 0},
            {"stream": 0, "offset": 4, "type": 2, "method": 0, "usage": 3, "usage_index": 0},
        ],
    }
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460")]),
        _source_report(),
        runtime_report=runtime,
    )
    runtime_row = result["properties"]["460"]["runtime_color_type_observation"]
    assert runtime_row["status"] == "observed"
    assert runtime_row["observed_type_codes"] == [4]
    assert runtime_row["property_linkage"] == "not-proven"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_bridge_reports_storage_mismatch_fail_closed():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("461", normalized=False)]),
        _source_report(),
    )
    assert result["properties"]["461"]["status"] == "mismatch"
    assert "normalized_true" in result["properties"]["461"]["meb_storage"]["failed_checks"]
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_bridge_reports_missing_property_as_partial():
    result = analyze_meb_d3d9_color_bridge(
        _meb([]),
        _source_report(),
    )
    assert result["properties"]["460"]["status"] == "partial"
    assert result["properties"]["460"]["meb_storage"]["status"] == "partial"


def test_bridge_source_text_hash_and_literal_census_are_provenance_only():
    source_text = b'uint f(void) { return "460" ? 1 : 0; }\n'
    source_report = _source_report()
    import hashlib

    source_report["source"]["sha256"] = hashlib.sha256(source_text).hexdigest()
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460")]),
        source_report,
        source_text=source_text,
    )
    integrity = result["source_integrity"]
    assert integrity["source_hash_matches_report"] is True
    assert integrity["literal_property_id_counts"] == {"460": 1, "461": 0}
    assert integrity["literal_property_ids_are_not_mapping_evidence"] is True
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_bridge_cli_roundtrip_with_source_text(tmp_path):
    meb_path = tmp_path / "meb.json"
    source_path = tmp_path / "source.json"
    source_text_path = tmp_path / "SHIFT.exe.c"
    output = tmp_path / "bridge.json"

    meb_path.write_text(
        json.dumps(_meb([_color("460")])),
        encoding="utf-8",
    )
    source_report = _source_report()
    source_text = b"source snapshot"
    import hashlib

    source_report["source"]["sha256"] = hashlib.sha256(source_text).hexdigest()
    source_path.write_text(json.dumps(source_report), encoding="utf-8")
    source_text_path.write_bytes(source_text)

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "d3d9_color_bridge_evidence.py"),
            str(meb_path),
            str(source_path),
            str(output),
            "--source-text",
            str(source_text_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT.MEBD3D9ColorBridgeEvidence/1"
    assert report["properties"]["460"]["candidate_types"][0]["code"] == 4
    assert report["source_integrity"]["source_hash_matches_report"] is True
    assert report["meb_property_mapping"]["status"] == "not-proven"
