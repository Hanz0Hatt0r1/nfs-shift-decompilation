import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_base_indexed_writable_near_transfer.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_base_indexed_writable_near_transfer.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_base_indexed", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_inventory_is_pinned():
    s = data()["surface"]
    assert s["decoded_instruction_count"] == 2847850
    assert s["base_indexed_writable_data_load_count"] == 63
    assert s["unique_effective_address_count"] == 51
    assert s["forward_window_decoded_instructions"] == 16
    assert s["same_register_indirect_transfer_count"] == 0
    assert s["exact_carrier_target_hit_count"] == 0


def test_target_agnostic_negative_is_scoped():
    a = data()["adjudication"]
    assert a["base_indexed_writable_same_register_near_transfer_subset_complete"] is True
    assert a["base_indexed_writable_same_register_can_target_exact_p1b_carrier"] is False
    assert a["register_copy_or_transform_after_base_indexed_load_remains_open"] is True
    assert a["base_indexed_stack_spill_reload_remains_open"] is True
    assert a["base_indexed_inter_block_carry_remains_open"] is True
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_reproduces_committed_evidence():
    assert module().build() == data()
