from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from native_scene_vulkan_set import _texture_map_for_submesh


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


def _fixture(tmp_path: Path):
    root = tmp_path / "ir"
    raw = root / "raw" / "diffuse.dds"
    raw.parent.mkdir(parents=True)
    payload = _dxt1_dds()
    raw.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    row = {
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "path": "tracks/silverstone/diffuse.dds",
        "sha256": digest,
        "decoded_sha256": digest,
        "raw": "raw/diffuse.dds",
    }
    binding = {
        "resources": {
            "textures": [{
                "id": "tex_diffuse",
                "path": row["path"],
                "sha256": digest,
                "gpu_ready": True,
            }],
        },
    }
    submesh = {
        "textures": [{
            "sampler": "diffuseMap",
            "d3d9_sampler_register": 1,
            "texture_id": "tex_diffuse",
        }],
    }
    return root, raw, row, binding, submesh, digest


def test_phase658_accepts_exact_manifest_and_materialized_dds_bytes(tmp_path: Path):
    root, _raw, row, binding, submesh, digest = _fixture(tmp_path)

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=[row],
        render_binding=binding,
        submesh=submesh,
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert blockers == []
    assert set(decoded) == {1}
    assert len(sources) == 1
    assert sources[0]["expected_sha256"] == digest
    assert sources[0]["decoded_sha256"] == digest
    assert sources[0]["raw_sha256"] == digest
    assert sources[0]["raw_identity_sha256_match"] is True


def test_phase658_rejects_tampered_materialized_dds_before_decode(tmp_path: Path):
    root, raw, row, binding, submesh, _digest = _fixture(tmp_path)
    raw.write_bytes(raw.read_bytes() + b"tampered")

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=[row],
        render_binding=binding,
        submesh=submesh,
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert decoded == {}
    assert sources == []
    assert blockers == ["texture:s1:raw-payload-sha256-mismatch"]


def test_phase658_rejects_manifest_decoded_identity_drift(tmp_path: Path):
    root, _raw, row, binding, submesh, _digest = _fixture(tmp_path)
    row["decoded_sha256"] = "f" * 64

    decoded, blockers, sources = _texture_map_for_submesh(
        root=root,
        rows=[row],
        render_binding=binding,
        submesh=submesh,
        prefer_archive="Silverstone_Era3_GrandPrix.bff",
    )

    assert decoded == {}
    assert sources == []
    assert blockers == ["texture:s1:ir-decoded-sha256-mismatch"]
