from pathlib import Path

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle
from vulkan_bundle_spirv import compile_bmw_vulkan_bundle


def _binding():
    return {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [{
            "format": "SHIFT.RenderCommand/1",
            "mesh": {
                "ref": TARGET_MEB,
                "resolved": {"resource_sha256": "a" * 64},
                "vertex_count": 3,
                "triangle_count": 1,
            },
            "submeshes": [{
                "shader": {
                    "vertex": "#version 450\nvoid main(){gl_Position=vec4(0.0);}",
                    "pixel": "#version 450\nlayout(location=0) out vec4 o; void main(){o=vec4(1.0);}",
                },
                "constant_commands": [],
                "constant_payload": {"registers": [], "ready": True},
                "textures": [],
                "external_samplers": [],
                "first_index": 0,
                "index_count": 3,
            }],
        }],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "indices": [0, 1, 2],
    }


def test_bundle_preserves_selected_command_metadata(tmp_path):
    result = build_bmw_vulkan_bundle(_binding(), _mesh(), tmp_path)
    assert result["source"]["render_command_format"] == "SHIFT.RenderCommand/1"
    assert result["source"]["mesh_ref"] == TARGET_MEB
    assert result["target"]["vertex_count"] == 3
    assert result["target"]["triangle_count"] == 1


def test_spirv_compile_reports_unavailable(monkeypatch, tmp_path):
    build_bmw_vulkan_bundle(_binding(), _mesh(), tmp_path)
    monkeypatch.setattr("shutil.which", lambda _name: None)
    result = compile_bmw_vulkan_bundle(tmp_path)
    assert result["format"] == "SHIFT.VulkanBundleSPIRV/1"
    assert result["status"] == "unavailable"
    assert result["ready"] is False


def test_spirv_compile_uses_supplied_validator(monkeypatch, tmp_path):
    build_bmw_vulkan_bundle(_binding(), _mesh(), tmp_path)

    def fake_run(command, **kwargs):
        output = Path(command[command.index("-o") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"SPIRV")
        return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = compile_bmw_vulkan_bundle(tmp_path, validator="/fake/glslangValidator")
    assert result["ready"] is True
    assert len(result["shader_results"]) == 2
    assert all(row["status"] == "compiled" for row in result["shader_results"])
    assert all(row["spirv_sha256"] for row in result["shader_results"])


def test_spirv_compile_fails_closed_on_compiler_error(monkeypatch, tmp_path):
    build_bmw_vulkan_bundle(_binding(), _mesh(), tmp_path)

    def fake_run(command, **kwargs):
        return type("Completed", (), {"returncode": 7, "stdout": "", "stderr": "bad shader"})()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = compile_bmw_vulkan_bundle(tmp_path, validator="/fake/glslangValidator")
    assert result["ready"] is False
    assert result["shader_results"][0]["status"] == "failed"
    assert "vulkan-bundle-spirv:compile-failed:shaders/submesh_0.vertex.glsl" in result["blocking_reasons"]
