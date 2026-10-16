from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "tools/ghidra/adapt_revenginstr_address_references.py"
SPEC = importlib.util.spec_from_file_location("global_reference_adapter", ADAPTER_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def test_adapts_generic_references_to_legacy_shift_shape(tmp_path: Path) -> None:
    generic = {
        "format": "REVENGINSTR.GhidraAddressReferences/1",
        "program": "sample",
        "executable_md5": "0123456789abcdef0123456789abcdef",
        "requested": "DAT_00104010",
        "resolved_address": "0x00104010",
        "found": True,
        "target_block": ".data",
        "primary_symbol": "sample_value",
        "data_type": "int",
        "data_length": 4,
        "reference_count": 1,
        "function_addresses": ["0x00101119"],
        "references": [{
            "from": "0x00101120",
            "type": "DATA",
            "source": "ANALYSIS",
            "operand_index": 1,
            "primary": True,
            "function_address": "0x00101119",
            "function_name": "sample_reader",
            "instruction": "MOV EAX,dword ptr [0x00104010]",
        }],
    }
    source = tmp_path / "generic.jsonl"
    destination = tmp_path / "shift.jsonl"
    source.write_text(json.dumps(generic) + "\n", encoding="utf-8")

    adapter.adapt_file(source, destination)

    result = json.loads(destination.read_text(encoding="utf-8"))
    assert result == {
        "format": "SHIFT.GhidraGlobalReferences/1",
        "program": "sample",
        "executable_md5": "0123456789abcdef0123456789abcdef",
        "requested": "DAT_00104010",
        "resolved_address": "0x00104010",
        "found": True,
        "primary_symbol": "sample_value",
        "data_type": "int",
        "data_length": 4,
        "reference_count": 1,
        "function_addresses": ["0x00101119"],
        "references": [{
            "from": "0x00101120",
            "type": "DATA",
            "operand_index": 1,
            "primary": True,
            "function_address": "0x00101119",
            "function_name": "sample_reader",
            "instruction": "MOV EAX,dword ptr [0x00104010]",
        }],
    }


def test_rejects_unrecognized_generic_format() -> None:
    with pytest.raises(ValueError, match="REVENGINSTR.GhidraAddressReferences/1"):
        adapter.adapt_row({"format": "unknown"}, 1)


def test_shift_global_reference_runner_prefers_shared_exporter_with_fallback() -> None:
    runner = (ROOT / "tools/ghidra/run_shift_global_references.sh").read_text(encoding="utf-8")
    assert "ExportGhidraAddressReferences.java" in runner
    assert "ShiftGlobalReferenceExporter.java" in runner
    assert "adapt_revenginstr_address_references.py" in runner
    assert "USE_SHARED_EXPORTER" in runner
