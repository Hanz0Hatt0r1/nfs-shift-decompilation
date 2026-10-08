from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_later_response_branch_ownership.json"
ANALYZER = ROOT / "tools/ghidra/analyze_fun_00766510_later_response_branch.py"
DOC = ROOT / "docs/PROCESS_1_FUN_00766510_LATER_RESPONSE_BRANCH.md"


def test_later_response_branch_contract_is_positive() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510LaterResponseBranchOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["xbox_recomp_required"] is False

    setup = payload["setup_owned"]
    assert setup["curve_3a08"] == (
        "FUN_00752f10 from VehicleLoadData+0xa38/+0xa40/+0xa48"
    )
    assert setup["application_vector_3a28"]["source"] == (
        "VehicleLoadData+0xc18 transformed by FUN_00753590"
    )
    assert setup["application_vector_3a28"]["storage"] == "+0x3a28/+0x3a30/+0x3a38"

    table = setup["table_3a40"]
    assert table["count"] == 6
    assert table["entry_stride"] == "0x18 bytes"
    assert table["source_record_stride"] == "0x48 bytes"
    assert table["source_record_first_component"] == "VehicleLoadData+0xa50"
    assert table["source_component_offsets_per_record"] == ["+0x00", "+0x14", "+0x28"]
    assert table["runtime_overwritten_lanes"] == ["+0x3ac0", "+0x3ac8"]


def test_sixth_table_entry_and_polynomial_state_remain_dynamic() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    state = payload["persistent_derived_state"]

    assert state["HDVehicle+0x3a00"]["writer"] == "FUN_00756b10"
    assert state["HDVehicle+0x3a00"]["formula"] == (
        "+0x3780*s^2 + +0x3778*s + +0x3770"
    )
    assert state["HDVehicle+0x3a00"]["writer_call_surface"] == [
        751615,
        752661,
        752742,
        761382,
    ]
    assert state["HDVehicle+0x3a00"]["setup_constant"] is False

    assert state["HDVehicle+0x3ac8"]["writer"] == "FUN_00756b10"
    assert state["HDVehicle+0x3ac8"]["formula"] == (
        "+0x3798*s^2 + +0x3790*s + +0x3788"
    )
    assert state["HDVehicle+0x3ac8"]["setup_constant"] is False
    assert state["HDVehicle+0x3ac0"]["runtime_write_line"] == 759727
    assert state["HDVehicle+0x3ac0"]["setup_constant"] is False

    mutable = state["mutable_coefficient_bases"]
    assert mutable["+0x3770"]["mutation"] == "FUN_00758000"
    assert mutable["+0x3788"]["mutation"] == "FUN_00758000"

    adjudication = payload["adjudication"]
    assert adjudication["later_response_branch_owner_closed"] is True
    assert adjudication["safe_to_model_whole_3a40_table_as_setup_constant"] is False
    assert adjudication["contact_response_provider_removable_now"] is False


def test_runtime_order_and_analyzer_anchors_are_pinned() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    runtime = payload["runtime_branch"]
    assert runtime["application_transform_line"] == 759711
    assert runtime["curve_line"] == 759724
    assert runtime["scale_line"] == 759725
    assert runtime["last_entry_y_refresh_line"] == 759727
    assert runtime["table_use_line"] == 759728
    assert runtime["body_apply_line"] == 759730
    assert runtime["cross_product_line"] == 759731
    assert runtime["caller_accumulator_line"] == 759732
    assert runtime["diagnostic_gate_line"] == 759738
    assert runtime["diagnostic_write_line"] == 759748

    text = ANALYZER.read_text(encoding="utf-8")
    for token in (
        "param_2 + 0xa38",
        "param_2 + 0xa68",
        "param_2 + 0x9f4",
        "param_2 + 0xc18",
        "+ 0x3ac0) =",
        "+ 0x3ac8) =",
        "FUN_00756b10(",
        "FUN_007551e0((void *)((int)param_1 + 0x3a40)",
        "FUN_00753650(local_1a0,&local_108,local_120)",
    ):
        assert token in text

    doc = DOC.read_text(encoding="utf-8")
    assert "P1.1b" in doc
    assert "sixth entry" in doc
    assert "contact_response" in doc
