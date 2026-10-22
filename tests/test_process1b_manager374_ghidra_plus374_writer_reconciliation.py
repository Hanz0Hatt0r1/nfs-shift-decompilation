from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1b_manager374_ghidra_plus374_writers.py"
EXPORTER = ROOT / "tools/ghidra/ShiftScalarUseExporter.java"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_ghidra_plus374", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def binary_payload(**overrides):
    payload = {
        "format": "SHIFT.GhidraEvidenceDatabase/1",
        "program_name": "SHIFT.exe",
        "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
        "language_id": "x86:LE:32:default",
        "image_base": "0x00400000",
        "pointer_size": 4,
        "memory_blocks": [
            {"name": ".text", "write": False, "execute": True},
            {"name": ".rdata", "write": False, "execute": False},
            {"name": ".data", "write": True, "execute": False},
        ],
    }
    payload.update(overrides)
    return payload


def raw_inventory(sites: list[str]):
    return {
        "format": "SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1",
        "authority": {
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
        },
        "scope": {
            "whole_text_scan": True,
            "computed_address_writes_included": False,
        },
        "inventory": {
            "literal_write_site_count": len(sites),
            "sites": [{"site": site} for site in sites],
        },
    }


def row(address: str, mnemonic: str, operand: str, *, operand_index: int = 0, text: str | None = None):
    return {
        "format": "SHIFT.GhidraScalarUses/1",
        "program": "SHIFT.exe",
        "target_scalar": "0x374",
        "function_address": "0x00401000",
        "function_name": "FUN_00401000",
        "instruction_address": address,
        "mnemonic": mnemonic,
        "text": text or f"{mnemonic} {operand}",
        "matching_operand_index": operand_index,
        "matching_operand_text": operand,
        "usage_class": "memory-or-copy",
    }


def prepare(tmp_path: Path, rows: list[dict], raw_sites: list[str], binary: dict | None = None):
    rows_path = tmp_path / "scalar.jsonl"
    binary_path = tmp_path / "binary.json"
    inventory_path = tmp_path / "inventory.json"
    write_rows(rows_path, rows)
    write_json(binary_path, binary or binary_payload())
    write_json(inventory_path, raw_inventory(raw_sites))
    return rows_path, binary_path, inventory_path


