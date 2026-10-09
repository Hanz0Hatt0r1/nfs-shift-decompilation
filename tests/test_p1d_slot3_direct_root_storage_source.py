import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_direct_root_storage_source.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_direct_root_storage_source.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_direct_root_storage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_direct_root_assignments_are_stack_only():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    surface = data["direct_exact_root_assignments"]
    assert surface["count"] == 2
    assert surface["persistent_or_unknown_count"] == 0
    assert surface["rows"] == [
        {"function":"FUN_00758b50","root":"param_1","lhs":"local_2c","text":"local_2c = param_1;","storage":"stack-local"},
        {"function":"FUN_00763570","root":"this","lhs":"local_4c","text":"local_4c = this;","storage":"stack-local"},
    ]


def test_bounded_gate_does_not_overclaim_escape_closure():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["source_direct_exact_entry_root_assignment_subset_complete"] is True
    assert a["source_direct_exact_entry_root_persistent_store_found"] is False
    assert a["derived_alias_storage_ruled_out"] is False
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_synthetic_persistent_root_assignment_fails_expected_surface(monkeypatch, tmp_path):
    m = load_module()
    chunks=[]
    for index,(name,(sig,root)) in enumerate(m.CARRIERS.items()):
        body = f"\n{{\n  local_ok = {root};\n}}\n" if index == 0 else "\n{\n}\n"
        chunks.append(sig + body)
    source=tmp_path / "SHIFT.exe.c"
    source.write_text("\n\n".join(chunks),encoding="utf-8")
    monkeypatch.setattr(m,"sha256",lambda path:m.SOURCE_SHA256)
    try:
        m.analyze(source)
    except ValueError as exc:
        assert "assignment surface drift" in str(exc)
    else:
        raise AssertionError("unexpected direct-root surface must fail closed")
