import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_constant_encoded_synthesis.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_constant_encoded_synthesis.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_encoded", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_committed_retail_counts_and_fail_closed_global_gates():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ConstantEncodedSynthesis/1"
    assert data["ready"] is True
    assert data["scope"]["exact_carrier_count"] == 15
    assert data["scan"]["instruction_count"] == 2_847_850
    assert data["scan"]["constant_seed_count"] == 67_970
    assert data["scan"]["recognized_transition_count"] == 2_168
    assert data["scan"]["exact_carrier_synthesis_hit_count"] == 0

    adj = data["adjudication"]
    assert adj["constant_only_encoded_carrier_synthesis_subset_complete"] is True
    assert adj["constant_only_encoded_exact_carrier_synthesis_found"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_synthetic_xor_decode_is_detected():
    module = load_module()
    text = """
00401000: b8 11 11 00 00        mov    eax,0x1111
00401005: 35 11 01 00 00        xor    eax,0x111
0040100a: 90                    nop
"""
    scan = module.scan_disassembly(text, {0x1000})
    assert scan["constant_seed_count"] == 1
    assert scan["recognized_transition_counts"]["xor"] == 1
    assert scan["exact_carrier_synthesis_hit_count"] >= 1
    assert scan["exact_carrier_synthesis_hits"][0]["value"] == "0x00001000"


def test_control_transfer_breaks_constant_lineage():
    module = load_module()
    text = """
00401000: b8 11 11 00 00        mov    eax,0x1111
00401005: 75 02                 jne    0x401009
00401007: 35 11 01 00 00        xor    eax,0x111
"""
    scan = module.scan_disassembly(text, {0x1000})
    assert scan["control_flow_reset_count"] == 1
    assert scan["exact_carrier_synthesis_hit_count"] == 0
