import json
from pathlib import Path

import pytest

import tools.extract_apitrace_single_frame as mod


def _lines():
    return [
        "1 IDirect3DDevice9::SetStreamSource(StreamNumber = 0, pStreamData = 0xaaa, OffsetInBytes = 0, Stride = 76) = S_OK",
        "2 IDirect3DDevice9::SetIndices(pIndexData = 0xbbb) = S_OK",
        "3 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2098) = S_OK",
        "4 IDirect3DDevice9::Present() = S_OK",
        "5 IDirect3DDevice9::SetIndices(pIndexData = 0xccc) = S_OK",
        "6 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 28) = S_OK",
        "7 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2462) = S_OK",
        "8 IDirect3DDevice9::Present() = S_OK",
    ]


def test_parse_pointer_targets_accepts_current_unique_bmw_schema(tmp_path: Path):
    evidence = tmp_path / "unique_bmw_geometry.json"
    evidence.write_text(
        json.dumps(
            {
                "geometry": [],
                "scan": {
                    "target_vertex_buffer_pointer": "0x27b39460",
                    "target_index_buffer_pointers": {
                        "50": "0x27b394e0",
                        "2098": "0x27b39560",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    vb, ibs = mod._parse_pointer_targets(evidence)

    assert vb == "0x27b39460"
    assert ibs == {
        50: "0x27b394e0",
        2098: "0x27b39560",
    }


def test_find_bmw_frame_selects_highest_primitive_coverage(monkeypatch, tmp_path: Path):
    trace = tmp_path / "shift.trace"
    trace.write_bytes(b"trace")
    monkeypatch.setattr(mod, "_dump_lines", lambda *args, **kwargs: iter(_lines()))

    result = mod.find_bmw_frame(trace)

    assert result["frame"]["frame_index"] == 1
    assert result["frame"]["start_call"] == 5
    assert result["frame"]["end_call"] == 8
    assert result["frame"]["target_draw_calls"] == [6, 7]
    assert result["frame"]["primitive_counts"] == [28, 2462]


def test_find_draw_frame_returns_exact_containing_frame(monkeypatch, tmp_path: Path):
    trace = tmp_path / "shift.trace"
    trace.write_bytes(b"trace")
    monkeypatch.setattr(mod, "_dump_lines", lambda *args, **kwargs: iter(_lines()))

    result = mod.find_draw_frame(trace, 3)

    assert result["frame"]["frame_index"] == 0
    assert result["frame"]["start_call"] == 0
    assert result["frame"]["end_call"] == 4
    assert result["frame"]["target_draw_calls"] == [3]


def test_find_draw_frame_rejects_missing_frame_boundary(monkeypatch, tmp_path: Path):
    trace = tmp_path / "shift.trace"
    trace.write_bytes(b"trace")
    monkeypatch.setattr(
        mod,
        "_dump_lines",
        lambda *args, **kwargs: iter(_lines()[:3]),
    )

    with pytest.raises(RuntimeError, match="no following Present"):
        mod.find_draw_frame(trace, 3)


def test_trim_frame_number_uses_apitrace_auto_frames(monkeypatch, tmp_path: Path):
    trace = tmp_path / "shift.trace"
    output = tmp_path / "single.trace"
    trace.write_bytes(b"trace")
    seen = {}

    def fake_run(command, cwd=None):
        seen["command"] = command
        output.write_bytes(b"trimmed")

    monkeypatch.setattr(mod, "_run", fake_run)

    command = mod.trim_frame_number(
        trace,
        output,
        frame=17,
        apitrace="apitrace",
    )

    assert command == [
        "apitrace",
        "trim",
        "--auto",
        "--frames=17/frame",
        "-o",
        str(output),
        str(trace),
    ]
    assert seen["command"] == command


def test_extract_auto_bmw_writes_trace_and_manifest(monkeypatch, tmp_path: Path):
    trace = tmp_path / "shift.trace"
    out = tmp_path / "out"
    trace.write_bytes(b"trace")
    monkeypatch.setattr(mod, "_dump_lines", lambda *args, **kwargs: iter(_lines()))

    def fake_run(command, cwd=None):
        output = Path(command[command.index("-o") + 1])
        output.write_bytes(b"trimmed")

    monkeypatch.setattr(mod, "_run", fake_run)

    result = mod.extract(trace, out, auto_bmw=True)

    assert result["ready"] is True
    assert result["mode"] == "auto-bmw"
    assert result["selection"]["frame"]["frame_index"] == 1
    assert (out / "single_frame.trace").read_bytes() == b"trimmed"

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "SHIFT.APITRACESingleFrameTrace/1"
    assert manifest["selection"]["frame"]["end_call"] == 8


def test_extract_requires_exactly_one_mode(tmp_path: Path):
    trace = tmp_path / "shift.trace"
    trace.write_bytes(b"trace")

    with pytest.raises(ValueError, match="exactly one"):
        mod.extract(trace, tmp_path / "out")
