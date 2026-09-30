import hashlib
import json

from native_scene_external_sampler_snapshots import (
    FORMAT,
    PROVENANCE_FORMAT,
    resolve_draw_external_sampler2d_snapshots,
    validate_external_sampler_snapshot_contract,
)


def _sha(char):
    return char * 64


def _texture():
    return {
        "format": "SHIFT.ReferenceTexture/1",
        "width": 1,
        "height": 1,
        "pixel_format": "RGBA8",
        "pixels": [10, 20, 30, 255],
    }


def _texture_sha(texture):
    return hashlib.sha256(
        json.dumps(
            texture,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _snapshot(*, draw_sha=None, resource_sha=None, register=7):
    texture = _texture()
    return {
        "draw_identity_sha256": draw_sha or _sha("d"),
        "resource": {
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "path": "tracks/silverstone/object.imb",
            "sha256": resource_sha or _sha("a"),
        },
        "primitive_index": 3,
        "d3d9_sampler_register": register,
        "sampler_type": "sampler2D",
        "texture": texture,
        "texture_sha256": _texture_sha(texture),
        "provenance": {
            "format": PROVENANCE_FORMAT,
            "source_kind": "runtime-capture",
            "source_sha256": _sha("c"),
        },
    }


def _draw():
    return {
        "hashes": {"draw_identity_sha256": _sha("d")},
        "resource": {
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "path": "tracks/silverstone/object.imb",
            "sha256": _sha("a"),
        },
        "primitive_index": 3,
    }


def _submesh():
    return {
        "external_samplers": [{
            "sampler": "shadowMap",
            "sampler_type": "sampler2D",
            "d3d9_sampler_register": 7,
        }]
    }


def test_snapshot_contract_validates_exact_hashed_rows():
    report = validate_external_sampler_snapshot_contract({
        "format": FORMAT,
        "version": 1,
        "snapshots": [_snapshot()],
    })

    assert report["ready"] is True
    assert report["snapshot_count"] == 1
    row = report["snapshots"][0]
    assert row["d3d9_sampler_register"] == 7
    assert row["texture_sha256"] == _texture_sha(_texture())
    assert len(report["index"]) == 1


def test_snapshot_contract_rejects_texture_hash_mismatch():
    row = _snapshot()
    row["texture_sha256"] = _sha("f")
    report = validate_external_sampler_snapshot_contract({
        "format": FORMAT,
        "version": 1,
        "snapshots": [row],
    })

    assert report["ready"] is False
    assert (
        "external-snapshot:0:texture-sha256-mismatch"
        in report["blocking_reasons"]
    )


def test_snapshot_contract_rejects_duplicate_draw_register_type():
    report = validate_external_sampler_snapshot_contract({
        "format": FORMAT,
        "version": 1,
        "snapshots": [_snapshot(), _snapshot()],
    })

    assert report["ready"] is False
    assert any(
        reason.endswith("duplicate-draw-register-type")
        for reason in report["blocking_reasons"]
    )


def test_resolver_requires_exact_resource_and_primitive_identity():
    contract = validate_external_sampler_snapshot_contract({
        "format": FORMAT,
        "version": 1,
        "snapshots": [_snapshot()],
    })
    textures, blockers, sources = resolve_draw_external_sampler2d_snapshots(
        contract,
        _draw(),
        _submesh(),
    )

    assert blockers == []
    assert list(textures) == [7]
    assert textures[7] == _texture()
    assert sources[0]["draw_identity_sha256"] == _sha("d")
    assert sources[0]["provenance"]["source_kind"] == "runtime-capture"

    wrong = _draw()
    wrong["resource"]["sha256"] = _sha("b")
    textures, blockers, _ = resolve_draw_external_sampler2d_snapshots(
        contract,
        wrong,
        _submesh(),
    )
    assert textures == {}
    assert "external-snapshot:s7:resource-sha256-mismatch" in blockers


def test_absent_contract_is_valid_but_resolves_nothing():
    contract = validate_external_sampler_snapshot_contract(None)
    assert contract["ready"] is True
    assert contract["status"] == "absent"

    textures, blockers, sources = resolve_draw_external_sampler2d_snapshots(
        contract,
        _draw(),
        _submesh(),
    )
    assert textures == {}
    assert blockers == []
    assert sources == []
