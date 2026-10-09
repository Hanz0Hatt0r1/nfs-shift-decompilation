import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_stack_root_alias_source.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_stack_root_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_stack_root_alias", TOOL)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_pinned_stack_aliases_do_not_escape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    a = data["aliases"]
    assert a["FUN_00758b50"]["alias"] == "local_2c"
    assert a["FUN_00758b50"]["passes_exact_root_to_callee"] is False
    assert a["FUN_00758b50"]["stores_exact_root_nonlocally"] is False
    assert a["FUN_00758b50"]["escapes_exact_root"] is False
    assert a["FUN_00763570"]["alias"] == "local_4c"
    assert a["FUN_00763570"]["uses_after_assignment"] == 0
    assert a["FUN_00763570"]["escapes_exact_root"] is False


def test_global_escape_gate_stays_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["source_stack_local_exact_entry_root_alias_subset_complete"] is True
    assert a["source_stack_local_exact_entry_root_escape_found"] is False
    assert a["derived_wheel_alias_storage_ruled_out"] is False
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_source_hash_drift_fails_closed(monkeypatch, tmp_path):
    m = load_module()
    p = tmp_path / "SHIFT.exe.c"
    p.write_text("drift", encoding="utf-8")
    monkeypatch.setattr(m, "sha256", lambda path: "0" * 64)
    try:
        m.analyze(p)
    except ValueError as exc:
        assert "unexpected SHIFT.exe.c SHA-256" in str(exc)
    else:
        raise AssertionError("source drift must fail closed")
