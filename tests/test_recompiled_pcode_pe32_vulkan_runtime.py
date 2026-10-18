import hashlib
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
    ci_smoke = evidence["ci_linux_vulkan_smoke"]
    limitations = evidence["limitations"]

    assert evidence["format"] == "NFSShift.RecompiledPcodePe32VulkanRuntime/1"
    assert loader["machine"] == "I386"
    assert loader["optional_header"] == "PE32"
    assert loader["maps_headers"] is True
    assert loader["maps_raw_sections_at_image_base_plus_rva"] is True
    assert loader["zero_fills_virtual_section_tails"] is True
    assert loader["executes_pe_entry_point"] is True
    assert loader["relocations"] is False
    assert loader["imports_and_iat_services"] is True
    assert loader["supplemental_pcode_modules"] is True
    assert loader["static_import_fixture_scope"] == {
        "KERNEL32.dll": 71,
        "imagehlp.dll": 3,
        "total_functions": 74,
    }
    assert fixture["result"] == "passed"
    assert fixture["mapped_image_size"] == 12288
    assert fixture["entry_point"] == "0x00401020"
    assert fixture["import_module_count"] == 2
    assert fixture["import_function_count"] == 74
    assert fixture["supplemental_module_loading_verified"] is True
    assert fixture["duplicate_pcode_exports_rejected"] is True
    assert fixture["events_interlocked_and_virtual_memory_verified"] is True
    assert fixture["pcode_read_of_mapped_guest_image_verified"] is True
    assert fixture["duplicate_load_rejected"] is True
    assert smoke["frames_rendered"] == smoke["simulation_steps"] == 3
    assert smoke["pcode_step_invocations"] == 3
    assert smoke["pcode_functions_dispatched"] == 6
    assert smoke["status"] == "ok"
    assert smoke["validation_enabled"] is True
    assert smoke["validation_errors"] == 0
    assert ci_smoke["conclusion"] == "success"
    assert ci_smoke["frames_rendered"] == ci_smoke["simulation_steps"] == 3
    assert ci_smoke["entrypoint_invocations"] == 1
    assert ci_smoke["supplemental_module_count"] == 1
    assert ci_smoke["import_function_count"] == 74
    assert ci_smoke["pcode_step_invocations"] == 3
    assert ci_smoke["pcode_functions_dispatched"] == 7
    assert ci_smoke["validation_errors"] == 0
    assert ci_smoke["status"] == "ok"
    assert evidence["native_runtime_ctest"]["passed"] == 138
    assert evidence["native_runtime_ctest"]["failed"] == 0
    assert evidence["python_regressions"]["scope"] == (
        "tests/test_recompiled_pcode_pe32_vulkan_runtime.py"
    )
    assert evidence["python_regressions"]["passed"] == 3
    assert evidence["python_regressions"]["failed"] == 0
    full_suite = evidence["python_full_suite"]
    assert full_suite["passed"] == 7520
    assert full_suite["skipped"] == 4
    assert full_suite["failed"] == 0
    assert full_suite["revenginstr_revision"] == (
        "a58d8dcdc6cfa73af360c3f4cb253ad43fe507d7"
    )
    assert evidence["latest_local_vulkan_attempt"] == {
        "result": "exited_before_first_frame",
        "frames_rendered": 0,
        "simulation_steps": 1,
        "pcode_step_invocations": 1,
        "pcode_functions_dispatched": 3,
        "validation_enabled": True,
        "validation_errors": 0,
        "process_exit_code": 1,
        "note": "The runtime loop ended before the first frame; the cause was not established.",
    }
    assert evidence["retail_entrypoint_probe"]["pcode_functions_dispatched"] == 1699
    assert evidence["retail_entrypoint_probe"]["next_blocker"] == (
        "KERNEL32.dll!RaiseException"
    )
    assert evidence["python_regressions"]["skipped"] == 0
    assert evidence["python_regressions"]["passed"] == 3
    assert evidence["limitations"]["retail_pe_tested"] is True
    assert evidence["limitations"]["structured_exception_handling"] is False
    assert evidence["limitations"]["playable_game"] is False
    assert evidence["limitations"]["behavioral_parity"] is False


