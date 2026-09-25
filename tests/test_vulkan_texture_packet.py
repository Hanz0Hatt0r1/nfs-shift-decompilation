from pathlib import Path

from vulkan_texture_packet import HEADER, RECORD, build_vulkan_texture_packet


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "textures": [{
                "sampler": "diffuseMap",
                "d3d9_sampler_register": 1,
                "resource_binding_id": 7,
                "texture_id": 12,
                "sampler_id": 4,
                "sampler_state": {
                    "format": "SHIFT.SamplerState/1",
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "address_u": "REPEAT",
                    "address_v": "REPEAT",
                },
            }]
        }],
    }


def _texture():
    return {
        "format": "SHIFT.ReferenceTexture/1",
        "width": 2,
        "height": 2,
        "pixel_format": "RGBA8",
        "pixels": [255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255, 255, 255, 255],
    }


def test_vulkan_texture_packet_roundtrip(tmp_path):
    output = tmp_path / "texture.svtp"
    result = build_vulkan_texture_packet(
        _command(),
        {"1": _texture()},
        output,
    )
    assert result["format"] == "SHIFT.VulkanTexturePacket/1"
    assert result["descriptor_set"] == 1
    assert result["texture_count"] == 1
    assert result["textures"][0]["register"] == 1
    assert result["textures"][0]["sampler_mode"] == 2

    raw = output.read_bytes()
    header = HEADER.unpack_from(raw)
    assert header[:4] == (b"SVTP", 1, 1, 1)
    record = RECORD.unpack_from(raw, HEADER.size)
    assert record[0:3] == (1, 2, 2)
    assert record[4] == 16
    assert len(raw) == HEADER.size + RECORD.size + 16


def test_vulkan_texture_packet_rejects_unsupported_sampler_addressing(tmp_path):
    command = _command()
    command["submeshes"][0]["textures"][0]["sampler_state"]["address_v"] = "MIRRORED_REPEAT"
    try:
        build_vulkan_texture_packet(command, {"1": _texture()}, tmp_path / "bad.svtp")
    except ValueError as error:
        assert "matching REPEAT or CLAMP_TO_EDGE" in str(error)
    else:
        raise AssertionError("unsupported sampler addressing must be blocked")


def test_vulkan_texture_packet_rejects_missing_sampler_source(tmp_path):
    command = {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "textures": [{
                "d3d9_sampler_register": 1,
                "resource_binding_id": 7,
                "texture_id": 12,
                "sampler_id": 4,
            }]
        }],
    }
    try:
        build_vulkan_texture_packet(command, {}, tmp_path / "bad.svtp")
    except ValueError as error:
        assert "missing texture reference image" in str(error)
    else:
        raise AssertionError("missing sampler image must be blocked")


def test_vulkan_texture_native_contract():
    source = Path("native_vulkan/src/vulkan_texture_upload.cpp").read_text(encoding="utf-8")
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    frag = Path("native_vulkan/shaders/texture.frag").read_text(encoding="utf-8")

    assert "VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER" in source
    assert "vkCreateSampler" in source
    assert "vkCmdCopyBufferToImage" in source
    assert "VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL" in source
    assert "vkUpdateDescriptorSets" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "SHIFT.VulkanTextureUpload/1" in source
    assert "shift_vulkan_texture_upload" in cmake
    assert "texture.vert.spv" in cmake
    assert "texture.frag.spv" in cmake
    assert "layout(set = 1, binding = 1)" in frag
