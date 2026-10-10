import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_static_carrier_seed_handoff.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_static_carrier_seed_handoff.json"
STATIC = ROOT / "evidence/p1a_p13a_slot01_static_callback_target_composition.json"
ABSOLUTE = ROOT / "evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json"
TEXT_RVA = ROOT / "evidence/p1a_p13a_exact_carrier_text_rva_literal_closure.json"
RDATA_RVA = ROOT / "evidence/p1a_p13a_exact_carrier_rdata_rva_diagnostic_closure.json"
RELOC = ROOT / "evidence/p1a_p13a_pe_base_relocation_carrier_closure.json"
INDIRECT = ROOT / "evidence/p1a_p13a_exact_carrier_incoming_indirect_index_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_static_seed", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_handoff():
    module = load_module()
    assert module.build(
        load(STATIC), load(ABSOLUTE), load(TEXT_RVA), load(RDATA_RVA), load(RELOC), load(INDIRECT)
    ) == load(EVIDENCE)


def test_bounded_static_seed_surface_is_exact():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13AStaticCarrierSeedHandoff/1"
    assert data["carrier_set"]["count"] == 16
    surface = data["bounded_static_seed_surface"]
    assert surface == {
        "exported_vtable_exact_carrier_hits": 0,
        "exported_static_table_exact_carrier_hits": 0,
        "whole_image_absolute_va_literal_hits": 0,
        "whole_image_raw_rva_matches": 2,
        "whole_image_raw_rva_semantic_pointer_hits": 0,
        "pe_base_relocation_records_present": False,
        "exact_carrier_callind_caller_edges": 0,
        "incoming_indirect_index_edges": 19500,
        "incoming_indirect_index_resolved_targets": 0,
    }


def test_static_handoff_narrows_without_promoting_runtime_gates():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_bounded_on_disk_static_exact_carrier_seed_surface_complete"] is True
    assert adj["p13a_bounded_on_disk_static_exact_carrier_seed_hit_found"] is False
    assert adj["p13a_standard_pe_loader_relocation_seed_path_ruled_out"] is True
    assert adj["p13a_incoming_indirect_index_capability_gap_explicit"] is True
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["manual_imagebase_plus_rva_pointer_construction_ruled_out"] is False
    assert adj["encoded_or_reconstructed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
