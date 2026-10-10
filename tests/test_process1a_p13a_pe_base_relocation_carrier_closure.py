import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1a_pe_base_relocation_carrier_frontier.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_pe_base_relocation_carrier_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_reloc", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_pe_authority_constants_are_pinned():
    module = load_module()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.RETAIL_SIZE == 8801792
    assert module.IMAGE_BASE == 0x00400000
    assert module.EXPECTED_CHARACTERISTICS == 0x0103
    assert module.IMAGE_FILE_RELOCS_STRIPPED == 0x0001
    assert module.BASE_RELOCATION_DIRECTORY_INDEX == 5
    assert module.EXPECTED_SECTIONS == [".text", ".rdata", ".data", ".tls", ".rsrc", ".secu"]


def test_committed_pe_relocation_surface_is_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13APeBaseRelocationCarrierClosure/1"
    pe = data["pe"]
    assert pe["format"] == "PE32"
    assert pe["image_base"] == "0x00400000"
    assert pe["file_characteristics"] == "0x0103"
    assert pe["image_file_relocs_stripped"] is True
    assert pe["number_of_rva_and_sizes"] == 16
    assert pe["base_relocation_directory"] == {"index": 5, "rva": "0x00000000", "size": 0}
    assert pe["section_names"] == [".text", ".rdata", ".data", ".tls", ".rsrc", ".secu"]
    assert pe["reloc_section_present"] is False


def test_only_standard_loader_relocation_path_closes():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_standard_pe_base_relocation_subset_complete"] is True
    assert adj["p13a_standard_pe_base_relocation_records_present"] is False
    assert adj["p13a_pe_loader_base_relocation_carrier_pointer_path_ruled_out"] is True
    assert adj["manual_imagebase_plus_rva_pointer_construction_ruled_out"] is False
    assert adj["encoded_or_reconstructed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
