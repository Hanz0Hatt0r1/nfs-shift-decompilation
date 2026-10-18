import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recompiled_pcode_vulkan_bridge_evidence_is_explicit_and_bounded() -> None:
    evidence = json.loads(
        (ROOT / "evidence/recompiled_pcode_vulkan_runtime_bridge_20261018.json")
        .read_text(encoding="utf-8")
    )
    fixture_smoke = evidence["vulkan_integration_smoke"]["ci_fixture"]
    full_smoke = evidence["vulkan_integration_smoke"]["full_lowered_library"]
    limitations = evidence["limitations"]

    assert evidence["format"] == "NFSShift.RecompiledPcodeLinuxVulkanRuntimeBridge/1"
    assert evidence["lowered_library"]["exported_functions"] == 41538
    assert evidence["lowered_library"]["smoke_test"] == "passed"
    assert fixture_smoke["pcode_module"] == "native_runtime/tests/recompiled_pcode_fixture.c"
    assert fixture_smoke["frames_rendered"] == fixture_smoke["step_invocations"] == 3
    assert fixture_smoke["pcode_functions_dispatched"] == 6
    assert fixture_smoke["status"] == "ok"
    assert fixture_smoke["validation_enabled"] is True
    assert fixture_smoke["validation_errors"] == 0
    assert full_smoke["library_sha256"] == evidence["lowered_library"]["sha256"]
    assert full_smoke["selected_step"] == "0x00401000"
    assert full_smoke["frames_rendered"] == full_smoke["step_invocations"] == 3
    assert full_smoke["pcode_functions_dispatched"] == 6
    assert full_smoke["status"] == "ok"
    assert full_smoke["validation_enabled"] is True
    assert full_smoke["validation_errors"] == 0
    assert evidence["validation"]["native_runtime_ctest"] == {
        "passed": 138,
        "failed": 0,
    }
    assert limitations["full_game"] is False
    assert limitations["full_pcode_library_used_in_vulkan_integration_smoke"] is True
    assert limitations["platform_imports"] is False
    assert limitations["behavioral_parity"] is False
