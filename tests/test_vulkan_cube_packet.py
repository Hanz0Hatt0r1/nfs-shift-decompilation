from pathlib import Path

from vulkan_cube_packet import HEADER, build_vulkan_cube_packet


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "external_samplers": [{
                "sampler": "environmentMap",
                "sampler_type": "samplerCube",
                "d3d9_sampler_register": 3,
                "sampler_state": {
                    "min_filter": "Linear",
                    "mag_filter": "Linear",
                    "address_u": "Clamp",
                    "address_v": "Clamp",
                    "address_w": "Clamp",
                },
            }]
        }],
    }


def _cube():
    faces = {}
    colors = {
        "px": [255, 0, 0, 255],
        "nx": [0, 255, 0, 255],
        "py": [0, 0, 255, 255],
        "ny": [255, 255, 0, 255],
        "pz": [255, 0, 255, 255],
        "nz": [0, 255, 255, 255],
    }
    for face, color in colors.items():
        faces[face] = {
            "format": "SHIFT.ReferenceTexture/1",
            "width": 1,
            "height": 1,
            "pixel_format": "RGBA8",
            "pixels": color,
        }
    return {"format": "SHIFT.ReferenceCubeTexture/1", "faces": faces}


def test_cube_packet_roundtrip(tmp_path):
    output = tmp_path / "cube.svcp"
    result = build_vulkan_cube_packet(_command(), _cube(), output)
    assert result["format"] == "SHIFT.VulkanCubeTexturePacket/1"
    assert result["descriptor_set"] == 1
    assert result["register"] == 3
    assert result["view_type"] == "VK_IMAGE_VIEW_TYPE_CUBE"
    assert [row["face"] for row in result["faces"]] == ["px", "nx", "py", "ny", "pz", "nz"]

    raw = output.read_bytes()
    assert HEADER.unpack_from(raw)[:6] == (b"SVCP", 1, 3, 1, 1, 6)
    assert len(raw) == HEADER.size + 6 * 4


def test_cube_packet_rejects_wrong_render_sampler(tmp_path):
    command = _command()
    command["submeshes"][0]["external_samplers"][0]["d3d9_sampler_register"] = 1
    try:
        build_vulkan_cube_packet(command, _cube(), tmp_path / "bad.svcp")
    except ValueError as error:
        assert "samplerCube" in str(error)
    else:
        raise AssertionError("environment cube must remain bound to s3")


def test_cube_packet_rejects_missing_face(tmp_path):
    cube = _cube()
    cube["faces"].pop("nz")
    try:
        build_vulkan_cube_packet(_command(), cube, tmp_path / "bad.svcp")
    except ValueError as error:
        assert "faces mismatch" in str(error)
    else:
        raise AssertionError("missing cube face must be blocked")


def test_cube_packet_rejects_non_clamp_sampler(tmp_path):
    command = _command()
    command["submeshes"][0]["external_samplers"][0]["sampler_state"]["address_w"] = "Wrap"
    try:
        build_vulkan_cube_packet(command, _cube(), tmp_path / "bad.svcp")
    except ValueError as error:
        assert "CLAMP_TO_EDGE" in str(error)
    else:
        raise AssertionError("environment cube must use explicit clamp addressing")


def test_vulkan_cube_native_contract():
    source = Path("native_vulkan/src/vulkan_sampler_cube.cpp").read_text(encoding="utf-8")
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    frag = Path("native_vulkan/shaders/cube.frag").read_text(encoding="utf-8")

    assert "VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT" in source
    assert "VK_IMAGE_VIEW_TYPE_CUBE" in source
    assert "arrayLayers=6" in source or "arrayLayers = 6" in source
    assert "VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER" in source
    assert "dstBinding=3" in source
    assert "vkCmdCopyBufferToImage" in source
    assert "shift_vulkan_sampler_cube" in cmake
    assert "cube.vert.spv" in cmake
    assert "cube.frag.spv" in cmake
    assert "layout(set = 1, binding = 3)" in frag
