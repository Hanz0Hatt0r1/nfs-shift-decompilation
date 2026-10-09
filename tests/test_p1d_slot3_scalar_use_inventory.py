from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_scalar_uses.py"
EXPORTER = ROOT / "tools/ghidra/ShiftScalarUseExporter.java"


def load_tool():
    spec = importlib.util.spec_from_file_location("slot3_scalar_inventory", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def row(**overrides):
    payload = {
        "format": "SHIFT.GhidraScalarUses/1",
        "program": "SHIFT.exe",
        "target_scalar": "0x28b8",
        "function_address": "0x00750000",
        "function_name": "FUN_00750000",
        "instruction_address": "0x00750010",
        "mnemonic": "LEA",
        "text": "LEA EAX,[ESI + 0x28b8]",
        "matching_operand_index": 1,
        "matching_operand_text": "[ESI + 0x28b8]",
        "usage_class": "address-materializer",
    }
    payload.update(overrides)
    return payload


def test_inventory_groups_exact_28b8_uses_and_stays_fail_closed(tmp_path: Path) -> None:
    tool = load_tool()
    input_path = tmp_path / "rows.jsonl"
    write_rows(
        input_path,
        [
            row(),
            row(
                instruction_address="0x00750020",
                mnemonic="MOV",
                text="MOV EAX,[ESI + 0x28b8]",
                usage_class="memory-or-copy",
            ),
            row(
                function_address="0x00760000",
                function_name="FUN_00760000",
                instruction_address="0x00760004",
                mnemonic="ADD",
                text="ADD EDI,0x28b8",
                matching_operand_index=1,
                matching_operand_text="0x28b8",
                usage_class="arithmetic",
            ),
        ],
    )

    payload = tool.analyze(input_path)
    assert payload["format"] == "SHIFT.P1D.Slot3ScalarUseInventory/1"
    assert payload["owner"] == "Process 1D / P1.3D"
    assert payload["target"] == "HDVehicle+0x28b8"
    inventory = payload["inventory"]
    assert inventory["exact_scalar_use_count"] == 3
    assert inventory["function_group_count"] == 2
    assert inventory["address_materializer_count"] == 1
    assert inventory["usage_classes"] == {
        "address-materializer": 1,
        "arithmetic": 1,
        "memory-or-copy": 1,
    }
    adjudication = payload["adjudication"]
    assert adjudication["numeric_offset_equality_is_selected_hdvehicle_identity"] is False
    assert adjudication["selected_root_provenance_complete"] is False
    assert adjudication["slot3_writer_proven"] is False
    assert adjudication["p1_3d_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_inventory_rejects_wrong_scalar(tmp_path: Path) -> None:
    tool = load_tool()
    input_path = tmp_path / "rows.jsonl"
    write_rows(input_path, [row(target_scalar="0x13b8")])
    with pytest.raises(ValueError, match="target scalar drift"):
        tool.analyze(input_path)


def test_inventory_rejects_wrong_input_format(tmp_path: Path) -> None:
    tool = load_tool()
    input_path = tmp_path / "rows.jsonl"
    write_rows(input_path, [row(format="SHIFT.Other/1")])
    with pytest.raises(ValueError, match="unexpected format"):
        tool.analyze(input_path)


def test_ghidra_exporter_is_exact_scalar_and_candidate_only() -> None:
    source = EXPORTER.read_text(encoding="utf-8")
    assert 'FORMAT = "SHIFT.GhidraScalarUses/1"' in source
    assert "instanceof Scalar" in source
    assert "Long.compareUnsigned" in source
    assert 'mnemonic.equals("lea")' in source
    assert "Candidate inventory only" in source
    assert "scalar equality is never semantic object identity" in source
