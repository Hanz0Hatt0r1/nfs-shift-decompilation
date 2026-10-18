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


def test_kernel32_crt_startup_evidence_tracks_vulkan_entrypoint_progress() -> None:
    evidence = json.loads(
        (
            ROOT
            / "evidence/recompiled_pcode_kernel32_crt_startup_20261018.json"
        ).read_text(encoding="utf-8")
    )
    runtime = evidence["local_linux_vulkan_smoke"]
    retail = evidence["retail_entrypoint_probe"]

    assert evidence["format"] == "NFSShift.RecompiledPcodeKernel32CrtStartup/1"
    assert evidence["runtime_changes"]["kernel32_static_imports"] == 46
    assert evidence["runtime_changes"]["x86_register_bank_bytes"] == 8192
    assert runtime["entrypoint_invocations"] == 1
    assert runtime["frames_rendered"] == runtime["simulation_steps"] == 3
    assert runtime["pcode_step_invocations"] == 3
    assert runtime["pcode_functions_dispatched"] == 7
    assert runtime["validation_enabled"] is True
    assert runtime["validation_errors"] == 0
    assert runtime["status"] == "ok"
    assert retail["pcode_functions_dispatched"] == 552
    assert retail["next_blocker"] == "missing generated P-code export rvi_00900f48"
    assert evidence["limitations"]["playable_game"] is False
