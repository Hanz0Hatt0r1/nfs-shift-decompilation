import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_text_base_delta_table_seeds.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_text_base_delta_table_seed_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_text_delta", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_machine_result_closes_only_nonexecuted_table_seed_subset():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330TextBaseDeltaTableSeedSurface/1"
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["retail_file_size"] == 8_801_792
    assert data["authority"]["text_base_va"] == "0x00401000"
    assert data["carrier_set"]["count"] == 15

    scan = data["scan"]
    assert scan["raw_exact_text_base_delta_hit_count"] == 1
    assert scan["non_executable_section_exact_text_base_delta_hit_count"] == 0
    assert scan["rel32_control_transfer_diagnostic_count"] == 1
    assert scan["unclassified_executable_diagnostic_count"] == 0

    hit = scan["raw_hits"][0]
    assert hit["carrier"] == "FUN_00768a4d"
    assert hit["text_base_delta"] == "0x00367a4d"
    assert hit["file_offset"] == "0x0019ab6c"
    assert hit["sequence_va"] == "0x0059b76c"
    assert hit["instruction_va"] == "0x0059b76b"
    assert hit["classification"] == "rel32_control_transfer_displacement"
    assert hit["control_transfer"] == "call"
    assert hit["control_target_va"] == "0x009031bd"
    assert hit["control_target_is_exact_p1b_carrier"] is False

    adj = data["adjudication"]
    assert adj["image_backed_text_base_delta_table_seed_subset_complete"] is True
    assert adj["image_backed_text_base_delta_table_seed_found"] is False
    assert adj["all_raw_text_base_delta_diagnostics_classified"] is True
    assert adj["memory_table_derived_carrier_pointers_ruled_out"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_helper_classifies_rel32_diagnostic_and_keeps_data_hits_distinct():
    module = load_module()
    section = {
        "name": ".text",
        "rva": 0x1000,
        "virtual_size": 0x100,
        "raw_size": 0x100,
        "raw_offset": 0,
        "characteristics": module.IMAGE_SCN_MEM_EXECUTE,
        "executable": True,
    }
    target = 0x00402000
    opcode_va = 0x00401010
    disp = target - (opcode_va + 5)
    blob = bytearray(0x100)
    blob[0x10] = 0xE8
    blob[0x11:0x15] = int(disp).to_bytes(4, "little", signed=True)
    row = module.classify_hit(bytes(blob), [section], "synthetic", target, disp & 0xFFFFFFFF, 0x11)
    assert row["classification"] == "rel32_control_transfer_displacement"
    assert row["control_transfer"] == "call"
    assert row["control_target_va"] == "0x00402000"

    data_section = dict(section)
    data_section.update({"name": ".rdata", "executable": False, "characteristics": 0})
    raw = module.classify_hit(bytes(blob), [data_section], "synthetic", target, disp & 0xFFFFFFFF, 0x11)
    assert raw["classification"] == "raw_dword_sequence"
    assert raw["section_executable"] is False
