import json

from bmw_vulkan_bundle import TARGET_MEB
from vulkan_bundle_interface_gate import validate_bmw_vulkan_interface


def _manifest(tmp_path):
    (tmp_path / "bundle_manifest.json").write_text(json.dumps({
        "format": "SHIFT.BMWVulkanBundle/1",
        "artifacts": {"shaders": []},
        "source": {"mesh_ref": TARGET_MEB},
    }), encoding="utf-8")


def _report(descriptors):
    return {
        "format": "SHIFT.VulkanBundleSPIRV/1",
        "ready": True,
        "blocking_reasons": [],
        "shader_results": [{
            "path": "shaders/submesh_0.pixel.glsl",
            "stage": "pixel",
            "reflection": {
                "ready": True,
                "descriptors": descriptors,
            },
        }],
    }


def _write_texture_packet(tmp_path, registers):
    data = bytearray(b"SVTP")
    data.extend((1).to_bytes(4, "little"))
    data.extend((len(registers)).to_bytes(4, "little"))
    data.extend((1).to_bytes(4, "little"))
    data.extend((0).to_bytes(4, "little"))
    for register in registers:
        data.extend(int(register).to_bytes(4, "little"))
        data.extend((1).to_bytes(4, "little"))
        data.extend((1).to_bytes(4, "little"))
        data.extend((20 + len(registers) * 24).to_bytes(4, "little"))
        data.extend((4).to_bytes(4, "little"))
        data.extend((2).to_bytes(4, "little"))
    (tmp_path / "textures.svtp").write_bytes(data)


def _write_cube_packet(tmp_path):
    header = (
        b"SVCP"
        + (1).to_bytes(4, "little")
        + (3).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
        + (6).to_bytes(4, "little")
        + (4).to_bytes(4, "little")
    )
    (tmp_path / "environment_cube.svcp").write_bytes(header + b"\0" * 24)


def test_interface_gate_accepts_constants_2d_and_cube(tmp_path):
    _manifest(tmp_path)
    _write_texture_packet(tmp_path, [0, 1, 2, 4])
    _write_cube_packet(tmp_path)
    report = _report([
        {"set": 0, "binding": 14, "descriptor_type": "uniform-buffer", "resource_type": "uniform-block", "stage": "vertex"},
        {"set": 0, "binding": 15, "descriptor_type": "uniform-buffer", "resource_type": "uniform-block", "stage": "fragment"},
        {"set": 1, "binding": 0, "descriptor_type": "combined-image-sampler", "resource_type": "sampler2D", "stage": "fragment"},
        {"set": 1, "binding": 3, "descriptor_type": "combined-image-sampler", "resource_type": "samplerCube", "stage": "fragment"},
        {"set": 1, "binding": 4, "descriptor_type": "combined-image-sampler", "resource_type": "sampler2D", "stage": "fragment"},
    ])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is True
    assert result["blocking_reasons"] == []


def test_interface_gate_blocks_missing_cube(tmp_path):
    _manifest(tmp_path)
    report = _report([{
        "set": 1,
        "binding": 3,
        "descriptor_type": "combined-image-sampler",
        "resource_type": "samplerCube",
        "stage": "fragment",
    }])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is False
    assert "vulkan-interface:missing-cube-resource:s3" in result["blocking_reasons"]


def test_interface_gate_blocks_unsupported_set(tmp_path):
    _manifest(tmp_path)
    report = _report([{
        "set": 2,
        "binding": 1,
        "descriptor_type": "combined-image-sampler",
        "resource_type": "sampler2D",
        "stage": "fragment",
    }])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is False
    assert "vulkan-interface:unsupported-descriptor-set:2" in result["blocking_reasons"]


def test_interface_gate_rejects_constant_binding_used_by_wrong_stage(tmp_path):
    _manifest(tmp_path)
    report = _report([{
        "set": 0,
        "binding": 14,
        "descriptor_type": "uniform-buffer",
        "resource_type": "uniform-block",
        "stage": "fragment",
    }])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is False
    assert "vulkan-interface:set0-stage-mismatch:14:fragment" in result["blocking_reasons"]


def test_interface_gate_rejects_vertex_stage_texture_descriptor(tmp_path):
    _manifest(tmp_path)
    _write_texture_packet(tmp_path, [1])
    report = _report([{
        "set": 1,
        "binding": 1,
        "descriptor_type": "combined-image-sampler",
        "resource_type": "sampler2D",
        "stage": "vertex",
    }])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is False
    assert "vulkan-interface:set1-stage-unsupported:1:vertex" in result["blocking_reasons"]


def test_interface_gate_rejects_duplicate_reflected_descriptor(tmp_path):
    _manifest(tmp_path)
    _write_texture_packet(tmp_path, [1])
    report = _report([
        {"set": 1, "binding": 1, "descriptor_type": "combined-image-sampler",
         "resource_type": "sampler2D", "stage": "fragment"},
        {"set": 1, "binding": 1, "descriptor_type": "combined-image-sampler",
         "resource_type": "sampler2D", "stage": "fragment"},
    ])
    result = validate_bmw_vulkan_interface(tmp_path, report)
    assert result["ready"] is False
    assert "vulkan-interface:duplicate-reflected-descriptor" in result["blocking_reasons"]
