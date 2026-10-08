from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_optional_response_branch_ownership.json"
ANALYZER = ROOT / "tools/ghidra/analyze_fun_00766510_optional_response_branch.py"


def test_optional_branch_owner_contract_is_positive_and_pc_backed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510OptionalResponseBranchOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False

    setup = payload["setup_owned"]
    assert setup["gate_3bc8"]["source"] == "VehicleLoadData+0xf10"
    assert setup["coefficients"]["+0x3c00"] == "VehicleLoadData+0xf68"
    assert setup["coefficients"]["+0x3c30"] == "VehicleLoadData+0xf98"
    assert setup["curve_3c40"] == (
        "FUN_00752f10 from VehicleLoadData+0xfa8/+0xfb0/+0xfb8"
    )
    assert setup["application_vector_3c60"] == (
        "FUN_00753590 from VehicleLoadData+0xfc0 into +0x3c60/+0x3c68/+0x3c70"
    )


def test_plus_3bd0_is_persistent_mutable_state() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    state = payload["persistent_mutable"]["HDVehicle+0x3bd0"]
    assert state["initial_source"] == "evaluated VehicleLoadData+0xf14"
    assert state["setup_constant"] is False
    assert state["mutation_surface"] == {
        "FUN_00757fa0_increment": 752639,
        "FUN_00758170_clamp": 752714,
        "FUN_00769d60_reset_clamp": 761376,
        "FUN_0076ed60_state_load": 764269,
    }
    adjudication = payload["adjudication"]
    assert adjudication["plus_3bd0_requires_persistent_mutation_model"] is True
    assert adjudication["safe_to_freeze_whole_optional_block_as_setup_config"] is False
    assert adjudication["contact_response_provider_removable_now"] is False


def test_optional_runtime_order_and_analyzer_are_pinned() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    runtime = payload["runtime_branch"]
    assert runtime["gate_line"] == 759577
    assert runtime["curve_line"] == 759611
    assert runtime["scalar_apply_line"] == 759615
    assert runtime["application_vector_line"] == 759618
    assert runtime["body_apply_line"] == 759619
    assert runtime["caller_accumulator_line"] == 759621
    assert runtime["diagnostic_write_line"] == 759630
    assert runtime["negative_result_required_for_body_apply"] is True

    text = ANALYZER.read_text(encoding="utf-8")
    for token in (
        "param_2 + 0xf10",
        "param_2 + 0xf14",
        "param_2 + 0xfa8",
        "param_2 + 0xfc0",
        "FUN_00757fa0_increment",
        "FUN_0076ed60_state_load",
        "runtime_scalar_apply",
    ):
        assert token in text
