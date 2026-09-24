from pathlib import Path


def test_runtime_capture_runner_exposes_sampler_snapshot_switch():
    script = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    assert "[switch]$CaptureTextureSnapshots" in script
    assert '[string]$TextureStages = "0,3,4"' in script
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT" in script
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR" in script
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_STAGES" in script
    assert "frames" in script
    assert "textures" in script
