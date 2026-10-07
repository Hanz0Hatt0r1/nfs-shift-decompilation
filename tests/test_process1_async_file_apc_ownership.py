from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_async_file_apc_ownership.json"
PREVIOUS = ROOT / "evidence/process1_controller1_message_queue_wake.json"
DOC = ROOT / "docs/PROCESS_1_ASYNC_FILE_APC_OWNERSHIP.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_async_file_apc_contract_joins_process1_controller_frontier() -> None:
    payload = _load(EVIDENCE)
    previous = _load(PREVIOUS)

    assert payload["format"] == "SHIFT.Process1AsyncFileApcOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == (
        "705af8b420e5eb1e3834ac43d5533c6b"
    )
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_executable_size"] == 8801792
    assert payload["source"]["xbox_recomp_required"] is False
    assert payload["joins"]["previous_contract"] == previous["format"]
    assert payload["joins"]["controller1_worker"] == previous["joins"]["worker"]
    assert payload["joins"]["controller1_worker"] == "FUN_00662880"
    assert payload["joins"]["async_file_worker"] == "0x00667240"
    assert payload["joins"]["workers_are_distinct"] is True


def test_async_file_thread_identity_and_virtual_worker_are_machine_locked() -> None:
    payload = _load(EVIDENCE)
    thread = payload["async_file_thread"]

    assert thread["thread_start_wrapper"] == "0x0065f0a0"
    assert thread["generic_thread_create"] == "0x00649cb0"
    assert thread["generic_thread_entry"] == "0x00649b10"
    assert thread["thread_name_va"] == "0x00aeff74"
    assert thread["worker_vtable"] == "0x00af386c"
    assert thread["worker_vtable_slot_4"] == "0x00667240"
    assert thread["vtable_worker_pointer_occurrences"] == ["0x00af3870"]
    assert thread["worker_direct_call_occurrences"] == 0
    assert thread["worker_dispatch_is_virtual"] is True

    spans = thread["machine_spans"]
    assert spans["thread_start"]["sha256"] == (
        "8ef3c1de07f96e6be0a611003fc9e973f71a528678515f0f956cdbe79a51fa62"
    )
    assert spans["thread_virtual_worker_dispatch"]["sha256"] == (
        "66ea451ea643112cd2691e8764c2ce1907e636431cd49c8cf7f2c9202962d9b4"
    )
    assert spans["thread_name_data"]["sha256"] == (
        "86b11ae477059d159bee6726b9fb1eaf4815d0c8b34d36df729c4f0cac050f2d"
    )
    assert spans["vtable_head"]["sha256"] == (
        "2e85e38911cabd1248674c7848bb03fe4b612d0fb06570b80b592b4a75e5054d"
    )


def test_async_operation_table_is_the_only_recovered_handler_pointer_surface() -> None:
    payload = _load(EVIDENCE)
    dispatch = payload["operation_dispatch"]

    assert dispatch["worker"] == "0x00667240"
    assert dispatch["dispatch_table"] == "0x00b890f0"
    assert dispatch["dispatch_entries"] == [
        {"operation": 2, "handler": "0x00655ab0"},
        {"operation": 3, "handler": "0x00655ab0"},
        {"operation": 4, "handler": "0x00655c80"},
        {"operation": 6, "handler": "0x00655c80"},
        {"operation": 5, "handler": "0x00655c80"},
    ]
    assert dispatch["handler_00655ab0_absolute_pointer_occurrences"] == [
        "0x00b890f4",
        "0x00b890fc",
    ]
    assert dispatch["handler_00655c80_absolute_pointer_occurrences"] == [
        "0x00b89104",
        "0x00b8910c",
        "0x00b89114",
    ]
    assert dispatch["handler_direct_call_or_jump_occurrences"] == 0
    assert dispatch["dispatch_helper"] == "0x006671b0"
    assert dispatch["worker_dispatch_callsite"] == "0x006674ec"

    spans = dispatch["machine_spans"]
    assert spans["dispatch_table_data"]["sha256"] == (
        "8b8b880209e902240062ce3e6b5f663cb80d2601a1cd437c7f7bd1e83d0ec2a4"
    )
    assert spans["dispatch_helper"]["sha256"] == (
        "17f6ecbad73436f12c39ebfd29a7f3e9dadab1427fed422fcc47e70294d09c5f"
    )
    assert spans["worker_dispatch_and_alertable_sleep"]["sha256"] == (
        "541de1fe69988de6e7c41dacac838593138b3627fe7fe7cdb9f7b393c4e7b5c4"
    )


