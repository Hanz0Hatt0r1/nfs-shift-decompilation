import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_pe_loader_entry_surface.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_pe_loader_entry_surface.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_pe_loader", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_entry_export_tls_and_loadconfig_surfaces():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330PeLoaderEntrySurface/1"
    assert data["entrypoint"] == {
        "is_exact_carrier": False,
        "rva": "0x0050488a",
        "va": "0x0090488a",
    }
    exports = data["export_surface"]
    assert exports["dll_name"] == "GeckoFnl.exe"
    assert exports["function_count"] == 509
    assert exports["named_count"] == 509
    assert exports["forwarder_count"] == 0
    assert exports["zero_function_rva_count"] == 0
    assert exports["exact_carrier_export_hit_count"] == 0
    tls = data["tls_surface"]
    assert tls["directory_rva"] == "0x007672ac"
    assert tls["address_of_callbacks"] == "0x00aa9990"
    assert tls["callback_count"] == 0
    assert tls["exact_carrier_callback_hit_count"] == 0
    assert data["load_config_surface"]["present"] is False


def test_loader_subset_closes_without_promoting_runtime_indirect_gates():
    adj = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adj["exact_carrier_is_pe_entrypoint"] is False
    assert adj["exact_carrier_export_surface_complete"] is True
    assert adj["exact_carrier_export_found"] is False
    assert adj["tls_callback_surface_complete"] is True
    assert adj["exact_carrier_tls_callback_found"] is False
    assert adj["load_config_published_handler_surface_complete"] is True
    assert adj["pe_published_loader_entry_subset_complete"] is True
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_absent_exception_directory_does_not_claim_absent_inline_eh():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["pe_exception_directory"]
    assert row["present"] is False
    assert row["directory_rva"] == "0x00000000"
    assert "says nothing about x86 MSVC inline EH" in row["note"]


def test_tool_pins_carrier_count_and_retail_hash():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert len(module.CARRIERS) == 15
    assert module.CARRIERS["FUN_00769520"] == 0x00769520
    assert module.CARRIERS["FUN_00771e10"] == 0x00771E10
