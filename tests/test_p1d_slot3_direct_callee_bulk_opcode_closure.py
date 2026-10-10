import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_direct_callee_bulk_opcode_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_direct_callee_bulk", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_direct_callee_surface_shape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1"
    surface = data["surface"]
    assert surface["carrier_count"] == 16
    assert surface["direct_callsite_count"] == 214
    assert surface["unique_direct_callee_count"] == 82
    assert surface["direct_callee_instruction_count"] == 9159


def test_direct_callee_manifests_are_pinned():
    surface = json.loads(EVIDENCE.read_text(encoding="utf-8"))["surface"]
    assert surface["direct_callsite_manifest_sha256"] == "bdd48b9a2c49f2aaec1f0311a895c7b077f44b254ca05c7165d84629e0ddbed8"
    assert surface["direct_callee_manifest_sha256"] == "439a0227f1f7619763f579f4e7a6d0033fd7de341eb7180645b0537124633b27"
    assert surface["indirect_callsite_manifest_sha256"] == "f25f5ac79ea099196349cf39ebb69c9e586ad2c12523f1c19cd43bf837444c27"


def test_no_direct_callee_string_bulk_opcodes_found():
    surface = json.loads(EVIDENCE.read_text(encoding="utf-8"))["surface"]
    assert surface["bulk_opcode_hit_count"] == 0
    assert surface["bulk_opcode_hits"] == []


def test_two_indirect_callsites_remain_explicitly_open():
    surface = json.loads(EVIDENCE.read_text(encoding="utf-8"))["surface"]
    assert surface["indirect_callsite_count"] == 2
    assert [(x["caller"], x["site"]) for x in surface["indirect_callsites"]] == [
        ("FUN_00770e80", "0x00770ec4"),
        ("FUN_00770e80", "0x00770f41"),
    ]


def test_global_alias_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["first_direct_callee_bulk_opcode_surface_complete"] is True
    assert gates["first_direct_callee_bulk_opcode_found"] is False
    assert gates["aggregate_or_bulk_alias_stores_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.FORMAT == data["format"]
    assert len(module.CARRIERS) == 16
    assert module.EXPECTED_DIRECT_CALLSITE_COUNT == 214
    assert module.EXPECTED_DIRECT_CALLEE_COUNT == 82
    assert module.EXPECTED_DIRECT_CALLEE_INSTRUCTION_COUNT == 9159
