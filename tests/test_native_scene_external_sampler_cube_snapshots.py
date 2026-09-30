import hashlib
import json

from native_scene_external_sampler_cube_snapshots import (
    FORMAT,
    PROVENANCE_FORMAT,
    reference_cube_sha256,
    resolve_draw_external_sampler_cube_snapshot,
    validate_external_sampler_cube_snapshot_contract,
)
from texture_reference import CUBE_FACES


def _sha(char):
    return char * 64


def _cube():
    faces = {}
    for index, face in enumerate(CUBE_FACES):
        faces[face] = {
            "format": "SHIFT.ReferenceTexture/1",
            "source_format": "D3D9_CAPTURE_PPM",
            "width": 1,
            "height": 1,
            "mipmaps": 1,
            "base_level_only": True,
            "storage": "uncompressed",
            "pixel_format": "RGBA8",
            "pixels": [index, index + 1, index + 2, 255],
            "byte_size": 4,
        }
    return {
        "format": "SHIFT.ReferenceCubeTexture/1",
        "source_format": "D3D9_CAPTURE_PPM_CUBE",
        "width": 1,
        "height": 1,
        "mipmaps": 1,
        "base_level_only": True,
        "storage": "uncompressed",
        "pixel_format": "RGBA8",
        "faces": faces,
        "byte_size": 24,
    }


def _face_sources():
    return {
        face: {
            "snapshot_path": f"frames/s3_face_{face}.ppm",
            "resolved_snapshot_path": f"/capture/s3_face_{face}.ppm",
            "path_resolution": "capture-root-relative",
            "source_sha256": hashlib.sha256(face.encode()).hexdigest(),
        }
        for face in CUBE_FACES
    }


def _source_sha(face_sources):
    hashes = {
        face: face_sources[face]["source_sha256"]
        for face in CUBE_FACES
    }
    return hashlib.sha256(
        json.dumps(
            hashes,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _contract():
    cube = _cube()
    face_sources = _face_sources()
    return {
        "format": FORMAT,
        "version": 1,
        "snapshots": [{
            "draw_identity_sha256": _sha("d"),
            "resource": {
                "archive": "Silverstone_Era3_GrandPrix.bff",
                "path": "tracks/silverstone/object.imb",
                "sha256": _sha("a"),
            },
            "primitive_index": 3,
            "d3d9_sampler_register": 3,
            "sampler_type": "samplerCube",
            "cube": cube,
            "cube_sha256": reference_cube_sha256(cube),
            "provenance": {
                "format": PROVENANCE_FORMAT,
                "source_kind": "D3D9_CAPTURE_PPM_CUBE",
                "source_sha256": _source_sha(face_sources),
                "face_sources": face_sources,
            },
        }],
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
            "sampler": "environmentMap",
            "sampler_type": "samplerCube",
            "d3d9_sampler_register": 3,
        }]
    }


def test_cube_snapshot_contract_validates_exact_scene_identity():
    report = validate_external_sampler_cube_snapshot_contract(_contract())

    assert report["ready"] is True, report["blocking_reasons"]
    assert report["snapshot_count"] == 1
    assert report["snapshots"][0]["cube"]["format"] == (
        "SHIFT.ReferenceCubeTexture/1"
    )


def test_cube_snapshot_resolver_revalidates_resource_and_primitive():
    report = validate_external_sampler_cube_snapshot_contract(_contract())
    cube, blockers, source = resolve_draw_external_sampler_cube_snapshot(
        report,
        _draw(),
        _submesh(),
    )

    assert blockers == []
    assert cube["format"] == "SHIFT.ReferenceCubeTexture/1"
    assert source["register"] == 3
    assert source["sampler_type"] == "samplerCube"
    assert source["resource"]["sha256"] == _sha("a")


def test_cube_snapshot_contract_rejects_non_s3_register():
    value = _contract()
    value["snapshots"][0]["d3d9_sampler_register"] = 4
    report = validate_external_sampler_cube_snapshot_contract(value)

    assert report["ready"] is False
    assert any(
        "sampler-register-not-proven-s3" in reason
        for reason in report["blocking_reasons"]
    )


def test_cube_snapshot_contract_rejects_tampered_face_source_hash():
    value = _contract()
    value["snapshots"][0]["provenance"]["face_sources"]["px"][
        "source_sha256"
    ] = _sha("f")
    report = validate_external_sampler_cube_snapshot_contract(value)

    assert report["ready"] is False
    assert any(
        "provenance-source-sha256-mismatch" in reason
        for reason in report["blocking_reasons"]
    )


def test_cube_snapshot_resolver_blocks_exact_resource_mismatch():
    report = validate_external_sampler_cube_snapshot_contract(_contract())
    draw = _draw()
    draw["resource"]["sha256"] = _sha("b")
    cube, blockers, source = resolve_draw_external_sampler_cube_snapshot(
        report,
        draw,
        _submesh(),
    )

    assert cube is None
    assert source is None
    assert (
        "external-cube-snapshot:s3:resource-sha256-mismatch"
        in blockers
    )
