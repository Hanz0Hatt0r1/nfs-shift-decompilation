from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_selected_bmw_query_fallback.json"
SETUP_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_selected_bmw_query_fallback.hpp"
PASS_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
CDF = Path("/mnt/data/bmw_m3_e36.cdf")


def test_phase741_evidence_freezes_pc_setup_and_selected_resource() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40SelectedBMWQueryFallback/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["setup_function"] == "FUN_00756bb0"
    assert payload["source"]["setup_machine_span"]["raw_byte_sha256"] == (
        "b144e5ff3a8eb7d73f627fbbebc20b362cf1155398d6a48cac3c74eb65da9960"
    )

    setup = payload["retail_setup"]
    assert setup["fw_max_height_base"] == "setup param_2+0x6a4"
    assert setup["fw_max_height_evaluated_f32"] == "setup param_2+0x6a8"
    assert setup["caller_fallback_f64"] == "HDVehicle+0x38e8"
    assert setup["operation_order"][-2:] == [
        "widen same f32 to f64",
        "store f64 to HDVehicle+0x38e8",
    ]

    resource = payload["resource"]
    assert resource["cdf_sha256"] == (
        "bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d"
    )
    assert resource["section"] == "FRONTWING"
    assert resource["field"] == "FWMaxHeight"
    assert resource["text_value"] == "0.10"
    assert resource["f32_bits"] == "0x3dcccccd"
    assert resource["widened_f64_bits"] == "0x3fb99999a0000000"


def test_phase741_active_contract_removes_selected_bmw_provider_authority() -> None:
    setup_header = SETUP_HEADER.read_text(encoding="utf-8")
    pass_header = PASS_HEADER.read_text(encoding="utf-8")

    assert "SHIFT.Fun00765c40SelectedBMWQueryFallback/1" in setup_header
    assert "kFun00756bb0CallerFallbackOffset = 0x38e8u" in setup_header
    assert "kFun00756bb0FWMaxHeightBaseOffset = 0x6a4u" in setup_header
    assert "kFun00756bb0FWMaxHeightEvaluatedOffset = 0x6a8u" in setup_header
    assert "0x3dcccccdu" in setup_header
    assert "0x3fb99999a0000000ull" in setup_header
    assert "selected_bmw_m3_e36_fun_00765c40_query_fallback" in setup_header

    assert "SHIFT.Fun00765c40ExternalPassInput/2" in pass_header
    assert "selected_bmw_miss_fallback" in pass_header
    assert "result.query_input.miss_fallback != *selected_fallback" in pass_header
    assert "native-owned selected BMW +0x38e8 fallback" in pass_header


def test_phase741_does_not_generalize_selected_value_or_close_collision_provider() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["selected_bmw_miss_fallback_provider_authority_removed"] is True
    assert scope["collision_provider_internalized"] is False
    assert scope["load_terms_external"] is True
    assert scope["generic_vehicle_value_generalized"] is False
    assert scope["physical_semantics_invented"] is False

    shared = payload["shared_state"]
    assert shared["FUN_00765c40_miss_fallback_read"] is True
    assert shared["FUN_00766510_upper_clamp_bound_read"] is True
    assert shared["contact_response_provider_internalized_by_this_phase"] is False
