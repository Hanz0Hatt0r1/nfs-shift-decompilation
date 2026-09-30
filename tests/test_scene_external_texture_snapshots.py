import hashlib
import json

from scene_external_texture_snapshots import (
    FORMAT,
    resolve_scene_external_texture_snapshots,
)


def _texture():
    return {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "D3D9_CAPTURE_PPM",
        "width": 1,
        "height": 1,
        "pixel_format": "RGBA8",
        "pixels": [9, 8, 7, 255],
    }


def _write_contract(tmp_path, *, sha=None, snapshots=None):
    texture_path = tmp_path / "draw0_s7.json"
    texture_path.write_text(
        json.dumps(_texture(), sort_keys=True),
        encoding="utf-8",
    )
    actual_sha = hashlib.sha256(texture_path.read_bytes()).hexdigest()
    rows = snapshots or [{
        "draw_order": 0,
        "scene_draw_identity_sha256": "a" * 64,
        "sampler": "shadowMap",
        "sampler_type": "sampler2D",
        "d3d9_sampler_register": 7,
        "reference_texture_path": texture_path.name,
        "reference_texture_sha256": sha or actual_sha,
        "source_provenance": {
            "kind": "D3D9_CAPTURE_PPM",
            "frame": 12,
            "draw": 34,
            "stage": 7,
        },
    }]
    contract = tmp_path / "external_snapshots.json"
    contract.write_text(
        json.dumps({
            "format": FORMAT,
            "version": 1,
            "snapshots": rows,
        }),
        encoding="utf-8",
    )
    return contract, actual_sha


def test_scene_external_snapshot_set_resolves_exact_reference_texture(tmp_path):
    contract, actual_sha = _write_contract(tmp_path)

    report, resources = resolve_scene_external_texture_snapshots(contract)

    assert report["ready"] is True, report["blocking_reasons"]
    assert report["snapshot_count"] == 1
    row = report["snapshots"][0]
    assert row["draw_order"] == 0
    assert row["d3d9_sampler_register"] == 7
    assert row["reference_texture"]["sha256"] == actual_sha
    assert row["source_provenance"]["stage"] == 7
    assert resources[(0, 7)]["format"] == "SHIFT.ReferenceTexture/1"
    assert report["boundary"]["snapshot_authenticity_asserted_by_caller"] is False


def test_scene_external_snapshot_set_rejects_reference_texture_hash_tamper(tmp_path):
    contract, _ = _write_contract(tmp_path, sha="0" * 64)

    report, resources = resolve_scene_external_texture_snapshots(contract)

    assert report["ready"] is False
    assert resources == {}
    assert any(
        reason.endswith("reference-texture-sha256-mismatch")
        for reason in report["blocking_reasons"]
    )


def test_scene_external_snapshot_set_rejects_duplicate_draw_register(tmp_path):
    texture_path = tmp_path / "draw0_s7.json"
    texture_path.write_text(
        json.dumps(_texture(), sort_keys=True),
        encoding="utf-8",
    )
    sha = hashlib.sha256(texture_path.read_bytes()).hexdigest()
    base = {
        "draw_order": 0,
        "scene_draw_identity_sha256": "a" * 64,
        "sampler": "shadowMap",
        "sampler_type": "sampler2D",
        "d3d9_sampler_register": 7,
        "reference_texture_path": texture_path.name,
        "reference_texture_sha256": sha,
        "source_provenance": {"kind": "D3D9_CAPTURE_PPM"},
    }
    contract, _ = _write_contract(
        tmp_path,
        snapshots=[base, dict(base)],
    )

    report, resources = resolve_scene_external_texture_snapshots(contract)

    assert report["ready"] is False
    assert resources == {}
    assert any(
        "duplicate-draw-register:0:s7" in reason
        for reason in report["blocking_reasons"]
    )


def test_scene_external_snapshot_set_rejects_non_2d_or_missing_provenance(tmp_path):
    texture_path = tmp_path / "draw0_s7.json"
    texture_path.write_text(
        json.dumps(_texture(), sort_keys=True),
        encoding="utf-8",
    )
    sha = hashlib.sha256(texture_path.read_bytes()).hexdigest()
    contract, _ = _write_contract(
        tmp_path,
        snapshots=[{
            "draw_order": 0,
            "scene_draw_identity_sha256": "a" * 64,
            "sampler": "environmentMap",
            "sampler_type": "samplerCube",
            "d3d9_sampler_register": 3,
            "reference_texture_path": texture_path.name,
            "reference_texture_sha256": sha,
        }],
    )

    report, resources = resolve_scene_external_texture_snapshots(contract)

    assert report["ready"] is False
    assert resources == {}
    assert any(
        reason.endswith("sampler-type-not-2d")
        for reason in report["blocking_reasons"]
    )
    assert any(
        reason.endswith("source-provenance-missing")
        for reason in report["blocking_reasons"]
    )
