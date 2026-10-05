from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from native_scene_vulkan_set import _texture_map_for_submesh


def _sha(char: str) -> str:
    return char * 64


def _dxt1_dds() -> bytes:
    values = (
        124, 0, 4, 4, 0, 0, 1,
        *([0] * 11),
        32, 0x4, struct.unpack("<I", b"DXT1")[0], 0,
        0, 0, 0, 0,
        0x1000, 0, 0, 0, 0,
    )
    return (
        b"DDS "
        + struct.pack("<31I", *values)
        + struct.pack("<HHI", 0xF800, 0x07E0, 0)
    )


def _dds_sha() -> str:
    return hashlib.sha256(_dxt1_dds()).hexdigest()


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "ir"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "diffuse.dds").write_bytes(_dxt1_dds())
    return root


def _submesh() -> dict:
    return {
        "textures": [{
            "sampler": "diffuseMap",
            "d3d9_sampler_register": 1,
            "texture_id": "tex_diffuse",
        }],
    }


def _binding(expected_sha: str | None) -> dict:
    texture = {
        "id": "tex_diffuse",
        "path": "tracks/silverstone/diffuse.dds",
        "gpu_ready": True,
    }
    if expected_sha is not None:
        texture["sha256"] = expected_sha
    return {
        "resources": {
            "textures": [texture],
        },
    }


def _row(*, archive: str, sha256: str) -> dict:
    return {
        "archive": archive,
        "path": "tracks/silverstone/diffuse.dds",
        "sha256": sha256,
        "raw": "raw/diffuse.dds",
    }


def test_phase657_accepts_exact_render_resource_path_and_sha(tmp_path: Path):
    root = _root(tmp_path)
    expected = _dds_sha()
    rows = [_row(archive="Silverstone_Era3_GrandPrix.bff", sha256=expected)]

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=rows,
        render_binding=_binding(expected),
        submesh=_submesh(),
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert blockers == []
    assert set(decoded) == {1}
    assert len(sources) == 1
    assert sources[0]["sha256"] == expected
    assert sources[0]["expected_sha256"] == expected
    assert sources[0]["identity_sha256_match"] is True


def test_phase657_rejects_path_match_with_different_ir_sha(tmp_path: Path):
    root = _root(tmp_path)
    rows = [_row(archive="Silverstone_Era3_GrandPrix.bff", sha256=_dds_sha())]

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=rows,
        render_binding=_binding(_sha("e")),
        submesh=_submesh(),
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert decoded == {}
    assert sources == []
    assert blockers == ["texture:s1:ir-resource-sha256-mismatch"]


def test_phase657_rejects_renderer_texture_without_exact_sha(tmp_path: Path):
    root = _root(tmp_path)
    rows = [_row(archive="Silverstone_Era3_GrandPrix.bff", sha256=_dds_sha())]

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=rows,
        render_binding=_binding(None),
        submesh=_submesh(),
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert decoded == {}
    assert sources == []
    assert blockers == ["texture:s1:renderer-resource-sha256-invalid"]


def test_phase657_fallback_keeps_exact_sha_identity_across_archives(tmp_path: Path):
    root = _root(tmp_path)
    expected = _dds_sha()
    rows = [
        _row(archive="Silverstone_Era3_GrandPrix.bff", sha256=_sha("a")),
        _row(archive="RENDER.bff", sha256=expected),
    ]

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=rows,
        render_binding=_binding(expected),
        submesh=_submesh(),
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert blockers == []
    assert set(decoded) == {1}
    assert sources[0]["archive"] == "RENDER.bff"
    assert sources[0]["sha256"] == expected
    assert sources[0]["expected_sha256"] == expected
