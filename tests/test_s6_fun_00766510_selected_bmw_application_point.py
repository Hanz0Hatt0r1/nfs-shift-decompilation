from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_selected_bmw_application_point.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_selected_bmw_application_point.hpp"
PHASE742 = ROOT / "native_runtime/cmake/phase742.cmake"
PHASE743 = ROOT / "native_runtime/cmake/phase743.cmake"


def test_phase743_evidence_reuses_phase727_rotated_scratch() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510SelectedBMWApplicationPoint/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    source = payload["pc_source"]
    assert source["producer_function"] == "FUN_00765c40"
    assert source["producer_source_line"] == 759159
    assert source["consumer_function"] == "FUN_00766510"
    assert source["consumer_application_source_line"] == 759688

    machine = payload["pc_machine"]
    assert machine["producer_span_sha256"] == (
        "b040d039c8913e6c9f332159ee20dc393f6454a564f9da2f955c45be6fda5015"
    )
    assert machine["consumer_transform_application_sha256"] == (
        "db2e2358db25f5cc7a6d869e2a346fc40b0562702c79a32ea4245b4d4ea7dc57"
    )

    native = payload["native_owner"]
    assert native["existing_result_field"].endswith(".body_rotated_local")
    assert native["origin_added_world_position_used_as_application_point"] is False
    scope = payload["scope"]
    assert scope["application_point_source_owner_closed"] is True
    assert scope["runtime_provider_handoff_joined"] is False
    assert scope["external_provider_count_after"] == 7


def test_phase743_header_is_an_alias_not_a_recomputed_transform() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510SelectedBMWApplicationPoint/1" in text
    assert "kFun00765c40RotatedScratchOffset = 0x38f0u" in text
    assert "world_transform.body_rotated_local" in text
    assert "world_transform.world_position" not in text
    assert "execute_fun_00765c40_world_position_transform" not in text
    assert "transform_fun_007aefb0_refresh" not in text


def test_phase743_preserves_same_pass_source_order_without_claiming_runtime_handoff() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    lifetime = payload["same_pass_lifetime"]
    assert lifetime["order"] == [
        "FUN_00765c40 writes +0x38f0",
        "FUN_00758b50 executes",
        "FUN_00766510 reads +0x38f0",
    ]
    assert lifetime["recomputed_by_FUN_00766510"] is False
    assert payload["scope"]["contact_response_provider_removed"] is False


def test_phase743_cmake_chains_after_phase742() -> None:
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase743.cmake)" in PHASE742.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00766510_selected_bmw_application_point_check" in PHASE743.read_text(encoding="utf-8")
