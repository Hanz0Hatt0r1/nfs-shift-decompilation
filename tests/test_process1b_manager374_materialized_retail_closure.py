import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/p1b_manager374_materialized_retail_frontier.json"
CLOSURE = ROOT / "evidence/p1b_manager374_materialized_retail_closure.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_materialized_retail_closure.py"
SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def module():
    spec = importlib.util.spec_from_file_location("p1b_materialized_retail_closure", BUILDER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_frontier_is_authoritative_zero_union():
    data = load(FRONTIER)
    assert data["format"] == "SHIFT.P1B.Manager374MaterializedRetailFrontier/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == SHA
    assert data["authority"]["all_probe_outputs_same_authoritative_executable"] is True
    assert data["inputs"] == {
        "same_region": "SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1",
        "ebp_spill_reload": "SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1",
        "esp_spill_reload": "SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1",
    }
    s = data["surface"]
    assert s["probe_count"] == 3
    assert s["candidate_record_count_by_probe"] == {
        "same_region": 0,
        "ebp_spill_reload": 0,
        "esp_spill_reload": 0,
    }
    assert s["candidate_record_count"] == 0
    assert s["candidate_records"] == []
    assert s["unique_candidate_site_count"] == 0
    assert s["unique_candidate_sites"] == []
    assert s["candidate_site_sources"] == []
    assert s["unadjudicated_candidate_site_count"] == 0
    assert s["unadjudicated_candidate_sites"] == []


def test_builder_reproduces_committed_closure():
    assert module().build() == load(CLOSURE)


def test_scoped_materialized_transport_closes_negative():
    data = load(CLOSURE)
    assert data["format"] == "SHIFT.P1B.Manager374MaterializedRetailClosure/1"
    assert data["surface"] == {
        "probe_count": 3,
        "same_region_write_candidate_count": 0,
        "ebp_spill_reload_write_candidate_count": 0,
        "esp_spill_reload_write_candidate_count": 0,
        "candidate_record_count": 0,
        "unique_candidate_site_count": 0,
        "remaining_materialized_candidate_site_count": 0,
    }
    a = data["adjudication"]
    assert a["materialized_plus_374_same_region_retail_frontier_empty"] is True
    assert a["materialized_plus_374_ebp_spill_reload_retail_frontier_empty"] is True
    assert a["materialized_plus_374_esp_spill_reload_retail_frontier_empty"] is True
    assert a["materialized_plus_374_bounded_transport_surface_complete"] is True
    assert a["all_materialized_candidate_receivers_classified"] is True
    assert a["materialized_plus_374_bounded_transport_can_write_manager_374"] is False


def test_global_identity_and_external_origin_gates_stay_fail_closed():
    a = load(CLOSURE)["adjudication"]
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert a["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert a["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert a["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert a["global_manager_root_origin_surface_complete"] is False
    assert a["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
