from pathlib import Path

def test_linux_vulkan_workflow_and_smoke_contract():
    workflow = Path(".github/workflows/linux-vulkan.yml").read_text(encoding="utf-8")
    smoke = Path("tools/run_linux_vulkan_smoke.py").read_text(encoding="utf-8")
    assert "mesa-vulkan-drivers" in workflow
    assert "glslang-tools" in workflow
    assert "shift_vulkan_bundle_execute" in smoke
    assert "sampler2D" in smoke
    assert "samplerCube" in smoke
    assert "P6" in smoke


def test_linux_vulkan_smoke_runner_resolves_repository_root():
    smoke = Path("tools/run_linux_vulkan_smoke.py").read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[1]" in smoke
    assert "sys.path.insert(0, str(REPOSITORY_ROOT))" in smoke
