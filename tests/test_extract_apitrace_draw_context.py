from pathlib import Path
from tools.extract_apitrace_draw_context import main, State, update

def test_state_tracks_d3d9_bindings():
    s = State()
    update(s, 1, "CreateVertexBuffer",
           "1 IDirect3DDevice9::CreateVertexBuffer(ppVertexBuffer = &0x22) = D3D_OK")
    update(s, 2, "SetStreamSource",
           "2 IDirect3DDevice9::SetStreamSource(StreamNumber = 0, pStreamData = 0x22, OffsetInBytes = 4, Stride = 52) = D3D_OK")
    update(s, 3, "SetIndices",
           "3 IDirect3DDevice9::SetIndices(pIndexData = 0x33) = D3D_OK")
    update(s, 4, "SetVertexDeclaration",
           "4 IDirect3DDevice9::SetVertexDeclaration(pDecl = 0x11) = D3D_OK")
    update(s, 5, "SetVertexShader",
           "5 IDirect3DDevice9::SetVertexShader(pShader = 0x44) = D3D_OK")
    update(s, 6, "SetPixelShader",
           "6 IDirect3DDevice9::SetPixelShader(pShader = 0x55) = D3D_OK")
    snap = s.snapshot()
    assert snap["streams"]["0"]["pointer"] == "0x22"
    assert snap["streams"]["0"]["stride"] == 52
    assert snap["index_buffer"]["pointer"] == "0x33"
    assert snap["vertex_declaration"]["pointer"] == "0x11"

def test_main_extracts_target(tmp_path, monkeypatch):
    dump = tmp_path / "dump.txt"
    dump.write_text(
        "10 IDirect3DDevice9::SetIndices(pIndexData = 0x33) = D3D_OK\n"
        "11 IDirect3DDevice9::DrawIndexedPrimitive(this = 0x1, "
        "PrimitiveType = D3DPT_TRIANGLELIST, BaseVertexIndex = 0, "
        "MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, "
        "primCount = 2462) = D3D_OK\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", [
        "extract_apitrace_draw_context.py", str(dump), str(tmp_path / "out"),
        "--max-per-target", "1"
    ])
    assert main() == 0
    text = (tmp_path / "out" / "target_draw_context.jsonl").read_text()
    assert '"target": "paint_2"' in text
