from __future__ import annotations

import json
from pathlib import Path

from src.physics import native_vehicle_external_provider_frontier_p2_4_current as current

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_residual_producer_session_capture.json"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
EXTERNAL_RESULT = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
HANDOFF_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_handoff.hpp"


def test_session_capture_evidence_is_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40ResidualProducerSessionCapture/1"
    assert payload["ready"] is True
    deps = payload["dependencies"]
    assert deps["external_result"] == "SHIFT.Fun00765c40ExternalPassResult/5"
    assert deps["producer_handoff"] == "SHIFT.Fun00765c40ResidualProducerHandoff/2"
    assert deps["historical_producer_handoff"] == "SHIFT.Fun00765c40ResidualProducerHandoff/1"
    assert payload["capture"]["pass_count"] == 2
    assert payload["capture"]["selective_family_presence_preserved"] is True
    assert payload["capture"]["persistent_session_state_added"] is False
    assert payload["ownership"]["witness_authoritative"] is False
    assert payload["ownership"]["witness_treated_as_native_computation"] is False
    assert payload["ownership"]["composed_executor_invoked_by_session"] is False
    assert payload["ownership"]["missing_witness_rejected"] is False
    assert payload["ownership"]["absent_family_promoted"] is False
    assert payload["ownership"]["remaining_explicit_producer_count"] == 9
    assert payload["boundaries"]["lower_scene_query_external"] is True
    assert payload["boundaries"]["external_provider_count_after"] == 7
    assert payload["boundaries"]["complete_FUN_00765c40_internalized"] is False


def test_session_result_captures_optional_witness_after_validation() -> None:
    header = SESSION_HEADER.read_text(encoding="utf-8")
    source = SESSION_SOURCE.read_text(encoding="utf-8")
    result_header = EXTERNAL_RESULT.read_text(encoding="utf-8")
    handoff_header = HANDOFF_HEADER.read_text(encoding="utf-8")

    assert "SHIFT.Fun00765c40ExternalPassResult/5" in result_header
    assert "std::optional<Fun00765c40ResidualProducerHandoff> residual_producer_handoff" in result_header
    assert "SHIFT.Fun00765c40ResidualProducerHandoff/2" in handoff_header
    assert "family_presence_explicit = false" in handoff_header
    assert "family_present{}" in handoff_header
    assert "fun_00765c40_residual_producer_handoffs" in header
    assert "fun_00765c40_residual_producer_handoff_capture_count" in header

    provider_call = source.index("providers_.fun_00765c40(pass_index, external_input)")
    validation = source.index("validate_fun_00765c40_external_pass_result", provider_call)
    query_snapshot = source.index("materialize_fun_00765c40_session_query_snapshot", validation)
    cache_commit = source.index("fun_00765c40_query_cache_handle_ =", query_snapshot)
    witness_gate = source.index("if (result.residual_producer_handoff.has_value())", cache_commit)
    witness_store = source.index("residual_producer_handoffs[pass_index] =", witness_gate)
    result_store = source.index("result.fun_00765c40_residual_producer_handoffs =")

    assert provider_call < validation < query_snapshot < cache_commit < witness_gate < witness_store < result_store
    assert "++telemetry.fun_00765c40_residual_producer_handoff_capture_count" in source
    assert "execute_fun_00765c40_composed_residual_pass" not in source
    assert "missing residual producer handoff" not in source


def test_current_frontier_marks_selective_transport_not_ownership() -> None:
    payload = current.contract()
    assert payload["external_provider_count"] == 7
    assert payload["residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/2"
    assert payload["historical_residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/1"
    assert payload["residual_producer_handoff_threaded_through_provider_result"] is True
    assert payload["residual_producer_handoff_threaded_through_session_result"] is True
    assert payload["residual_producer_handoff_authoritative"] is False
    assert payload["residual_producer_handoff_selective_families"] is True
    assert payload["residual_producer_handoff_legacy_all_families_compatible"] is True
    assert payload["complete_internalization"] is False
    assert payload["provider_removed"] is False
    assert len(payload["remaining_explicit_producers"]) == 9
