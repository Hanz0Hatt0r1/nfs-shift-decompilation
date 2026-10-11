import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_indirect_entry_coverage_v12.py"
SURFACE = ROOT / "evidence" / "p1b_hdvehicle_4330_base_indexed_implicit_stack_carriers.json"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v12.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_4330_indirect_v12", BUILDER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_machine_surface_is_exact_and_fail_closed():
    d = data(SURFACE)
    assert d["format"] == "SHIFT.P1B.HDVehicle4330BaseIndexedImplicitStackCarrierSurface/1"
    i = d["inventory"]
    assert i["base_indexed_data_load_count"] == 63
    assert i["unique_effective_address_count"] == 51
    assert i["implicit_push_event_count"] == 5
    assert i["implicit_pop_reload_event_count"] == 0
    assert i["normalized_esp_adjust_event_count"] == 0
    assert i["tainted_register_indirect_transfer_count"] == 0
    assert i["direct_call_argument_escape_count"] == 5
    assert len({x["direct_callee"] for x in i["direct_call_argument_escapes"]}) == 4
    assert d["adjudication"]["direct_call_argument_escape_callees_require_provenance"] is True
    assert d["adjudication"]["indirect_entry_into_carriers_ruled_out"] is False


def test_exact_escape_sites_and_callees_are_stable():
    i = data(SURFACE)["inventory"]
    got = [(x["load_site"], x["push_site"], x["call_site"], x["direct_callee"]) for x in i["direct_call_argument_escapes"]]
    assert got == [
        ("0x004b1c10", "0x004b1c17", "0x004b1c1b", "0x006329e0"),
        ("0x004cd45d", "0x004cd464", "0x004cd46b", "0x00632c70"),
        ("0x005f51e0", "0x005f51e2", "0x005f51ed", "0x00403c90"),
        ("0x008d1951", "0x008d1958", "0x008d1960", "0x008b4c70"),
        ("0x00d742fd", "0x00d74304", "0x00d74308", "0x006329e0"),
    ]


def test_v12_composes_surface_without_promoting_global_gates():
    d = data(EVIDENCE)
    assert d["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/12"
    s = d["surface"]
    assert s["previous_bounded_coverage_class_count"] == 15
    assert s["composed_coverage_class_count"] == 16
    assert s["base_indexed_direct_call_argument_escape_count"] == 5
    assert s["base_indexed_direct_call_argument_escape_unique_callee_count"] == 4
    assert s["bounded_exact_carrier_hit_count"] == 0
    a = d["adjudication"]
    assert a["base_indexed_direct_call_argument_escapes_require_callee_provenance"] is True
    assert a["base_indexed_inter_block_carry_remains_open"] is True
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_reproduces_committed_v12():
    assert module().build() == data(EVIDENCE)
