from pathlib import Path

from vulkan_render_command import run_vulkan_render_command


def _binding():
    return {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [{
            "format": "SHIFT.RenderCommand/1",
            "ready": False,
            "blocking_reasons": ["shader-not-ready"],
            "mesh": {
                "ref": "vehicles/test/body.meb",
                "vertex_count": 3,
                "triangle_count": 1,
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
            "submeshes": [{"first_index": 0, "index_count": 3}],
        }],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        "indices": [0, 1, 2],
    }


def test_vulkan_runner_prepare_only(tmp_path):
    result = run_vulkan_render_command(
        _binding(),
        _mesh(),
        tmp_path / "triangle.svpk",
        tmp_path / "triangle.ppm",
        prepare_only=True,
    )

    assert result["format"] == "SHIFT.VulkanRenderCommandRunner/1"
    assert result["status"] == "prepared"
    assert result["command"]["ready"] is False
    assert result["packet"]["version"] == 2
    assert result["packet"]["attribute_count"] == 1
    assert result["render"]["status"] == "not-run"
    assert len(result["packet"]["sha256"]) == 64


def test_vulkan_runner_blocks_missing_native_executable(tmp_path):
    result = run_vulkan_render_command(
        _binding(),
        _mesh(),
        tmp_path / "triangle.svpk",
        tmp_path / "triangle.ppm",
        executable=tmp_path / "missing-vulkan",
    )
    assert result["status"] == "blocked"
    assert result["render"]["status"] == "executable-missing"
    assert "vulkan-runner:executable-missing" in result["blocking_reasons"]


def test_vulkan_runner_rejects_wrong_render_binding(tmp_path):
    bad = dict(_binding())
    bad["format"] = "SHIFT.NotRenderBinding/1"
    try:
        run_vulkan_render_command(
            bad,
            _mesh(),
            tmp_path / "bad.svpk",
            tmp_path / "bad.ppm",
            prepare_only=True,
        )
    except ValueError as error:
        assert "RenderBinding" in str(error)
    else:
        raise AssertionError("wrong RenderBinding format must be rejected")
