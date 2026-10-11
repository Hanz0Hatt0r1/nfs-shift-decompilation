import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_manager374_literal_writer_closure.json"
VPTR = ROOT / "evidence" / "hdvehicle_64e8_manager_374_vptr_receiver_rejections.json"
BUILDER = ROOT / "tools" / "ghidra" / "build_p1b_manager374_literal_writer_closure.py"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location("p1b_literal_closure", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_committed_evidence():
    assert load_builder().build() == load_evidence()


def test_structured_vptr_contract_flattens_to_exact_15_sites():
    vptr = json.loads(VPTR.read_text(encoding="utf-8"))
    assert vptr["format"] == "SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1"
    sites = load_builder().vptr_rejection_sites(vptr)
    assert len(sites) == 15
    assert "0x008446cb" in sites
    assert "0x00a38974" in sites
    assert vptr["adjudication"]["numeric_plus_0x374_equality_used_as_identity"] is False


def test_exact_25_site_partition_closes_without_overlap():
    data = load_evidence()
    surface = data["surface"]
    assert surface["literal_write_site_count"] == 25
    assert surface["unique_literal_write_site_count"] == 25
    assert surface["partition_counts"] == {
        "proven_manager_domain": 2,
        "inherited_closed_negative": 3,
        "vptr_receiver_rejections": 15,
        "corrected_precluster_rejections": 2,
        "fmod_codec_rejections": 3,
    }
    assert sum(surface["partition_counts"].values()) == 25
    assert surface["closed_site_count"] == 25
    assert surface["remaining_literal_site_count"] == 0
    assert surface["remaining_literal_sites"] == []


def test_only_literal_surface_promotes():
    adj = load_evidence()["adjudication"]
    assert adj["literal_plus_0x374_writer_surface_complete"] is True
    assert adj["literal_manager_374_receiver_provenance_complete"] is True
    assert adj["literal_plus_0x374_site_can_place_fixed_hdvehicle_4330"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
