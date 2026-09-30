import json
import struct
from pathlib import Path

import pytest

from vulkan_geometry_packet import HEADER, ATTRIBUTE, export_vulkan_geometry_packet


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": False,
        "blocking_reasons": ["shader-not-ready"],
        "mesh": {
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
                }],
            },
        },
        "submeshes": [
            {"first_index": 3, "index_count": 3},
            {"first_index": 0, "index_count": 3},
        ],
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


def test_export_vulkan_geometry_packet_materializes_selected_submesh(tmp_path):
    output = tmp_path / "mesh.svpk"
    report = export_vulkan_geometry_packet(_command(), _mesh(), output, submesh_index=1)

    assert report["format"] == "SHIFT.VulkanGeometryPacket/1"
    assert report["command_ready"] is False
    assert report["source_first_index"] == 0
    assert report["first_index"] == 0
    assert report["index_count"] == 3
    assert report["vertex_count"] == 4
    assert report["deferred_properties"] == []

    raw = output.read_bytes()
    assert len(raw) == HEADER.size + ATTRIBUTE.size + (4 * 12) + (3 * 4)
    header = HEADER.unpack_from(raw)
    assert header[:7] == (b"SVGP", 2, 4, 3, 12, 1, 0)
    attribute = ATTRIBUTE.unpack_from(raw, HEADER.size)
    assert attribute == (0, 2, 0, 12)

    indices_offset = HEADER.size + ATTRIBUTE.size + 48
    assert struct.unpack_from("<3I", raw, indices_offset) == (0, 1, 2)


def test_export_vulkan_geometry_packet_rejects_non_zero_position_location(tmp_path):
    command = _command()
    command["mesh"]["vertex_layout"]["attributes"][0]["location"] = 2
    try:
        export_vulkan_geometry_packet(command, _mesh(), tmp_path / "bad.svpk")
    except ValueError as error:
        assert "location 0" in str(error)
    else:
        raise AssertionError("non-zero POSITION location must be blocked")


def test_export_vulkan_geometry_packet_rejects_non_triangle_range(tmp_path):
    command = _command()
    command["submeshes"] = [{"first_index": 0, "index_count": 4}]
    try:
        export_vulkan_geometry_packet(command, _mesh(), tmp_path / "bad.svpk")
    except ValueError as error:
        assert "triangle-list" in str(error)
    else:
        raise AssertionError("non-triangle-list submesh must be blocked")


def test_export_vulkan_geometry_packet_bakes_row_vector_scene_transform(
    tmp_path,
):
    command = _command()
    command["world_matrix"] = [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]
    command["mesh"]["vertex_count"] = 3
    command["mesh"]["triangle_count"] = 1
    command["mesh"]["vertex_layout"]["buffer_stride"] = 36
    command["mesh"]["vertex_layout"]["attributes"] = [
        {
            "property_id": "200",
            "usage": "POSITION",
            "usage_index": 0,
            "location": 0,
            "offset": 0,
            "stride": 36,
            "storage": "FLOAT32x3",
            "android": "FLOAT32x3",
            "element_size": 12,
            "abi_status": "proven",
        },
        {
            "property_id": "220",
            "location": 1,
            "offset": 12,
            "stride": 36,
            "storage": "FLOAT32x3",
            "android": "FLOAT32x3",
            "element_size": 12,
            "abi_status": "proven",
        },
        {
            "property_id": "240",
            "location": 2,
            "offset": 24,
            "stride": 36,
            "storage": "FLOAT32x3",
            "android": "FLOAT32x3",
            "element_size": 12,
            "abi_status": "proven",
        },
    ]
    command["submeshes"] = [{"first_index": 0, "index_count": 3}]
    mesh = {
        "format": "SHIFT.NeutralMesh/1",
        "vertices": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        "normals": [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        "tangents": [
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        "indices": [0, 1, 2],
    }
    output = tmp_path / "scene.svpk"
    report = export_vulkan_geometry_packet(
        command,
        mesh,
        output,
        apply_world_matrix=True,
    )

    assert report["scene_transform"]["executed"] is True
    assert report["scene_transform"]["mode"] == (
        "cpu-baked-row-vector-affine"
    )
    assert report["scene_transform"]["transformed_properties"] == [
        "200", "220", "240"
    ]
    assert report["normalization"]["source_space"] == "scene world space"

    raw = output.read_bytes()
    vertex_offset = HEADER.size + 3 * ATTRIBUTE.size
    position = struct.unpack_from("<3f", raw, vertex_offset)
    normal = struct.unpack_from("<3f", raw, vertex_offset + 12)
    tangent = struct.unpack_from("<3f", raw, vertex_offset + 24)
    assert position == pytest.approx((10.0, 21.0, 30.0))
    assert normal == pytest.approx((0.0, 1.0, 0.0))
    assert tangent == pytest.approx((-1.0, 0.0, 0.0))


def test_export_vulkan_geometry_packet_rejects_non_affine_scene_matrix(
    tmp_path,
):
    command = _command()
    command["world_matrix"] = [
        1.0, 0.0, 0.0, 0.25,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    try:
        export_vulkan_geometry_packet(
            command,
            _mesh(),
            tmp_path / "bad-scene.svpk",
            apply_world_matrix=True,
        )
    except ValueError as error:
        assert "affine" in str(error)
    else:
        raise AssertionError("non-affine scene matrix was accepted")
