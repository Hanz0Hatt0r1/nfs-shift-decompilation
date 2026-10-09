import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "inventory_p1a_slot01_overlap_stores.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_overlap_store_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_overlap_stores", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scanner_includes_true_overlap_and_excludes_reads(monkeypatch, tmp_path):
    module = load_module()
    exe = tmp_path / "SHIFT.exe"
    db = tmp_path / "shift_ghidra.sqlite"

    monkeypatch.setattr(
        module,
        "sha256",
        lambda path: module.EXE_SHA256 if path.name == "SHIFT.exe" else module.SQLITE_SHA256,
    )
    monkeypatch.setattr(module, "load_functions", lambda _path: [(0x1000, 0x1100, "FUN_TEST")])
    synthetic = "\n".join(
        [
            "  1000: 89 81 34 05 00 00     mov    DWORD PTR [ecx+0x534],eax",
            "  1006: 0f 11 81 30 05 00 00  movups XMMWORD PTR [ecx+0x530],xmm0",
            "  100d: 8b 81 38 05 00 00     mov    eax,DWORD PTR [ecx+0x538]",
            "  1013: d9 81 38 05 00 00     fld    DWORD PTR [ecx+0x538]",
            "  1019: 89 81 3c 05 00 00     mov    DWORD PTR [ecx+0x53c],eax",
            "  101f: dd 99 38 05 00 00     fstp   QWORD PTR [ecx+0x538]",
        ]
    )
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: synthetic)

    payload = module.inventory(exe, db)
    assert payload["overlapping_store_count"] == 3
    assert payload["partial_store_count"] == 1
    assert payload["qword_or_wider_store_count"] == 2
    assert payload["unowned_instruction_count"] == 0
    assert [row["site"] for row in payload["stores"]] == [
        "0x00001006",
        "0x00001019",
        "0x0000101f",
    ]
    assert payload["stores"][0]["literal_displacement"] == "0x530"
    assert payload["stores"][0]["write_range"] == ["0x530", "0x540"]


def test_pinned_inventory_is_exact_and_owned():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    inv = payload["inventory"]
    assert inv["scanned_sized_function_count"] == 41538
    assert inv["overlapping_store_count"] == 25
    assert inv["partial_store_count"] == 24
    assert inv["qword_or_wider_store_count"] == 1
    assert inv["function_count"] == 13
    assert inv["unowned_instruction_count"] == 0
    assert inv["partial_writer_function_count"] == 12
    assert inv["known_qword_writer"]["site"] == "0x00761b67"
    assert inv["known_qword_writer"]["matches_slot0_or_slot1"] is False


def test_all_partial_receivers_reject_but_global_slots_stay_open():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = payload["candidate_adjudication"]
    assert len(rows) == 12
    assert {row["function"] for row in rows} == set(payload["inventory"]["partial_writer_functions"])
    assert all(row["selected_slot_writer"] is False for row in rows)

    adj = payload["adjudication"]
    assert adj["exact_literal_overlap_store_surface_complete"] is True
    assert adj["all_partial_store_receivers_rejected"] is True
    assert adj["known_qword_store_receiver_rejected"] is True
    assert adj["selected_slot0_or_slot1_exact_literal_overlap_writer_found"] is False
    assert adj["computed_address_store_surface_complete"] is False
    assert adj["escaped_alias_store_surface_complete"] is False
    assert adj["bulk_copy_or_memory_init_surface_complete"] is False
    assert adj["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_new_receiver_bridges_are_machine_pinned():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    by_name = {row["function"]: row for row in payload["candidate_adjudication"]}

    copied = by_name["FUN_005cb010"]["new_machine_proof"]
    assert copied["allocator_stride"] == "0x005c11aa imul esi,esi,0x560"
    assert copied["node_vptr"] == "0x00adc8c0"
    assert copied["vtable_slot2"] == "0x00adc8c8 -> 0x005d1ba0"
    assert copied["only_direct_call_to_FUN_005cb010"] == "0x005d1bba"
    assert copied["literal_pointer_occurrences_of_FUN_005cb010"] == 0

    ctor = by_name["FUN_00860bf0"]["new_machine_proof"]
    assert "0x8c0" in ctor["allocation"]
    assert ctor["vptr_store"] == "0x00860c15 mov [esi],0x00b1dae0"
    assert by_name["FUN_008614c0"]["new_machine_proof"]["vtable_slot0"] == "0x00b1dae0 -> 0x00862b40"
    assert by_name["FUN_008620b0"]["new_machine_proof"]["update_call"] == "0x00862b51 call FUN_008620b0"
