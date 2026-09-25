import struct

import pytest

from vulkan_constant_packet import HEADER, build_vulkan_constant_packet


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "uniforms": {
                "bindings": [
                    {"name": "Offset", "stage": "vertex", "register_index": 0, "register_count": 1},
                    {"name": "Tint", "stage": "pixel", "register_index": 0, "register_count": 1},
                ]
            },
            "constant_payload": {
                "ready": True,
                "registers": [
                    {"register_index": 0, "values": [0.1, 0.2, 0.0, 0.0]},
                ],
            },
            "constant_commands": [
                {"name": "Offset", "stage": "vertex", "register_index": 0, "register_count": 1},
                {"name": "Tint", "stage": "pixel", "register_index": 0, "register_count": 1},
            ],
        }],
    }


def test_constant_packet_rejects_stage_ambiguous_register(tmp_path):
    result = build_vulkan_constant_packet(_command(), tmp_path / "ambiguous.svcp")
    assert result["ready"] is False
    assert "constant-packet:stage-ambiguous:0" in result["blocking_reasons"]


def test_constant_packet_roundtrip_with_unique_stage_registers(tmp_path):
    command = _command()
    command["submeshes"][0]["constant_commands"] = [
        {"name": "Offset", "stage": "vertex", "register_index": 0, "register_count": 1},
        {"name": "Tint", "stage": "pixel", "register_index": 1, "register_count": 1},
    ]
    command["submeshes"][0]["constant_payload"]["registers"].append(
        {"register_index": 1, "values": [0.2, 0.4, 0.6, 1.0]}
    )

    out = tmp_path / "constants.svcp"
    result = build_vulkan_constant_packet(command, out)
    assert result["ready"] is True
    assert result["banks"]["vertex"]["binding"] == 14
    assert result["banks"]["pixel"]["binding"] == 15
    assert result["banks"]["vertex"]["populated"] == [0]
    assert result["banks"]["pixel"]["populated"] == [1]

    raw = out.read_bytes()
    assert len(raw) == HEADER.size + 8192
    assert HEADER.unpack_from(raw)[:4] == (b"SVCP", 1, 256, 16)
    body = HEADER.size
    assert struct.unpack_from("<4f", raw, body) == (0.1, 0.2, 0.0, 0.0)
    assert struct.unpack_from("<4f", raw, body + 4096 + 16) == (0.2, 0.4, 0.6, 1.0)


def test_constant_packet_rejects_unknown_stage(tmp_path):
    command = _command()
    command["submeshes"][0]["constant_commands"] = [
        {"name": "Bad", "stage": "compute", "register_index": 0, "register_count": 1}
    ]
    result = build_vulkan_constant_packet(command, tmp_path / "bad.svcp")
    assert result["ready"] is False
    assert "constant-packet:unsupported-stage:compute" in result["blocking_reasons"]


@pytest.mark.parametrize("register", [-1, 256])
def test_constant_packet_rejects_out_of_range_register(tmp_path, register):
    command = _command()
    command["submeshes"][0]["constant_commands"] = [{
        "name": "Bad", "stage": "vertex", "register_index": register, "register_count": 1
    }]
    command["submeshes"][0]["constant_payload"]["registers"] = [{
        "register_index": register, "values": [1, 2, 3, 4]
    }]
    result = build_vulkan_constant_packet(command, tmp_path / "bad.svcp")
    assert result["ready"] is False
    assert any("invalid-register" in reason for reason in result["blocking_reasons"])


def test_vulkan_constant_native_contract():
    from pathlib import Path

    source = Path("native_vulkan/src/vulkan_constant_upload.cpp").read_text(encoding="utf-8")
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    vert = Path("native_vulkan/shaders/constants.vert").read_text(encoding="utf-8")
    frag = Path("native_vulkan/shaders/constants.frag").read_text(encoding="utf-8")

    assert "VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER" in source
    assert "vkCreateDescriptorSetLayout" in source
    assert "dstBinding = 14" in source
    assert "dstBinding = 15" in source
    assert "vkUpdateDescriptorSets" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "SHIFT.VulkanConstantUpload/1" in source

    assert "shift_vulkan_constant_upload" in cmake
    assert "constants.vert.spv" in cmake
    assert "constants.frag.spv" in cmake
    assert "layout(set = 0, binding = 14" in vert
    assert "layout(set = 0, binding = 15" in frag
