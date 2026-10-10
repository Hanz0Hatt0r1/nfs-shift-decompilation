import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_whole_image_literal_pointers.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_whole_image_literal_pointer_surface.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_whole_literals", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_zero_literal_pointer_hits():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1"
    assert data["authority"]["retail_file_size"] == 8_801_792
    assert data["carrier_set"]["count"] == 15
    surface = data["whole_image_surface"]
    assert surface["absolute_va_hit_count"] == 0
    assert surface["rva_hit_count"] == 0
    assert surface["absolute_va_hits"] == []
    assert surface["rva_hits"] == []


def test_gates_close_only_literal_encoding_classes():
    adj = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adj["whole_image_exact_carrier_absolute_va_literal_surface_complete"] is True
    assert adj["whole_image_exact_carrier_rva_literal_surface_complete"] is True
    assert adj["whole_image_exact_carrier_literal_pointer_hit_found"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["global_runtime_derived_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_scanner_surfaces_absolute_and_rva_literals():
    module = load_tool()
    address = module.CARRIERS["FUN_00769520"]
    base = 0x00400000
    blob = b"AA" + struct.pack("<I", address) + b"BB" + struct.pack("<I", address - base) + b"CC"
    result = module.scan_literals(blob, base)
    assert result["absolute_va_hits"] == [
        {"carrier": "FUN_00769520", "value": "0x00769520", "file_offset": 2}
    ]
    assert result["rva_hits"] == [
        {"carrier": "FUN_00769520", "value": "0x00369520", "file_offset": 8}
    ]


def test_tool_pins_retail_hash_size_and_carrier_count():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.EXPECTED_FILE_SIZE == 8_801_792
    assert len(module.CARRIERS) == 15
