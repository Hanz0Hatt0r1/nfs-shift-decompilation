from bmw_runtime_geometry_proof import build_report


TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"


def _geometry():
    return {
        "format": "SHIFT.BMWM3MEBRuntimeGeometryParity/1",
        "status": "match",
        "ready": True,
        "resource": {"path": TARGET_MEB, "sha256": TARGET_SHA256},
        "runtime_stream": {
            "vertex_buffer": "0x27b39460",
            "stride": 76,
            "derived_vertex_buffer_bytes": 269800,
        },
        "primitive_correlations": [
            {"status": "match", "triangle_count": 50, "runtime_ib": "0x27b394e0"},
            {"status": "match", "triangle_count": 2098, "runtime_ib": "0x27b39560"},
            {"status": "match", "triangle_count": 2462, "runtime_ib": "0x27b395e0"},
            {"status": "match", "triangle_count": 204, "runtime_ib": "0x27b39660"},
            {"status": "match", "triangle_count": 192, "runtime_ib": "0x27b396e0"},
            {"status": "match", "triangle_count": 28, "runtime_ib": "0x27b39760"},
        ],
    }


def _parity(pointer_metadata=True):
    vb = {
        "label": "vertex-buffer",
        "runtime_buffer_pointer": "0x27b39460" if pointer_metadata else None,
        "comparison": {"ready": True, "observed_byte_size": 269800},
    }
    ib_sizes = [300, 12588, 14772, 1224, 1152, 168]
    ib_ptrs = ["0x27b394e0", "0x27b39560", "0x27b395e0", "0x27b39660", "0x27b396e0", "0x27b39760"]
    ib = [
        {
            "label": f"index-buffer:{size}-bytes",
            "runtime_buffer_pointer": pointer if pointer_metadata else None,
            "comparison": {"ready": True, "observed_byte_size": size},
        }
        for size, pointer in zip(ib_sizes, ib_ptrs)
    ]
    return {
        "format": "SHIFT.BMWM3DirectBlobParity/1",
        "status": "match",
        "ready": True,
        "matches": 7,
        "results": [vb, *ib],
        "evidence_boundary": {
            "raw_runtime_vb_bytes": "proven",
            "raw_runtime_ib_bytes": "proven",
            "meb_byte_parity": "proven",
        },
    }


def test_proof_requires_pointer_provenance():
    report = build_report(_geometry(), _parity(pointer_metadata=False))
    assert report["ready"] is False
    assert "parity:vertex-buffer-pointer-metadata-missing-or-mismatch" in report["blocking_reasons"]
    assert "parity:index-buffer-pointer-metadata-missing" in report["blocking_reasons"]


def test_proof_accepts_complete_geometry_and_byte_parity():
    report = build_report(_geometry(), _parity())
    assert report["ready"] is True
    assert report["status"] == "proven"
    assert report["evidence_boundary"]["raw_runtime_vb_bytes"] == "proven"
    assert report["evidence_boundary"]["raw_runtime_ib_bytes"] == "proven"
    assert report["render_consumer_contract"]["vertex_buffer"]["bytes"] == 269800
    assert len(report["render_consumer_contract"]["index_buffers"]) == 6


def test_geometry_pointer_mismatch_blocks():
    geometry = _geometry()
    geometry["runtime_stream"]["vertex_buffer"] = "0x999"
    report = build_report(geometry, _parity())
    assert report["ready"] is False
    assert "geometry:vertex-buffer-pointer-mismatch" in report["blocking_reasons"]
