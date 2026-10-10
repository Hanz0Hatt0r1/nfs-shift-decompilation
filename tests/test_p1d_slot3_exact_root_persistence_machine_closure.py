import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_exact_root_persistence_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_exact_root_persistence_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_root_persistence_pe", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_machine_windows_and_counts_are_pinned():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3ExactRootPersistenceMachineClosure/1"
    scope = data["scope"]
    assert scope["carrier_window_count"] == 6
    assert scope["memory_store_root_count"] == 0
    assert scope["push_root_count"] == 0
    assert scope["ranked_persistence_candidate_count"] == 8
    expected = {
        "FUN_00758b50": (52, 161, "82218e6367840c8d9c7e3723fcad5c70e25c8d198fd1772c65dbc83900ac9377"),
        "FUN_00755950": (16, 60, "79b509c1706c0aa91c335548404f53e9dac1c10b89cf71e7894edda47d2567ba"),
        "FUN_00755a60": (387, 1278, "3c7f7ecc4348f555cf643c02ab652440568351bade905e9ffbf8056f71ec1f8a"),
        "FUN_00752fc0": (7, 37, "830ecb8fa09bf20a07a8e269f4d44351dc167232bba00f5d9a7d931675d111cc"),
        "FUN_00760b50": (135, 505, "f648d08e067bd2a9e4a22187829d08e40b58d6cbce8e9c967d00e403090d2ec8"),
        "FUN_00755f80": (35, 106, "c2843b9d46ffebf900114d96fcc96e1b21d7c11355dc3aad8209bbde5ca80179"),
    }
    got = {row["function"]: (row["instruction_count"], row["machine_byte_count"], row["machine_bytes_sha256"]) for row in scope["windows"]}
    assert got == expected


def test_exact_ranked_candidate_set_and_semantic_adjudication():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = {row["instruction_address"]: row for row in data["ranked_candidates"]}
    assert set(rows) == {
        "0x00755964", "0x00755b8f", "0x00755c04", "0x00755db3",
        "0x00760d02", "0x00755f9c", "0x00755fb8", "0x00755fd6",
    }
    assert rows["0x00755964"]["machine_adjudication"] == "derived-interior-alias"
    assert rows["0x00755c04"]["machine_adjudication"] == "derived-interior-alias"
    assert rows["0x00755db3"]["machine_adjudication"] == "known-exact-root-forward"
    for site in ("0x00755b8f", "0x00760d02", "0x00755f9c", "0x00755fb8", "0x00755fd6"):
        assert rows[site]["machine_adjudication"] == "child-pointer-load"


def test_classifier_surfaces_store_and_push_root_candidates():
    module = load_module()
    store = {"mnemonic": "mov", "operands": "dword ptr [eax+0x10],esi"}
    push = {"mnemonic": "push", "operands": "esi"}
    assert "memory-store-root" in module.classify(store, "esi")
    assert "push-root" in module.classify(push, "esi")


def test_global_alias_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["bounded_six_window_machine_persistence_inventory_complete"] is True
    assert gates["bounded_six_window_persistence_candidates_adjudicated"] is True
    assert gates["bounded_six_window_selected_slot3_writer_found"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
