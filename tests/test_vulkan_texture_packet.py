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
    assert "1,1,&set" in source
    assert "setLayoutCount=2" in source
    assert "SHIFT.VulkanTextureUpload/1" in source
    assert "shift_vulkan_texture_upload" in cmake
    assert "texture.vert.spv" in cmake
    assert "texture.frag.spv" in cmake
    assert "layout(set = 1, binding = 1)" in frag


def _command_with_external_2d(*, sampler_state=True):
    command = _command()
    row = {
        "sampler": "shadowMap",
        "sampler_type": "sampler2D",
        "d3d9_sampler_register": 7,
    }
    if sampler_state:
        row["sampler_state"] = {
            "format": "SHIFT.SamplerState/1",
            "min_filter": "LINEAR",
            "mag_filter": "LINEAR",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        }
    command["submeshes"][0]["external_samplers"] = [row]
    return command


def test_vulkan_texture_packet_transports_explicit_external_sampler2d(tmp_path):
    output = tmp_path / "external.svtp"
    result = build_vulkan_texture_packet(
        _command_with_external_2d(),
        {"1": _texture()},
        output,
        external_textures={"7": _texture()},
    )

    assert result["texture_count"] == 2
    assert result["material_texture_count"] == 1
    assert result["external_texture_count"] == 1
    assert [row["register"] for row in result["textures"]] == [1, 7]
    external = result["textures"][1]
    assert external["source_kind"] == "external"
    assert external["sampler"] == "shadowMap"
    assert external["sampler_mode"] == 4

    raw = output.read_bytes()
    header = HEADER.unpack_from(raw)
    assert header[:4] == (b"SVTP", 1, 2, 1)
    first = RECORD.unpack_from(raw, HEADER.size)
    second = RECORD.unpack_from(raw, HEADER.size + RECORD.size)
    assert first[0] == 1
    assert second[0] == 7


def test_vulkan_texture_packet_does_not_require_unsupplied_external_sampler(tmp_path):
    output = tmp_path / "material-only.svtp"
    result = build_vulkan_texture_packet(
        _command_with_external_2d(),
        {"1": _texture()},
        output,
    )

    assert result["texture_count"] == 1
    assert result["external_texture_count"] == 0
    assert result["textures"][0]["register"] == 1


def test_vulkan_texture_packet_rejects_external_snapshot_without_declaration(tmp_path):
    try:
        build_vulkan_texture_packet(
            _command(),
            {"1": _texture()},
            tmp_path / "bad-external.svtp",
            external_textures={"7": _texture()},
        )
    except ValueError as error:
        assert "no sampler2D declaration: s7" in str(error)
    else:
        raise AssertionError("undeclared external sampler snapshot was accepted")


def test_vulkan_texture_packet_requires_explicit_external_sampler_state(tmp_path):
    try:
        build_vulkan_texture_packet(
            _command_with_external_2d(sampler_state=False),
            {"1": _texture()},
            tmp_path / "bad-state.svtp",
            external_textures={"7": _texture()},
        )
    except ValueError as error:
        assert "requires explicit sampler_state" in str(error)
    else:
        raise AssertionError("external sampler snapshot without state was accepted")
