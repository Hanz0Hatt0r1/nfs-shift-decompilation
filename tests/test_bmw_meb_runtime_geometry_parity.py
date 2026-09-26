from pathlib import Path
import hashlib
import tempfile

import bmw_meb_runtime_geometry_parity as mod

def _summary():
    return {
        "source_sha256": mod.TARGET_SHA256,
        "vertex_count": 3550,
        "vertex_stride": 76,
        "index_count": 15102,
        "primitives": [
            {"first_index": 0, "index_count": 150},
            {"first_index": 150, "index_count": 6294},
            {"first_index": 6444, "index_count": 7386},
            {"first_index": 13830, "index_count": 612},
            {"first_index": 14442, "index_count": 576},
            {"first_index": 15018, "index_count": 84},
        ],
    }

def _geometry(counts, vb="0x27b39460", stride=76):
    ibs = ["0x1","0x2","0x3","0x4","0x5","0x6"]
    lines = [f"1 IDirect3DDevice9::SetStreamSource(this = 0x1, StreamNumber = 0, pStreamData = {vb}, OffsetInBytes = 0, Stride = {stride}) = D3D_OK"]
    for ib, count in zip(ibs, counts):
        lines.append(f"2 IDirect3DDevice9::SetIndices(this = 0x1, pIndexData = {ib}) = D3D_OK")
        lines.append(f"3 IDirect3DDevice9::DrawIndexedPrimitive(this = 0x1, PrimitiveType = D3DPT_TRIANGLELIST, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = {count}) = D3D_OK")
    return "\n".join(lines)

def test_compact_manifest_and_six_primitive_coverage():
    expected = mod.build_expectations(_summary())
    assert expected["vertex_buffer_bytes"] == 269800
    assert expected["index_buffer_bytes_uint16"] == 30204
    report = mod.correlate(expected, mod.parse_draw_evidence(_geometry([50,2098,2462,204,192,28])))
    assert report["ready"] is True
    assert report["runtime_stream"]["vertex_buffer"] == "0x27b39460"

def test_missing_primitive_blocks():
    expected = mod.build_expectations(_summary())
    report = mod.correlate(expected, mod.parse_draw_evidence(_geometry([50,2098,2462,204,192])))
    assert report["ready"] is False
    assert "geometry:missing-primitive-triangle-count:28" in report["blocking_reasons"]

def test_conflicting_vertex_buffers_block():
    expected = mod.build_expectations(_summary())
    text = _geometry([50,2098,2462], vb="0x1") + "\n" + _geometry([204,192,28], vb="0x2")
    report = mod.correlate(expected, mod.parse_draw_evidence(text))
    assert report["ready"] is False
    assert any(x.startswith("geometry:vertex-buffer-binding-set:") for x in report["blocking_reasons"])

def test_repacked_artifact_size_and_hash():
    expected = mod.build_expectations(_summary())
    with tempfile.TemporaryDirectory() as td:
        vb = Path(td) / "v.bin"
        vb.write_bytes(b"A" * expected["vertex_buffer_bytes"])
        sha = hashlib.sha256(vb.read_bytes()).hexdigest()
        report = mod.validate_repacked_artifact(vb, 269800, "vb", sha)
        assert report["status"] == "match"

def test_wrong_resource_hash_blocks():
    doc = _summary()
    doc["source_sha256"] = "00" * 32
    expected = mod.build_expectations(doc)
    report = mod.correlate(expected, mod.parse_draw_evidence(_geometry([50,2098,2462,204,192,28])))
    assert report["ready"] is False
    assert "geometry:unexpected-target-sha256" in report["blocking_reasons"]
