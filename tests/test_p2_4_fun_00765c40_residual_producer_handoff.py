import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_residual_producer_handoff.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_handoff.hpp"
COMPOSED = ROOT / "native_runtime/include/shift_fun_00765c40_composed_residual_executor.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_RESIDUAL_PRODUCER_HANDOFF.md"


def test_handoff_evidence_keeps_unresolved_producers_explicit() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40ResidualProducerHandoff/1"
    assert payload["ready"] is True
    assert payload["consumer"] == "SHIFT.Fun00765c40ComposedResidualExecutor/1"
    assert payload["payload_family_count"] == 8
    assert payload["payload_families"] == [
        "wheel_plane",
        "wheel_state_source_bits",
        "FUN_007584f0_computed_payloads",
        "wheel_pair",
        "contact_array",
        "contact_body_entries",
        "bounded_state_tail",
        "optional_body_sweep",
    ]
    preserved = payload["preserved_outside_handoff"]
    assert preserved["current_BODY_bytes"] == "native-owned"
    assert preserved["query_cache"] == "native-owned"
    assert "external scheduling seam" in preserved["wheel_job_queue_execution"]
    assert "0x00c133ac/+0x1c0" in preserved["lower_scene_query_provider"]
    claims = payload["claims"]
    assert claims["producer_formulas_internalized"] is False
    assert claims["top_level_provider_result_extended"] is False
    assert claims["top_level_provider_removed"] is False
    assert claims["complete_FUN_00765c40_internalized"] is False
    assert claims["external_provider_count_after"] == 7


def test_handoff_header_and_composed_bridge_cover_exact_payload_families() -> None:
    header = HEADER.read_text(encoding="utf-8")
    composed = COMPOSED.read_text(encoding="utf-8")
    assert "SHIFT.Fun00765c40ResidualProducerHandoff/1" in header
    assert "kFun00765c40ResidualProducerHandoffFamilyCount = 8u" in header
    for field in [
        "wheel_plane",
        "wheel_state_source_bits",
        "persistent_write",
        "wheel_pair",
        "contact_array",
        "contact_body_entries",
        "bounded_state_tail",
        "optional_body_sweep",
    ]:
        assert field in header
        assert f"inputs.{field} = handoff.{field}" in composed
    assert "apply_fun_00765c40_residual_producer_handoff" in composed
    assert "inputs.current_body_bytes = handoff" not in composed
    assert "inputs.cached_query_handle = handoff" not in composed
    assert "inputs.execute_wheel_job_queue = handoff" not in composed
    assert "inputs.read_load_term = handoff" not in composed
    assert "inputs.initial_body = handoff" not in composed


def test_stable_cmake_and_docs_keep_provider_removal_fail_closed() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00765c40_residual_producer_handoff_check" in cmake
    assert "native-physics-phase" not in cmake
    doc = DOC.read_text(encoding="utf-8")
    assert "Complete `FUN_00765c40` internalization remains false" in doc
    assert "provider count remains 7" in doc
    assert "wheel-job queue execution" in doc
    assert "0x00c133ac" in doc
