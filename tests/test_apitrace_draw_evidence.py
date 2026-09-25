import json
import zipfile

from tools.apitrace_draw_evidence import analyze


def line(call, nv, start, prim):
    return (
        f"{call} IDirect3DDevice9::DrawIndexedPrimitive(this = 0x1, "
        f"PrimitiveType = D3DPT_TRIANGLELIST, BaseVertexIndex = 0, "
        f"MinVertexIndex = 0, NumVertices = {nv}, startIndex = {start}, "
        f"primCount = {prim}) = D3D_OK\n"
    )


def test_analyze_identifies_bmw_target_signatures(tmp_path):
    src = tmp_path / "draws.txt"
    src.write_text(
        line(100, 3550, 0, 50)
        + line(101, 3550, 0, 192)
        + line(102, 3550, 0, 2462)
        + line(103, 3550, 0, 2098)
        + line(104, 12, 0, 4),
        encoding="utf-8",
    )
    report = analyze(src, top_n=10)
    assert report["format"] == "SHIFT.APITRACEDrawEvidence/1"
    assert report["status"] == "observed"
    assert report["ready"] is False
    assert report["source"]["draw_count"] == 5
    assert report["target"]["paint_ranges"]["paint_1"]["observed_draw_count"] == 1
    assert report["target"]["paint_ranges"]["paint_2"]["observed_draw_count"] == 1
    assert report["target"]["paint_ranges"]["paint_1"]["index_count_match"] is True
    assert report["target"]["paint_ranges"]["paint_1"]["start_index_match"] is False
    assert report["target"]["adjacent_target_pairs"]["2462->2098"] == 1
    assert report["evidence_boundary"]["same_instance_gate"] == "not-proven"


def test_analyze_accepts_zip_input(tmp_path):
    src = tmp_path / "draws.txt"
    src.write_text(line(200, 3550, 0, 2098), encoding="utf-8")
    archive = tmp_path / "draws.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(src, arcname="shift_draws.txt")
    report = analyze(archive)
    assert report["source"]["member"] == "shift_draws.txt"
    assert report["target"]["paint_ranges"]["paint_1"]["observed_draw_count"] == 1
