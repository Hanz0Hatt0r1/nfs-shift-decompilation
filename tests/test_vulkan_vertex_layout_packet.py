import struct

from vulkan_geometry_packet import ATTRIBUTE, HEADER, export_vulkan_geometry_packet


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "mesh": {
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 52,
                "attributes": [
                    {"property_id": "200", "usage": "POSITION", "usage_index": 0,
                     "location": 0, "offset": 0, "stride": 52,
                     "storage": "FLOAT32x3", "android": "FLOAT32x3",
                     "components": 3, "normalized": False, "element_size": 12,
                     "abi_status": "proven"},
                    {"property_id": "220", "usage": "NORMAL", "usage_index": 0,
                     "location": 1, "offset": 12, "stride": 52,
                     "storage": "FLOAT32x3", "android": "FLOAT32x3",
                     "components": 3, "normalized": False, "element_size": 12,
                     "abi_status": "inferred"},
                    {"property_id": "460", "usage": "COLOR", "usage_index": 0,
                     "location": 2, "offset": 24, "stride": 52,
                     "storage": "UINT8x4", "android": "UINT8x4_BGRA",
                     "components": 4, "normalized": True, "element_size": 4,
                     "abi_status": "proven"},
                    {"property_id": "310", "usage": "BLENDWEIGHT", "usage_index": 0,
                     "location": 3, "offset": 28, "stride": 52,
                     "storage": "FLOAT32x4", "android": "FLOAT32x4",
                     "components": 4, "normalized": False, "element_size": 16,
                     "abi_status": "proven"},
                    {"property_id": "580", "usage": "BLENDINDICES", "usage_index": 0,
                     "location": 4, "offset": 44, "stride": 52,
                     "storage": "UINT8x4", "android": "UINT8x4",
                     "components": 4, "normalized": False, "element_size": 4,
                     "abi_status": "proven"},
                ],
            },
        },
        "submeshes": [{"first_index": 0, "index_count": 3}],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        "normals": [[0.0, 0.0, 1.0]] * 3,
        "colors": [[10, 20, 30, 255], [40, 50, 60, 255], [70, 80, 90, 255]],
        "bone_weights": [[1.0, 0.0, 0.0, 0.0]] * 3,
        "bone_indices": [[0, 1, 2, 3]] * 3,
        "indices": [0, 1, 2],
        "uv_layers": {},
    }


def test_vulkan_packet_contains_all_supported_attributes(tmp_path):
    output = tmp_path / "mesh.svpk"
    report = export_vulkan_geometry_packet(_command(), _mesh(), output)

    assert report["version"] == 2
    assert [row["property_id"] for row in report["attributes"]] == [
        "200", "220", "460", "310", "580"
    ]
    assert report["deferred_properties"] == []

    raw = output.read_bytes()
    header = HEADER.unpack_from(raw)
    assert header[:7] == (b"SVGP", 2, 3, 3, 52, 5, 0)

    attrs = [
        ATTRIBUTE.unpack_from(raw, HEADER.size + i * ATTRIBUTE.size)
        for i in range(5)
    ]
    assert attrs[0] == (0, 2, 0, 52)
    assert attrs[1] == (1, 2, 12, 52)
    assert attrs[2] == (2, 4, 24, 52)
    assert attrs[3] == (3, 3, 28, 52)
    assert attrs[4] == (4, 5, 44, 52)

    vertex_base = HEADER.size + (5 * ATTRIBUTE.size)
    # COLOR0 source bytes are BGRA and are explicitly repacked to RGBA.
    assert raw[vertex_base + 24:vertex_base + 28] == bytes([30, 20, 10, 255])
    assert struct.unpack_from("<4f", raw, vertex_base + 28) == (1.0, 0.0, 0.0, 0.0)
    assert raw[vertex_base + 44:vertex_base + 48] == bytes([0, 1, 2, 3])


def test_vulkan_packet_defers_unresolved_color1():
    command = _command()
    command["mesh"]["vertex_layout"]["buffer_stride"] = 56
    command["mesh"]["vertex_layout"]["attributes"].append({
        "property_id": "461", "usage": "COLOR", "usage_index": 1,
        "location": 5, "offset": 52, "stride": 56,
        "storage": "UINT8x4", "android": "UINT8x4",
        "components": 4, "normalized": True, "element_size": 4,
        "abi_status": "ambiguous",
    })
    report = export_vulkan_geometry_packet(command, _mesh(), __import__("pathlib").Path("/tmp/phase209-color1.svpk"))
    assert "461" in report["deferred_properties"]


def test_vulkan_packet_rejects_missing_required_proven_source(tmp_path):
    command = _command()
    command["mesh"]["vertex_layout"]["attributes"][1]["abi_status"] = "proven"
    _mesh_data = _mesh()
    _mesh_data.pop("normals")
    try:
        export_vulkan_geometry_packet(command, _mesh_data, tmp_path / "bad.svpk")
    except ValueError as error:
        assert "220" in str(error)
    else:
        raise AssertionError("missing proven vertex source must be blocked")
