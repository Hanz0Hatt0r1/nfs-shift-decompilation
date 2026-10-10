import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_16carrier_bulk_opcode_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_16carrier_bulk_opcode_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_bulk_opcode", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_surface_is_all_16_carriers():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3SixteenCarrierBulkOpcodeClosure/1"
    assert data["scope"]["carrier_count"] == 16
    assert len(data["scope"]["functions"]) == 16
    assert data["scope"]["instruction_count"] == 5178


def test_no_direct_x86_bulk_string_opcodes_found():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    surface = data["direct_bulk_opcode_surface"]
    assert surface["hit_count"] == 0
    assert surface["hits"] == []
    assert surface["rep_prefixed_or_x86_string_opcode_found"] is False
    assert all(row["bulk_opcode_hits"] == [] for row in data["scope"]["functions"].values())


def test_global_aggregate_and_runtime_gates_stay_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["machine_direct_bulk_opcode_16_carrier_subset_complete"] is True
    assert gates["machine_direct_bulk_opcode_found"] is False
    assert gates["aggregate_or_bulk_alias_stores_ruled_out"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_tool_contract_matches_evidence():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.FORMAT == data["format"]
    assert len(module.SPECS) == 16
    assert sum(module.EXPECTED_INSTRUCTIONS.values()) == 5178
    assert set(module.SPECS) == set(data["scope"]["functions"])
