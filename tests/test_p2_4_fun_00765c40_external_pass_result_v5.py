import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_external_pass_result_v5.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
HANDOFF = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_handoff.hpp"
HISTORICAL = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"


def test_result_v5_appends_optional_non_authoritative_producer_witness() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40ExternalPassResult/5"
    assert payload["extends_historical_result"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    field = payload["appended_field"]
    assert field["name"] == "residual_producer_handoff"
    assert field["trailing"] is True
    assert field["authoritative"] is False
    assert field["required_on_selected_bmw"] is False
    assert field["required_on_generic_fixtures"] is False
    assert payload["historical_prefix_preserved"] == [
        "load_terms", "query_input", "returned_cache_handle", "query_output"
    ]
    validation = payload["known_invariant_validation"]
    assert validation["enabled_when_witness_present"] is True
    assert validation["proven_finite_payload"] == "Fun007584f0ComputedInputs"
    assert validation["opaque_qword_payloads_reinterpreted"] is False
    assert validation["unproven_body_vector_ranges_added"] is False
    assert payload["ownership"]["producer_handoff_session_captured"] is True
    assert payload["scope"]["complete_FUN_00765c40_internalized"] is False
    assert payload["scope"]["top_level_provider_removed"] is False
    assert payload["scope"]["external_provider_count_after"] == 7


def test_active_header_preserves_v4_prefix_and_validates_only_known_witness_invariants() -> None:
    text = HEADER.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert '"SHIFT.Fun00765c40ExternalPassResult/5"' in text
    assert '"SHIFT.Fun00765c40ExternalPassResult/4"' in text
    prefix = [
        text.index("Fun00765c40LoadTerms load_terms"),
        text.index("Fun00765c40QueryInputBoundary query_input"),
        text.index("std::optional<std::uint64_t> returned_cache_handle"),
        text.index("std::optional<CollisionQueryOutput> query_output"),
        text.index("std::optional<Fun00765c40ResidualProducerHandoff> residual_producer_handoff"),
    ]
    assert prefix == sorted(prefix)
    assert "Absence is\n    // valid" in text
    assert "Presence does not make these values native-owned" in text
    assert "if (result.residual_producer_handoff.has_value())" in text
    assert "validate_fun_00765c40_residual_producer_handoff_known_invariants" in text
    assert "validate_fun_007584f0_computed_inputs(handoff.persistent_write)" in handoff
    assert "must not add guessed range/semantic constraints" in handoff


def test_phase744_historical_evidence_remains_v4() -> None:
    payload = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    assert payload["contracts"]["external_result"] == "SHIFT.Fun00765c40ExternalPassResult/4"
