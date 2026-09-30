import json

from vulkan_bundle_spirv import compile_bmw_vulkan_bundle


def test_spirv_gate_accepts_neutral_vulkan_draw_bundle(tmp_path):
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps({
            "format": "SHIFT.VulkanDrawBundle/1",
            "artifacts": {"shaders": []},
        }),
        encoding="utf-8",
    )

    report = compile_bmw_vulkan_bundle(
        tmp_path,
        validator="fake-glslangValidator",
    )

    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["source_bundle_format"] == "SHIFT.VulkanDrawBundle/1"


def test_spirv_gate_still_rejects_unknown_bundle_format(tmp_path):
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps({
            "format": "SHIFT.Other/1",
            "artifacts": {"shaders": []},
        }),
        encoding="utf-8",
    )

    try:
        compile_bmw_vulkan_bundle(
            tmp_path,
            validator="fake-glslangValidator",
        )
    except ValueError as error:
        assert "SHIFT.VulkanDrawBundle/1" in str(error)
    else:
        raise AssertionError("unknown bundle format was accepted")
