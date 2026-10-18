import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pe32_vulkan_runtime_evidence_is_explicit_and_bounded() -> None:
    evidence = json.loads(
        (
            ROOT
            / "evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json"
        ).read_text(encoding="utf-8")
    )
    loader = evidence["pe32_guest_loader"]
    fixture = evidence["fixture_validation"]
    smoke = evidence["local_linux_vulkan_smoke"]
    limitations = evidence["limitations"]

    assert evidence["format"] == "NFSShift.RecompiledPcodePe32VulkanRuntime/1"
    assert loader["machine"] == "I386"
    assert loader["optional_header"] == "PE32"
    assert loader["maps_headers"] is True
    assert loader["maps_raw_sections_at_image_base_plus_rva"] is True
    assert loader["zero_fills_virtual_section_tails"] is True
    assert loader["executes_pe_entry_point"] is False
    assert loader["relocations"] is False
    assert loader["imports_and_iat_services"] is False
    assert fixture["result"] == "passed"
    assert fixture["pcode_read_of_mapped_guest_image_verified"] is True
    assert fixture["duplicate_load_rejected"] is True
    assert smoke["frames_rendered"] == smoke["simulation_steps"] == 3
    assert smoke["pcode_step_invocations"] == 3
    assert smoke["pcode_functions_dispatched"] == 6
    assert smoke["status"] == "ok"
    assert smoke["validation_enabled"] is True
    assert smoke["validation_errors"] == 0
    assert evidence["native_runtime_ctest"] == {"passed": 138, "failed": 0}
    assert evidence["python_regressions"] == {
        "passed": 7518,
        "skipped": 3,
        "failed": 0,
    }
    assert limitations["retail_pe_tested"] is False
    assert limitations["playable_game"] is False
    assert limitations["behavioral_parity"] is False
