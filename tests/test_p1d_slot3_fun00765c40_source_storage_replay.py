import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_fun00765c40_source_storage_replay.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00765c40_source_storage_replay.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_765c40_source_storage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_inputs(tmp_path, module):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({
        "format": module.BASE_FORMAT,
        "ready": True,
        "carrier_set": {"count": 15},
        "direct_exact_root_assignments": {
            "rows": module.EXPECTED_EXISTING_ASSIGNMENTS,
            "persistent_or_unknown_count": 0,
        },
        "adjudication": {"source_direct_exact_entry_root_assignment_subset_complete": True},
    }), encoding="utf-8")
    handoff = tmp_path / "handoff.json"
    handoff.write_text(json.dumps({
        "format": module.HANDOFF_FORMAT,
        "ready": True,
        "carrier": {
            "function": "FUN_00765c40",
            "entry": "0x00765c40",
            "previous_p1d_exact_carrier_count": 15,
            "expanded_p1d_exact_carrier_count": 16,
        },
        "adjudication": {"p1d_exact_carrier_set_expanded_to_16": True},
    }), encoding="utf-8")
    return base, handoff


def test_pinned_16_carrier_replay_closes_only_direct_exact_root_source_subset():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00765c40SourceStorageReplay/1"
    assert data["carrier_expansion"] == {
        "added_entry": "0x00765c40",
        "added_function": "FUN_00765c40",
        "new_count": 16,
        "previous_count": 15,
    }
    replay = data["fun00765c40_source_replay"]
    assert replay["direct_exact_root_assignment_count"] == 0
    assert replay["persistent_or_unknown_direct_root_assignment_count"] == 0
    combined = data["combined_direct_exact_root_assignments"]
    assert combined["count"] == 2
    assert combined["persistent_or_unknown_count"] == 0


def test_global_escape_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["source_direct_exact_entry_root_assignment_16_carrier_subset_complete"] is True
    assert gates["source_storage_replay_for_16_carriers_complete"] is True
    assert gates["fun00765c40_direct_exact_entry_root_assignment_found"] is False
    assert gates["derived_alias_storage_ruled_out"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_synthetic_new_direct_root_assignment_fails_closed(monkeypatch, tmp_path):
    module = load_module()
    base, handoff = write_inputs(tmp_path, module)
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        module.SIGNATURE
        + "\n\n{\n  void *local_44;\n  local_44 = this;\n}\n\n"
        + "void FUN_00765d00(void)\n\n{\n}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "sha256", lambda path: module.SOURCE_SHA256)
    try:
        module.analyze(source, base, handoff)
    except ValueError as exc:
        assert "direct exact-root assignment surface is not empty" in str(exc)
    else:
        raise AssertionError("new exact-root assignment must fail closed")


def test_unproven_16_carrier_handoff_fails_closed(monkeypatch, tmp_path):
    module = load_module()
    base, handoff = write_inputs(tmp_path, module)
    payload = json.loads(handoff.read_text(encoding="utf-8"))
    payload["adjudication"]["p1d_exact_carrier_set_expanded_to_16"] = False
    handoff.write_text(json.dumps(payload), encoding="utf-8")
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(module.SIGNATURE + "\n\n{\n}\n", encoding="utf-8")
    monkeypatch.setattr(module, "sha256", lambda path: module.SOURCE_SHA256)
    try:
        module.analyze(source, base, handoff)
    except ValueError as exc:
        assert "16-carrier expansion is not proven upstream" in str(exc)
    else:
        raise AssertionError("unproven carrier expansion must fail closed")
