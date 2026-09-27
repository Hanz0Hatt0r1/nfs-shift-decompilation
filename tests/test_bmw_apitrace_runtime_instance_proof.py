import json
from pathlib import Path

from bmw_apitrace_runtime_instance_proof import (
    DEFAULT_PRIMITIVE_COUNTS,
    build_report,
    validate_file,
)


def _row(primitive: int, draw_call: int, ib: str, *, ready: bool = True) -> dict:
    declaration = {
        "pointer": "0xddd",
        "binding_call": draw_call - 3,
        "creation": {
            "kind": "decl",
            "call": 10,
            "pointer": "0xddd",
            "raw": "CreateVertexDeclaration(ppDecl = 0xddd)",
        },
        "same_instance": ready,
    }
    vertex_buffer = {
        "pointer": "0xaaa",
        "binding_call": draw_call - 2,
        "offset_bytes": 0,
        "stride": 76,
        "creation": {
            "kind": "vb",
            "call": 11,
            "pointer": "0xaaa",
            "raw": "CreateVertexBuffer(ppVertexBuffer = 0xaaa)",
        },
        "same_instance": ready,
    }
    index_buffer = {
        "pointer": ib,
        "binding_call": draw_call - 1,
        "creation": {
            "kind": "ib",
            "call": draw_call - 10,
            "pointer": ib,
            "raw": "CreateIndexBuffer(...)",
        },
        "same_instance": ready,
    }
    return {
        "geometry_key_sha256": f"geometry-{primitive}",
        "first_draw_call": draw_call,
        "primitive_counts": [primitive],
        "draws": [
            {
                "call": draw_call,
                "base_vertex_index": 0,
                "min_vertex_index": 0,
                "num_vertices": 3550,
                "start_index": 0,
                "prim_count": primitive,
            }
        ],
        "state": {
            "vertex_declaration": {
                "call": draw_call - 3,
                "raw": "SetVertexDeclaration(pDecl = 0xddd)",
                "pointer": "0xddd",
            }
        },
        "resources": {
            "vertex_declaration": declaration,
            "vertex_buffer": vertex_buffer,
            "index_buffer": index_buffer,
        },
    }


def _report() -> dict:
    ibs = {
        28: "0x27b39760",
        50: "0x27b394e0",
        192: "0x27b396e0",
        204: "0x27b39660",
        2098: "0x27b39560",
        2462: "0x27b395e0",
    }
    rows = [_row(p, 100 + i * 10, ib) for i, (p, ib) in enumerate(sorted(ibs.items()))]
    return {
        "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
        "source": {"path": "shift.trace", "kind": "trace"},
        "scan": {
            "target_vertex_count": 3550,
            "target_vertex_buffer_pointer": "0xaaa",
            "target_index_buffer_pointers": ibs,
        },
        "geometry": rows,
    }


def test_runtime_instance_proof_requires_all_known_bmw_primitives():
    report = build_report(_report())
    assert report["ready"] is True
    assert report["status"] == "proven"
    assert report["unique_instance_count"] == 6
    assert len(report["selected_instances"]) == len(DEFAULT_PRIMITIVE_COUNTS)
    assert report["evidence_boundary"]["declaration_bytes"] == "not-observed"


def test_runtime_instance_proof_rejects_missing_declaration_creation():
    data = _report()
    data["geometry"][0]["resources"]["vertex_declaration"]["same_instance"] = False
    report = build_report(data)
    assert report["ready"] is False
    assert any(
        reason.startswith("primitive:28:checks-failed:")
        for reason in report["blocking_reasons"]
    )


def test_runtime_instance_proof_rejects_pointer_mismatch():
    data = _report()
    data["geometry"][0]["resources"]["vertex_buffer"]["pointer"] = "0xdead"
    report = build_report(data)
    assert report["ready"] is False
    assert "target_vertex_buffer_pointer_match" in report["blocking_reasons"][0]


def test_validate_file_round_trip(tmp_path: Path):
    path = tmp_path / "unique_bmw_geometry.json"
    path.write_text(json.dumps(_report()) + "\n", encoding="utf-8")
    report = validate_file(path)
    assert report["format"] == "SHIFT.BMWM3APITRACERuntimeDrawInstanceProof/1"
    assert report["ready"] is True
