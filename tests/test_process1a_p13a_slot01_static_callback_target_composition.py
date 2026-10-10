import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_slot01_static_callback_target_composition.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_slot01_static_callback_target_composition.json"
CARRIER = ROOT / "evidence/p1a_p13a_slot01_carrier_surface_composition.json"
INDIRECT = ROOT / "evidence/p1d_slot3_exact_carrier_indirect_call_surface.json"
STATIC = ROOT / "evidence/p1d_slot3_exact_carrier_static_pointer_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_static_callback", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_evidence():
    module = load_module()
    assert module.build(load(CARRIER), load(INDIRECT), load(STATIC)) == load(EVIDENCE)


def test_exact_carrier_callind_caller_surface_is_empty():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01StaticCallbackTargetComposition/1"
    assert data["carrier_set"]["count"] == 16
    surface = data["callind_caller_surface"]
    assert surface["whole_index_indirect_call_edge_count"] == 19500
    assert surface["exact_carrier_caller_edge_count"] == 0
    assert surface["exact_carrier_caller_edges"] == []


def test_exported_static_target_surfaces_are_zero_hit():
    surface = load(EVIDENCE)["static_target_surface"]
    assert surface["vtable_candidate_count"] == 2533
    assert surface["vtable_slot_count"] == 22416
    assert surface["vtable_exact_carrier_target_hit_count"] == 0
    assert surface["static_table_record_count"] == 55066
    assert surface["static_table_declared_length_total"] == 956464
    assert surface["static_table_raw_hex_bytes_total"] == 684472
    assert surface["static_pointer_encoding"] == "little-endian 32-bit absolute VA"
    assert surface["static_table_exact_carrier_pointer_hit_count"] == 0


def test_only_static_callback_target_subsets_close():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_exact_carrier_callind_caller_subset_complete"] is True
    assert adj["p13a_exact_carrier_callind_caller_edge_found"] is False
    assert adj["p13a_exact_carrier_vtable_target_subset_complete"] is True
    assert adj["p13a_exact_carrier_static_table_literal_pointer_subset_complete"] is True
    assert adj["p13a_exact_carrier_static_target_hit_found"] is False
    assert adj["callbacks_registered_outside_carriers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["global_indirect_dispatch_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
