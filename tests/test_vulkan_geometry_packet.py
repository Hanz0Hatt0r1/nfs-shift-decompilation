import json
import struct
from pathlib import Path

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
