import json
from pathlib import Path

from tools.run_apitrace_bmw_buffer_proof import run_pipeline


def _geometry():
    return {
        "format": "SHIFT.BMWM3MEBRuntimeGeometryParity/1",
        "status": "match",
        "ready": True,
        "resource": {
            "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
        },
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


def test_pipeline_writes_expected_outputs_and_proof(monkeypatch, tmp_path):
    trace = tmp_path / "shift.trace"
    geometry = tmp_path / "geometry.json"
    bff = tmp_path / "BMW_M3_E36.bff"
    out = tmp_path / "out"
    trace.write_bytes(b"trace")
    bff.write_bytes(b"bff")
    geometry.write_text(json.dumps(_geometry()) + "\n", encoding="utf-8")

    def fake_extract_from_source(trace, geometry_report, output_dir, *, apitrace):
        extracted = Path(output_dir)
        extracted.mkdir(parents=True, exist_ok=True)
        payload_dir = extracted / "buffer_payloads"
        payload_dir.mkdir()
        sizes = [269800, 300, 12588, 14772, 1224, 1152, 168]
        ib_pointers = [
            "0x27b394e0", "0x27b39560", "0x27b395e0",
            "0x27b39660", "0x27b396e0", "0x27b39760",
        ]
        records = []
        for i, size in enumerate(sizes):
            path = payload_dir / f"{i}.bin"
            payload = (b"V" if i == 0 else bytes([i - 1])) * size
            path.write_bytes(payload)
            records.append({
                "buffer_kind": "vertex_buffer" if i == 0 else "index_buffer",
                "buffer_pointer": "0x27b39460" if i == 0 else ib_pointers[i - 1],
                "blob_size": size,
                "full_buffer_candidate": True,
                "payload_path": str(path),
                "creation_call": 10 + i,
                "lock_call": 20 + i,
                "unlock_call": 30 + i,
                "fake_memcpy_call": 29 + i,
            })
        evidence = {
            "format": "SHIFT.APITRACEBMWBufferBlobEvidence/1",
            "source": {"trace": str(trace), "geometry_report": str(geometry_report)},
            "buffers": records,
        }
        (extracted / "buffer_blob_evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n",
            encoding="utf-8",
        )
        ibs = [
            "0x27b39760",
            "0x27b394e0",
            "0x27b396e0",
            "0x27b39660",
            "0x27b39560",
            "0x27b395e0",
        ]
        primitives = [28, 50, 192, 204, 2098, 2462]
        geometry_rows = []
        for i, (primitive, pointer) in enumerate(zip(primitives, ibs)):
            draw_call = 100 + i * 10
            geometry_rows.append({
                "geometry_key_sha256": f"geometry-{primitive}",
                "first_draw_call": draw_call,
                "primitive_counts": [primitive],
                "draws": [{
                    "call": draw_call,
                    "base_vertex_index": 0,
                    "min_vertex_index": 0,
                    "num_vertices": 3550,
                    "start_index": 0,
                    "prim_count": primitive,
                }],
                "state": {
                    "vertex_declaration": {
                        "call": draw_call - 3,
                        "raw": "SetVertexDeclaration(pDecl = 0xddd)",
                        "pointer": "0xddd",
                    }
                },
                "resources": {
                    "vertex_declaration": {
                        "pointer": "0xddd",
                        "binding_call": draw_call - 3,
                        "creation": {
                            "kind": "decl",
                            "call": 10,
                            "pointer": "0xddd",
                            "raw": "CreateVertexDeclaration(ppDecl = 0xddd)",
                        },
                        "same_instance": True,
                    },
                    "vertex_buffer": {
                        "pointer": "0x27b39460",
                        "binding_call": draw_call - 2,
                        "offset_bytes": 0,
                        "stride": 76,
                        "creation": {
                            "kind": "vb",
                            "call": 11,
                            "pointer": "0x27b39460",
                            "raw": "CreateVertexBuffer(...)",
                        },
                        "same_instance": True,
                    },
                    "index_buffer": {
                        "pointer": pointer,
                        "binding_call": draw_call - 1,
                        "creation": {
                            "kind": "ib",
                            "call": 12 + i,
                            "pointer": pointer,
                            "raw": "CreateIndexBuffer(...)",
                        },
                        "same_instance": True,
                    },
                },
            })
        unique = {
            "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
            "source": {"path": str(trace), "kind": "trace"},
            "scan": {
                "target_vertex_count": 3550,
                "target_vertex_buffer_pointer": "0x27b39460",
                "target_index_buffer_pointers": dict(zip(primitives, ibs)),
            },
            "geometry": geometry_rows,
        }
        (out / "unique_bmw_geometry.json").write_text(
            json.dumps(unique, indent=2) + "\n",
            encoding="utf-8",
        )
        return {"payload_records": 7, "full_buffer_candidates": 7}

    def fake_artifacts(bff_path, output_dir):
        expected = Path(output_dir) / "expected"
        expected.mkdir(parents=True, exist_ok=True)
        sizes = [269800, 300, 12588, 14772, 1224, 1152, 168]
        vertex = expected / "vertex_buffer.meb-order.bin"
        vertex.write_bytes(b"V" * sizes[0])
        index = expected / "index_buffer.uint16.bin"
        index.write_bytes(b"I")
        primitive_paths = []
        for i, size in enumerate(sizes[1:]):
            p = expected / f"index_buffer_{i:02d}.uint16.bin"
            p.write_bytes(bytes([i]) * size)
            primitive_paths.append(p)
        return {
            "manifest": {"format": "SHIFT.BMWM3RuntimeBufferArtifacts/1"},
            "directory": expected,
            "vertex": vertex,
            "index": index,
        }

    def fake_unique_geometry(trace, output_dir, **kwargs):
        return {
            "status": "observed",
            "source_kind": "trace",
            "unique_geometry_bindings": 6,
        }

    monkeypatch.setattr(
        "tools.run_apitrace_bmw_buffer_proof.extract_unique_bmw_geometry",
        fake_unique_geometry,
    )
    monkeypatch.setattr(
        "tools.run_apitrace_bmw_buffer_proof.extract_from_source",
        fake_extract_from_source,
    )
    monkeypatch.setattr(
        "tools.run_apitrace_bmw_buffer_proof._write_expected_artifacts",
        fake_artifacts,
    )

    result = run_pipeline(trace, geometry, bff, out, apitrace="apitrace")
    assert result["ready"] is True
    assert result["byte_parity"]["matches"] == 7
    assert result["geometry_proof"]["ready"] is True
    assert result["runtime_draw_instance_proof"]["ready"] is True
    assert result["next_gate"]["runtime_declaration_instance"] == "proven"
    assert (out / "runtime_geometry_proof.json").is_file()
    assert (out / "runtime_draw_instance_proof.json").is_file()
    assert (out / "pipeline_result.json").is_file()


def test_pipeline_rejects_missing_trace(tmp_path):
    geometry = tmp_path / "geometry.json"
    bff = tmp_path / "BMW_M3_E36.bff"
    geometry.write_text("{}", encoding="utf-8")
    bff.write_bytes(b"bff")
    try:
        run_pipeline(tmp_path / "missing.trace", geometry, bff, tmp_path / "out")
    except FileNotFoundError as exc:
        assert "missing.trace" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
