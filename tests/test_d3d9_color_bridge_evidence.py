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
            {
                "id": "binary-descriptor-triple-semantics",
                "status": "observed",
                "function": "FUN_009340C0",
                "address": "0x009340C0",
                "source_line": 500,
                "detail": "Binary mesh loader consumes [Type, Usage, Channel] triples",
            },
            {
                "id": "binary-mesh-loader-identity",
                "status": "observed",
                "function": "FUN_009340C0",
                "address": "0x009340C0",
                "source_line": 520,
                "detail": "MEB descriptor triple is consumed by the binary mesh loader",
            },
            {
                "id": "meb-extension-registration",
                "status": "observed",
                "function": "FUN_00859800",
                "address": "0x00859800",
                "source_line": 540,
                "detail": "MEB extension registration path",
            },
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


def _resource_color_report(property_id="460", *, payload_sha="b" * 64, raw_sha=None):
    return {
        "format": "SHIFT.ColorABIEvidence/1",
        "property_id": property_id,
        "raw_bytes_sha256": payload_sha if raw_sha is None else raw_sha,
        "sample_count": 2,
        "source": {
            "kind": "bff-meb",
            "archive": "BMW_M3_E36.bff",
            "resource": "cars/body.meb",
            "entry_index": 7,
            "resource_sha256": "a" * 64,
            "stream": "colors" if property_id == "460" else "colors2",
            "vertex_count": 2,
            "property_layout": {
                "id": property_id,
                "payload_offset": 76,
                "stride": 4,
                "bytes": 8,
            },
            "property_descriptor": {
                "id": property_id,
                "offset": 64,
                "words": [4, 6, 0 if property_id == "460" else 1],
                "raw_hex": (
                    "040000000600000000000000"
                    if property_id == "460"
                    else "040000000600000100000000"
                ),
            },
            "descriptor_range": {"offset": 64, "length": 12, "end": 76},
            "descriptor_range_status": "observed",
            "payload_range": {"offset": 76, "length": 8, "end": 84},
            "payload_range_status": "observed",
            "payload_raw_bytes_sha256": payload_sha,
            "decoded_stream_matches_payload": True,
            "decoded_stream_matches_payload_status": "observed",
        },
    }


def test_color_bridge_accepts_coherent_real_resource_provenance():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460"), _color("461")]),
        _source_report(),
        resource_reports=[_resource_color_report("460")],
    )
    assert result["resource_provenance"]["460"]["status"] == "observed"
    assert result["resource_provenance"]["460"]["reports"][0]["status"] == "observed"
    assert result["resource_provenance"]["461"]["status"] == "not-supplied"
    assert result["resource_errors"] == []
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_color_bridge_rejects_tampered_resource_payload_hash():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460")]),
        _source_report(),
        resource_reports=[_resource_color_report("460", raw_sha="c" * 64)],
    )
    assert result["resource_provenance"]["460"]["status"] == "mismatch"
    assert result["resource_provenance"]["460"]["reports"][0]["status"] == "mismatch"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_color_bridge_isolates_unknown_resource_property_id():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460"), _color("461")]),
        _source_report(),
        resource_reports=[_resource_color_report("999")],
    )
    assert result["resource_provenance"]["460"]["status"] == "not-supplied"
    assert result["resource_provenance"]["461"]["status"] == "not-supplied"
    assert result["resource_errors"][0]["property_id"] == "999"
    assert result["resource_errors"][0]["status"] == "mismatch"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_color_bridge_keeps_resource_provenance_independent_per_property():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460"), _color("461")]),
        _source_report(),
        resource_reports=[
            _resource_color_report("460"),
            _resource_color_report("461"),
        ],
    )
    assert result["resource_provenance"]["460"]["status"] == "observed"
    assert result["resource_provenance"]["461"]["status"] == "observed"
    assert len(result["resource_provenance"]["460"]["reports"]) == 1
    assert len(result["resource_provenance"]["461"]["reports"]) == 1


def test_bridge_promotes_exact_descriptor_triple_to_type4():
    result = analyze_meb_d3d9_color_bridge(
        _meb([
            _color("460"),
            _color("461"),
        ]),
        _source_report(),
    )
    assert result["descriptor_triple_evidence"]["d3d9_type_mapping"]["status"] == "match"
    assert result["properties"]["460"]["property_to_type"]["status"] == "observed"
    assert result["properties"]["461"]["property_to_type"]["status"] == "observed"
    assert result["d3d9_candidates"]["status"] == "resolved"
    assert result["d3d9_candidates"]["selected_type"]["code"] == 4
    assert result["d3d9_candidates"]["selected_type"]["name"] == "D3DCOLOR"
    assert result["d3d9_candidates"]["selected_type"]["memory_order"] == "BGRA"
    assert result["meb_property_mapping"]["status"] == "observed"
    assert result["selection"] == "resolved"
    assert result["verified_abi"] is True


def test_bridge_does_not_promote_without_both_color_descriptors():
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460")]),
        _source_report(),
    )
    assert result["properties"]["460"]["property_to_type"]["status"] == "not-proven"
    assert result["d3d9_candidates"]["status"] == "ambiguous"
    assert result["meb_property_mapping"]["status"] == "not-proven"
    assert result["selection"] == "not-selected"
    assert result["verified_abi"] is False

def test_bridge_accepts_exact_pe_backed_color_abi():
    pe = {
        "format": "SHIFT.PEImageEvidence/1",
        "conclusions": {
            "d3d9_color_abi": {
                "status": "observed",
                "type_4": {
                    "ordinal": 4,
                    "internal_name": "RGBA32",
                    "size_bytes": 4,
                    "components": 4,
                    "d3d9_type": "D3DDECLTYPE_D3DCOLOR",
                },
                "usage_6": {
                    "ordinal": 6,
                    "source_name": "Colour",
                    "numeric_d3d9_usage": 10,
                },
            }
        },
    }
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460"), _color("461")]),
        _source_report(),
        pe_evidence=pe,
    )
    assert result["pe_color_abi"]["status"] == "observed"
    assert result["pe_color_abi"]["type_4"]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"
    assert result["pe_color_abi"]["usage_6"]["numeric_d3d9_usage"] == 10
    assert result["meb_property_mapping"]["status"] == "observed"


def test_bridge_rejects_invalid_pe_color_abi():
    pe = {
        "format": "SHIFT.PEImageEvidence/1",
        "conclusions": {
            "d3d9_color_abi": {
                "status": "observed",
                "type_4": {
                    "ordinal": 4,
                    "internal_name": "WRONG",
                    "size_bytes": 4,
                    "components": 4,
                    "d3d9_type": "D3DDECLTYPE_FLOAT4",
                },
                "usage_6": {
                    "ordinal": 6,
                    "source_name": "Colour",
                    "numeric_d3d9_usage": 10,
                },
            }
        },
    }
    result = analyze_meb_d3d9_color_bridge(
        _meb([_color("460"), _color("461")]),
        _source_report(),
        pe_evidence=pe,
    )
    assert result["pe_color_abi"]["status"] == "mismatch"
