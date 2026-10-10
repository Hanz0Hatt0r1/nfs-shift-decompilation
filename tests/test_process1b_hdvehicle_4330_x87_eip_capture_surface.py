import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_x87_eip_capture.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_x87_eip_capture_surface.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_x87_eip", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_four_decoded_sites_and_zero_eip_extraction():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330X87EipCaptureSurface/1"
    assert data["decoded_x87_env_sites"]["count"] == 4
    assert data["decoded_x87_env_sites"]["addresses"] == [
        "0x004177e4", "0x0050d063", "0x00913763", "0x00913a1b"
    ]
    adj = data["adjudication"]
    assert adj["decoded_x87_env_site_surface_complete"] is True
    assert adj["real_x87_env_save_instruction_count"] == 2
    assert adj["x87_saved_eip_extraction_found"] is False
    assert adj["x87_fstenv_eip_capture_surface_complete"] is True


def test_false_decodes_are_data_and_padding_not_functions():
    rows = {row["address"]: row for row in json.loads(EVIDENCE.read_text(encoding="utf-8"))["classifications"]}
    assert rows["0x004177e4"]["owner"] is None
    assert "switch-table data" in rows["0x004177e4"]["classification"]
    assert rows["0x0050d063"]["owner"] is None
    assert "padding false decode" in rows["0x0050d063"]["classification"]


def test_real_env_saves_do_not_promote_global_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = {row["address"]: row for row in data["classifications"]}
    assert rows["0x00913763"]["owner"] == "FUN_00913576"
    assert rows["0x00913a1b"]["owner"] == "FUN_0091382e"
    assert "no saved-EIP extraction" in rows["0x00913763"]["classification"]
    adj = data["adjudication"]
    assert adj["noncanonical_eip_capture_surface_complete"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_parser_surfaces_x87_environment_save_mnemonics_only():
    module = load_tool()
    text = """Disassembly of section .text:\n  1000: d9 34 24              fnstenv [esp]\n  1003: d9 24 24              fldenv [esp]\n  1006: 90                    nop\n"""
    rows = module.x87_sites(module.parse_objdump(text))
    assert len(rows) == 1
    assert rows[0]["address"] == 0x1000


def test_tool_pins_hashes_sites_and_machine_windows():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.SQLITE_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert module.EXPECTED_SITES == [0x004177E4, 0x0050D063, 0x00913763, 0x00913A1B]
    assert module.JUMP_TABLE[0] == 0x004177D9
    assert module.JUMP_TABLE[-1] == 0x004177CC
    assert module.WINDOWS[0x00913760] == module.WINDOWS[0x00913A18]
