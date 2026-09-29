import json

import pytest

from bmw_vulkan_bundle import TARGET_MEB
from bmw_vulkan_bundle_set import FORMAT, build_bmw_vulkan_bundle_set


def _shader(tag):
    return {
        "vertex": f"#version 450\n// {tag} vertex\nvoid main(){{}}",
        "pixel": f"#version 450\n// {tag} pixel\nvoid main(){{}}",
        "source_payload_sha256": (tag * 64)[:64],
        "permutation_identity": {
            "format": "SHIFT.ShaderPermutationIdentity/1",
            "identity_sha256": ((tag.upper() or "A") * 64)[:64],
        },
    }


def _command():
    return {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [{
            "format": "SHIFT.RenderCommand/1",
            "ready": True,
            "validation": {"valid": True, "blocking_reasons": []},
            "mesh": {
                "ref": TARGET_MEB,
                "resolved": {"resource_sha256": "a" * 64},
                "vertex_count": 4,
                "triangle_count": 2,
                "vertex_layout": {
                    "format": "SHIFT.VertexLayout/1",
                    "buffer_stride": 12,
                    "attributes": [{
                        "property_id": "200",
                        "usage": "POSITION",
                        "usage_index": 0,
                        "location": 0,
                        "offset": 0,
                        "stride": 12,
                        "storage": "FLOAT32x3",
                        "android": "FLOAT32x3",
                        "components": 3,
                        "normalized": False,
                        "element_size": 12,
                        "abi_status": "proven",
                    }],
                },
            },
            "submeshes": [
                {
                    "shader": _shader("a"),
                    "constant_commands": [],
                    "constant_payload": {
                        "format": "SHIFT.MaterialConstantPayload/1",
                        "registers": [],
                        "ready": True,
                    },
                    "textures": [],
                    "external_samplers": [],
                    "first_index": 0,
                    "index_count": 3,
                },
                {
                    "shader": _shader("b"),
                    "constant_commands": [],
                    "constant_payload": {
                        "format": "SHIFT.MaterialConstantPayload/1",
                        "registers": [],
                        "ready": True,
                    },
                    "textures": [],
                    "external_samplers": [],
                    "first_index": 3,
                    "index_count": 3,
                },
            ],
        }],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [
            [-1.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [1.0, 1.0, 0.0],
            [-1.0, 1.0, 0.0],
        ],
        "indices": [0, 1, 2, 0, 2, 3],
    }


def test_bundle_set_preserves_draw_order_and_atomic_bundle_abi(tmp_path):
    result = build_bmw_vulkan_bundle_set(
        _command(), _mesh(), tmp_path
    )

    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["draw_count"] == 2
    assert [row["source_submesh_index"] for row in result["draws"]] == [0, 1]
    assert [row["first_index"] for row in result["draws"]] == [0, 3]
    assert [row["index_count"] for row in result["draws"]] == [3, 3]

    for index in (0, 1):
        child = tmp_path / "draws" / f"submesh_{index:03d}"
        assert (child / "geometry.svpk").is_file()
        assert (child / "constants.svcp").is_file()
        manifest = json.loads((child / "bundle_manifest.json").read_text(encoding="utf-8"))
        assert manifest["format"] == "SHIFT.BMWVulkanBundle/1"
        assert manifest["source"]["submesh_index"] == index

    persisted = json.loads(
        (tmp_path / "bundle_set_manifest.json").read_text(encoding="utf-8")
    )
    assert persisted["format"] == FORMAT
    assert persisted["draw_count"] == 2
    assert (tmp_path / "bundle_set.paths").read_text(encoding="utf-8").splitlines() == [
        "draws/submesh_000",
        "draws/submesh_001",
    ]
    assert persisted["artifacts"]["draw_order"]["entry_count"] == 2


def test_bundle_set_can_preserve_explicit_non_numeric_draw_order(tmp_path):
    result = build_bmw_vulkan_bundle_set(
        _command(), _mesh(), tmp_path, submesh_indices=[1, 0]
    )
    assert [row["source_submesh_index"] for row in result["draws"]] == [1, 0]
    assert [row["draw_order"] for row in result["draws"]] == [0, 1]
    assert (tmp_path / "bundle_set.paths").read_text(encoding="utf-8").splitlines() == [
        "draws/submesh_001",
        "draws/submesh_000",
    ]


def test_bundle_set_propagates_atomic_gate_failure(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][1]["shader"].pop(
        "source_payload_sha256"
    )

    result = build_bmw_vulkan_bundle_set(command, _mesh(), tmp_path)

    assert result["ready"] is False
    assert result["draws"][0]["ready"] is True
    assert result["draws"][1]["ready"] is False
    assert any(
        reason.startswith(
            "bundle-set:submesh-1:native-submission:shader-payload-identity-missing"
        )
        for reason in result["blocking_reasons"]
    )


def test_bundle_set_rejects_duplicate_or_out_of_range_indices(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        build_bmw_vulkan_bundle_set(
            _command(), _mesh(), tmp_path / "dup", submesh_indices=[0, 0]
        )
    with pytest.raises(ValueError, match="out of range"):
        build_bmw_vulkan_bundle_set(
            _command(), _mesh(), tmp_path / "bad", submesh_indices=[2]
        )