def test_exact_write_sites_reconcile_and_final_gates_stay_false(tmp_path: Path) -> None:
    tool = load_tool()
    paths = prepare(
        tmp_path,
        [
            row("0x00401010", "MOV", "DWORD PTR [ESI + 0x374]"),
            row("0x00401020", "ADD", "DWORD PTR [ECX + EDX*4 + 0x374]"),
            row(
                "0x00401030",
                "LEA",
                "[ESI + 0x374]",
                operand_index=1,
                text="LEA EAX,[ESI + 0x374]",
            ),
            row("0x00401040", "CMP", "DWORD PTR [EBX + 0x374]"),
            row("0x00401050", "MOV", "DWORD PTR [ESI + 0x1374]"),
        ],
        ["0x00401010", "0x00401020"],
    )

    payload = tool.analyze(*paths)
    assert payload["format"] == "SHIFT.P1B.Manager374GhidraPlus374WriterReconciliation/1"
    assert payload["authority"]["ghidra_program_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    surface = payload["surface"]
    assert surface["ghidra_exact_scalar_use_count"] == 5
    assert surface["ghidra_exact_plus_374_write_candidate_count"] == 2
    assert [row["site"] for row in surface["ghidra_exact_plus_374_write_candidates"]] == [
        "0x00401010",
        "0x00401020",
    ]
    assert surface["ghidra_exact_plus_374_other_first_memory_operand_count"] == 1
    assert surface["ghidra_exact_plus_374_other_first_memory_operands"][0]["site"] == "0x00401040"
    assert surface["ghidra_skipped_non_destination_or_non_exact_memory_use_count"] == 2
    assert surface["missing_from_ghidra"] == []
    assert surface["extra_in_ghidra"] == []

    adjudication = payload["adjudication"]
    assert adjudication["ghidra_literal_plus_0x374_writer_site_reconciliation_complete"] is True
    assert adjudication["all_plus_374_candidate_receivers_classified"] is False
    assert adjudication["unknown_or_unrelated_manager_root_alias_surface_complete"] is False
    assert adjudication["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adjudication["global_manager_root_origin_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_reconciliation_surfaces_missing_and_extra_sites(tmp_path: Path) -> None:
    tool = load_tool()
    paths = prepare(
        tmp_path,
        [
            row("0x00401010", "MOV", "DWORD PTR [ESI + 0x374]"),
            row("0x00401030", "MOV", "DWORD PTR [EDI + 0x374]"),
        ],
        ["0x00401010", "0x00401020"],
    )
    payload = tool.analyze(*paths)
    assert payload["surface"]["missing_from_ghidra"] == ["0x00401020"]
    assert payload["surface"]["extra_in_ghidra"] == ["0x00401030"]
    assert payload["adjudication"]["ghidra_literal_plus_0x374_writer_site_reconciliation_complete"] is False


def test_ghidra_float_ptr_x87_writes_reconcile_with_retail_sites(tmp_path: Path) -> None:
    tool = load_tool()
    sites = ["0x004826a6", "0x00865013", "0x00a44ac5"]
    paths = prepare(
        tmp_path,
        [
            row(site, "FSTP", "float ptr [ESI + 0x374]")
            for site in sites[:2]
        ]
        + [row(sites[2], "FSTP", "float ptr [EBX + 0x374]")],
        sites,
    )

    payload = tool.analyze(*paths)
    surface = payload["surface"]
    assert surface["ghidra_exact_plus_374_write_candidate_count"] == 3
    assert [item["site"] for item in surface["ghidra_exact_plus_374_write_candidates"]] == sites
    assert surface["ghidra_write_mnemonic_counts"] == {"fstp": 3}
    assert surface["missing_from_ghidra"] == []
    assert surface["extra_in_ghidra"] == []
    assert payload["adjudication"]["ghidra_literal_plus_0x374_writer_site_reconciliation_complete"] is True
    assert payload["adjudication"]["manager_374_join_to_hdvehicle_4330_complete"] is False


def test_program_identity_drift_fails_closed(tmp_path: Path) -> None:
    tool = load_tool()
    paths = prepare(
        tmp_path,
        [row("0x00401010", "MOV", "DWORD PTR [ESI + 0x374]")],
        ["0x00401010"],
        binary_payload(executable_md5="00000000000000000000000000000000"),
    )
    with pytest.raises(ValueError, match="unexpected executable MD5"):
        tool.analyze(*paths)


def test_wrong_scalar_and_duplicate_rows_fail_closed(tmp_path: Path) -> None:
    tool = load_tool()
    bad = row("0x00401010", "MOV", "DWORD PTR [ESI + 0x374]")
    bad["target_scalar"] = "0x28b8"
    paths = prepare(tmp_path, [bad], ["0x00401010"])
    with pytest.raises(ValueError, match="target scalar drift"):
        tool.analyze(*paths)

    paths = prepare(
        tmp_path,
        [
            row("0x00401010", "MOV", "DWORD PTR [ESI + 0x374]"),
            row("0x00401010", "ADD", "DWORD PTR [ECX + 0x374]"),
        ],
        ["0x00401010"],
    )
    with pytest.raises(ValueError, match="duplicate instruction row"):
        tool.analyze(*paths)


def test_shared_ghidra_exporter_is_exact_scalar_candidate_inventory() -> None:
    source = EXPORTER.read_text(encoding="utf-8")
    assert 'FORMAT = "SHIFT.GhidraScalarUses/1"' in source
    assert "instanceof Scalar" in source
    assert "Long.compareUnsigned" in source
    assert '"\\\"program\\\":" + q(instruction.getProgram().getName())' in source
    assert "Candidate inventory only" in source
    assert "scalar equality is never semantic object identity" in source
