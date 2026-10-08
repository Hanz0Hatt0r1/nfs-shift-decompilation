from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_early_response_branch_ownership.json"
ANALYZER = ROOT / "tools/ghidra/analyze_fun_00766510_early_response_branch.py"


def test_early_response_branch_contract_is_positive() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510EarlyResponseBranchOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False

    setup = payload["setup"]
    assert setup["clamp_3b00"]["source"] == "VehicleLoadData+0xcc8"
    assert setup["application_vector_3b08"]["storage"] == "+0x3b08/+0x3b10/+0x3b18"
    table = setup["table_3b20"]
    assert table["count"] == 6
    assert table["entry_stride"] == "0x18 bytes"
    assert table["source_record_stride"] == "0x48 bytes"
    assert table["source_record_first_component"] == "VehicleLoadData+0xd08"
    assert table["source_component_offsets_per_record"] == ["+0x00", "+0x14", "+0x28"]


def test_mutable_table_lane_and_persistent_state_are_not_frozen() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    state = payload["persistent_derived_state"]
    assert state["HDVehicle+0x3ae8"]["writer"] == "FUN_00756b60"
    assert state["HDVehicle+0x3ae8"]["setup_constant"] is False
    assert state["HDVehicle+0x3ae8"]["writer_call_surface"] == [
        751658,
        752626,
        752713,
        761375,
    ]
    assert state["HDVehicle+0x3ba8"]["runtime_write_line"] == 759541
    assert state["HDVehicle+0x3ba8"]["setup_constant"] is False
    adjudication = payload["adjudication"]
    assert adjudication["safe_to_model_whole_3b20_table_as_setup_constant"] is False
    assert adjudication["contact_response_provider_removable_now"] is False


def test_runtime_order_and_analyzer_anchors_are_pinned() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    runtime = payload["runtime_branch"]
    assert runtime["table_use_line"] == 759554
    assert runtime["application_transform_line"] == 759545
    assert runtime["body_apply_line"] == 759556
    assert runtime["caller_accumulator_write_line"] == 759558

    text = ANALYZER.read_text(encoding="utf-8")
    for token in (
        "param_2 + 0xcc8",
        "param_2 + 0xd20",
        "param_2 + 0xcd0",
        "+ 0x3ba8) =",
        "FUN_007551e0((void *)((int)param_1 + 0x3b20)",
        "FUN_007baa70(*(void **)((int)param_1 + 0x33a0)",
    ):
        assert token in text
