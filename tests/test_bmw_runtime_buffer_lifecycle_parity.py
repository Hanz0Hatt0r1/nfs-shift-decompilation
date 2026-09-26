from bmw_runtime_buffer_lifecycle_parity import (
    build_report,
    parse_buffer_creations,
    _latest_before,
)


def _geometry():
    return {
        "resource": {
            "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
        },
        "runtime_stream": {
            "vertex_buffer": "0x100",
            "derived_vertex_buffer_bytes": 269800,
            "stride": 76,
            "observed_target_draw_count": 28,
        },
        "primitive_correlations": [
            {
                "index": 0,
                "triangle_count": 50,
                "runtime_ib": "0x200",
                "representative": {"draw_index": 139, "call": 500},
            },
            {
                "index": 1,
                "triangle_count": 2098,
                "runtime_ib": "0x300",
                "representative": {"draw_index": 120, "call": 490},
            },
        ],
    }


def test_parse_buffer_creations_reads_vertex_and_index_records():
    rows = parse_buffer_creations(
        "10 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 269800, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "20 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 300, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x200, pSharedHandle = NULL) = D3D_OK\n"
    )
    assert rows["vertex"][0]["length"] == 269800
    assert rows["vertex"][0]["pointer"] == "0x100"
    assert rows["index"][0]["length"] == 300
    assert rows["index"][0]["format"] == "D3DFMT_INDEX16"


def test_latest_before_respects_pointer_lifetime_boundary():
    rows = parse_buffer_creations(
        "10 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 64, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "30 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 128, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
    )["vertex"]
    assert _latest_before(rows, "0x100", 20)["length"] == 64
    assert _latest_before(rows, "0x100", 40)["length"] == 128


def test_build_report_matches_bmw_buffer_creation_sizes():
    report = build_report(
        _geometry(),
        "470 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 269800, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "480 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 300, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x200, pSharedHandle = NULL) = D3D_OK\n"
        "481 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 12588, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x300, pSharedHandle = NULL) = D3D_OK\n"
    )
    assert report["ready"] is True
    assert report["target_draw_call"] == 500
    assert report["vertex_buffer"]["creation"]["length"] == 269800
    assert report["index_buffers"][0]["status"] == "match"
    assert report["index_buffers"][1]["status"] == "match"


def test_build_report_blocks_creation_after_target_draw():
    report = build_report(
        _geometry(),
        "600 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 269800, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "601 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 300, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x200, pSharedHandle = NULL) = D3D_OK\n"
        "602 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 12588, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x300, pSharedHandle = NULL) = D3D_OK\n"
    )
    assert report["ready"] is False
    assert "vertex-buffer:create-not-observed-before-draw" in report["blocking_reasons"]


def test_build_report_rejects_wrong_index_format():
    report = build_report(
        _geometry(),
        "470 IDirect3DDevice9::CreateVertexBuffer(this = 0x1, Length = 269800, Usage = 0x0, FVF = 0x0, Pool = D3DPOOL_MANAGED, ppVertexBuffer = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "480 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 300, Usage = 0x0, Format = D3DFMT_INDEX32, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x200, pSharedHandle = NULL) = D3D_OK\n"
        "481 IDirect3DDevice9::CreateIndexBuffer(this = 0x1, Length = 12588, Usage = 0x0, Format = D3DFMT_INDEX16, Pool = D3DPOOL_MANAGED, ppIndexBuffer = &0x300, pSharedHandle = NULL) = D3D_OK\n"
    )
    assert report["ready"] is False
    assert any(reason.startswith("index-buffer:format-unexpected:0x200") for reason in report["blocking_reasons"])
