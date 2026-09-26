from pathlib import Path

from tools.extract_apitrace_unique_bmw import extract


def _write_dump(path: Path) -> None:
    path.write_text(
        """\
1 IDirect3DDevice9::CreateVertexBuffer(Length = 269800, Usage = 0, FVF = 0, Pool = 1, ppVertexBuffer = 0xaaa) = S_OK
2 IDirect3DDevice9::CreateIndexBuffer(Length = 12588, Usage = 0, Format = 101, Pool = 1, ppIndexBuffer = 0xbbb) = S_OK
3 IDirect3DDevice9::CreateVertexDeclaration(pVertexElements = NULL, ppDecl = 0xddd) = S_OK
4 IDirect3DDevice9::SetVertexDeclaration(pDecl = 0xddd) = S_OK
5 IDirect3DDevice9::SetStreamSource(StreamNumber = 0, pStreamData = 0xaaa, OffsetInBytes = 0, Stride = 76) = S_OK
6 IDirect3DDevice9::SetIndices(pIndexData = 0xbbb) = S_OK
7 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2098) = S_OK
8 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2098) = S_OK
9 IDirect3DDevice9::CreateIndexBuffer(Length = 14772, Usage = 0, Format = 101, Pool = 1, ppIndexBuffer = 0xccc) = S_OK
10 IDirect3DDevice9::SetIndices(pIndexData = 0xccc) = S_OK
11 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2462) = S_OK
12 IDirect3DIndexBuffer9::Release(this = 0xbbb) = 0
13 IDirect3DDevice9::CreateIndexBuffer(Length = 12588, Usage = 0, Format = 101, Pool = 1, ppIndexBuffer = 0xbbb) = S_OK
14 IDirect3DDevice9::SetIndices(pIndexData = 0xbbb) = S_OK
15 IDirect3DDevice9::DrawIndexedPrimitive(Type = 4, BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = 2098) = S_OK
""",
        encoding="utf-8",
    )


def test_streams_and_deduplicates_bmw_geometry(tmp_path: Path):
    dump = tmp_path / "garage.txt"
    out = tmp_path / "out"
    _write_dump(dump)

    summary = extract(dump, out, progress_every=0)

    assert summary["status"] == "observed"
    assert summary["target_draw_count"] == 4
    assert summary["target_draw_counts_by_primitive"] == {2098: 3, 2462: 1}
    assert summary["unique_geometry_bindings"] == 3

    report = (out / "unique_bmw_geometry.json").read_text(encoding="utf-8")
    assert '"format": "SHIFT.APITRACEUniqueBMWGeometry/1"' in report

    callset = [int(x) for x in (out / "callset.txt").read_text().splitlines() if x]
    assert 7 in callset
    assert 11 in callset
    assert 15 in callset
    assert 1 in callset
    assert 2 in callset
    assert 9 in callset
    assert 13 in callset


def test_pointer_reuse_after_release_is_not_deduplicated(tmp_path: Path):
    dump = tmp_path / "garage.txt"
    out = tmp_path / "out"
    _write_dump(dump)

    extract(dump, out, progress_every=0)

    import json

    report = json.loads(
        (out / "unique_bmw_geometry.json").read_text(encoding="utf-8")
    )
    rows = report["geometry"]
    reused = [
        row for row in rows
        if row["resources"].get("index_buffer", {}).get("pointer") == "0xbbb"
    ]

    assert len(reused) == 2
    assert sorted(
        row["resources"]["index_buffer"]["creation"]["call"] for row in reused
    ) == [2, 13]


def test_auto_trim_is_explicitly_trace_only(tmp_path: Path):
    dump = tmp_path / "garage.txt"
    out = tmp_path / "out"
    _write_dump(dump)

    summary = extract(dump, out, progress_every=0, auto_trim=True)

    assert summary["trim_status"] == "unsupported-for-text-dump"
    assert not (out / "bmw_unique.trace").exists()
