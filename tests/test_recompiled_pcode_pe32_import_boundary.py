import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pe32_import_boundary_evidence_names_and_bounds_stubs() -> None:
    evidence = json.loads(
        (
            ROOT
            / "evidence/recompiled_pcode_pe32_import_boundary_20261018.json"
        ).read_text(encoding="utf-8")
    )
    fixture = evidence["pe_fixture"]
    smoke = evidence["local_linux_vulkan_smoke"]
    limitations = evidence["limitations"]

    assert evidence["format"] == "NFSShift.RecompiledPcodePe32ImportBoundary/1"
    assert fixture["import_modules"] == ["KERNEL32.dll"]
    assert fixture["imported_functions"] == [
        "KERNEL32.dll!Sleep",
        "KERNEL32.dll!#123",
    ]
    assert [slot["guest_value"] for slot in fixture["iat_slots"]] == [
        "0xf0000000",
        "0xf0000010",
    ]
    assert fixture["import_trap_calls_fail_closed"] is True
    assert fixture["observed_error"] == "unimplemented PE import KERNEL32.dll!Sleep"
    assert fixture["api_implementation"] is False
    assert smoke["frames_rendered"] == smoke["simulation_steps"] == 3
    assert smoke["pcode_step_invocations"] == 3
    assert smoke["pcode_functions_dispatched"] == 6
    assert smoke["validation_enabled"] is True
    assert smoke["validation_errors"] == 0
    assert evidence["native_runtime_ctest"] == {"passed": 138, "failed": 0}
    assert evidence["python_regressions"] == {
        "passed": 7519,
        "skipped": 3,
        "failed": 0,
    }
    assert limitations["imported_api_execution"] is False
    assert limitations["playable_game"] is False