def test_all_direct_pc_async_file_callsites_are_accounted_for() -> None:
    payload = _load(EVIDENCE)
    calls = payload["async_file_calls"]

    assert calls["read_file_ex_iat"] == "0x00aa6240"
    assert calls["write_file_ex_iat"] == "0x00aa6234"
    assert calls["read_file_ex_call_sites"] == ["0x006558d5", "0x00655c15"]
    assert calls["write_file_ex_call_sites"] == ["0x006559df", "0x00655dca"]
    assert calls["read_completion_routine"] == "0x006553e0"
    assert calls["write_completion_routine"] == "0x00655410"
    assert calls["all_direct_read_file_ex_callsites_accounted_for"] is True
    assert calls["all_direct_write_file_ex_callsites_accounted_for"] is True

    expected = {
        "read_call_1": "c8fae4949a3d9d6a5fec70c4cc939fa6cfa48709c73c12c52bc723d1b1544c72",
        "write_call_1": "3a9ad12af11448a597ba4011ad20b74107a3bebf0a6705f693ac295993535ef3",
        "read_call_2": "ee754aa6f2deaf1318829694de1124968e6cebcde5618cd04656932d78092d77",
        "write_call_2": "c4223dae28af7ef9af3136c7f6873a229263d519a8087064136a4f76909f36e2",
        "read_completion": "1c45703b9acea9563b4ac7515762b01ed1778bffec545607cf5577ecf891d97b",
        "write_completion": "55a55c175c1191be6ba25f8b71a855220ebcb4f4c59726e77d4de305a75dc272",
    }
    for key, digest in expected.items():
        assert calls["machine_spans"][key]["sha256"] == digest


def test_known_file_completion_surface_is_not_promoted_to_controller1_apc_wake() -> None:
    payload = _load(EVIDENCE)
    wait = payload["alertable_wait"]
    adjudication = payload["adjudication"]

    assert wait["sleep_ex_iat"] == "0x00aa6274"
    assert wait["sleep_ex_wrapper"] == "0x00649780"
    assert wait["async_worker_passes_alertable_true"] is True
    assert wait["async_worker_sleep_wrapper_callsite"] == "0x006674f8"
    assert wait["controller1_sleep_call_is_a_separate_worker_path"] is True
    assert wait["machine_span"]["sha256"] == (
        "260451a7ed8644869aebf1085cde645cf66e9be0397021c69457405e77d760a5"
    )

    assert (
        adjudication[
            "identified_read_write_file_ex_surface_owned_by_base_file_async_thread_proven"
        ]
        is True
    )
    assert (
        adjudication["identified_read_write_file_ex_surface_owned_by_controller1_proven"]
        is False
    )
    assert (
        adjudication[
            "identified_file_completion_apc_path_is_controller1_wake_source_proven"
        ]
        is False
    )
    assert adjudication["all_possible_apc_paths_into_controller1_excluded"] is False
    assert adjudication["render_or_present_phase_lock_proven"] is False


def test_documentation_preserves_remaining_apc_and_render_uncertainty() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "Base File: Async Thread" in text
    assert "FUN_00662880" in text
    assert "all direct PC-retail `ReadFileEx` callsites are accounted for" in text
    assert "all direct PC-retail `WriteFileEx` callsites are accounted for" in text
    assert "does **not** prove" in text
    assert "rendering or presentation is phase-locked" in text
    assert "Xbox recomp was available for navigation" in text