def test_startup_function_evidence_is_exact_and_fails_closed_at_seh_boundary() -> None:
    evidence = json.loads(
        (
            ROOT
            / "evidence/recompiled_pcode_startup_function_00918b33_20261018.json"
        ).read_text(encoding="utf-8")
    )
    function = evidence["function"]
    retail = evidence["retail_entrypoint_probe"]
    export_path = ROOT / "evidence" / function["instruction_export"]
    export = json.loads(export_path.read_text(encoding="utf-8"))

    assert evidence["format"] == "NFSShift.RecompiledPcodeRetailStartupFunction/1"
    assert hashlib.sha256(export_path.read_bytes()).hexdigest() == (
        function["instruction_export_sha256"]
    )
    assert export["format"] == "SHIFT.GhidraFunctionInstructions/2"
    assert export["function"]["address"] == function["entry"]
    assert export["function"]["size"] == function["body_bytes"]
    assert export["instruction_count"] == function["instructions"]
    assert sum(len(row["pcode"]) for row in export["instructions"]) == (
        function["pcode_operations"]
    )
    assert function["entry"] == "0x00918b33"
    assert function["body_bytes"] == 2447
    assert function["instructions"] == 778
    assert function["pcode_operations"] == 3919
    assert function["lowering"] == "passed using revenginstr.pcode.c_lowering"
    assert function["switch_table_targets"] == [
        "0x00918e84",
        "0x00918ce9",
        "0x00918d06",
        "0x00918d53",
        "0x00918d8d",
        "0x00918d96",
        "0x00918dcd",
        "0x00918ec7",
    ]
    assert retail["dispatches_before_function"] == 1272
    assert retail["dispatches_after_function"] == 1699
    assert retail["next_blocker"] == "KERNEL32.dll!RaiseException"
    assert retail["playable_game"] is False


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
    assert evidence["runtime_changes"]["kernel32_static_imports"] == 71
    assert evidence["runtime_changes"]["imagehlp_static_imports"] == 3
    assert evidence["runtime_changes"]["x86_register_bank_bytes"] == 8192
    assert runtime["entrypoint_invocations"] == 1
    assert runtime["frames_rendered"] == runtime["simulation_steps"] == 3
    assert runtime["pcode_step_invocations"] == 3
    assert runtime["pcode_functions_dispatched"] == 7
    assert runtime["validation_enabled"] is True
    assert runtime["validation_errors"] == 0
    assert runtime["status"] == "ok"
    assert retail["pcode_functions_dispatched"] == 1699
    assert retail["next_blocker"] == "KERNEL32.dll!RaiseException"
    assert retail["supplemental_function"] == "0x00918b33"
    assert retail["exception_code"] == "0xC000008F"
    assert evidence["limitations"]["playable_game"] is False


def test_guest_thread_startup_evidence_tracks_retail_import_frontier() -> None:
    evidence = json.loads(
        (
            ROOT
            / "evidence/recompiled_pcode_pe32_guest_thread_state_20261018.json"
        ).read_text(encoding="utf-8")
    )
    thread = evidence["guest_thread_state"]
    timer = evidence["winmm_timer_profile"]
    validation = evidence["validation"]
    smoke = evidence["local_linux_vulkan_smoke"]
    retail = evidence["retail_entrypoint_probe"]

    assert evidence["format"] == "NFSShift.RecompiledPcodePe32GuestThreadState/1"
    assert evidence["base_main_revision"] == (
        "229e13861ba9aa035ca4c1ce04c9c47939bfc7d5"
    )
    assert thread["teb_address"] == "0x7ffde000"
    assert thread["teb_exception_list"] == "0xffffffff"
    assert thread["x87_control_word"] == "0x037f"
    assert thread["image_overlap"] == "fails closed"
    assert timer["supported_guest_period_ms"] == 1
    assert timer["request_lifetimes_are_matched"] is True
    assert timer["host_timer_resolution_is_changed"] is False
    assert validation["native_runtime_ctest"]["passed"] == 138
    assert validation["native_runtime_ctest"]["failed"] == 0
    assert smoke["fixture_import_modules"] == 3
    assert smoke["fixture_import_functions"] == 76
    assert smoke["frames_rendered"] == smoke["simulation_steps"] == 3
    assert smoke["validation_errors"] == 0
    assert smoke["status"] == "ok"
    assert retail["pcode_functions_dispatched"] == 1893
    assert retail["passed_startup_import"] == {
        "function": "WINMM.dll!timeBeginPeriod",
        "period_ms": 1,
    }
    assert retail["next_blocker"] == "KERNEL32.dll!ConvertThreadToFiber"
    assert retail["fiber_scheduling_implemented"] is False
    assert evidence["limitations"]["playable_game"] is False
