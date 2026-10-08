import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_residual_producer_promotion_gate.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_promotion_gate.hpp"
NATIVE_TEST = ROOT / "native_runtime/tests/fun_00765c40_residual_producer_promotion_gate_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_RESIDUAL_PRODUCER_PROMOTION_GATE.md"


def test_promotion_gate_evidence_is_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40ResidualProducerPromotionGate/2"
    assert payload["extends_historical_format"] == "SHIFT.Fun00765c40ResidualProducerPromotionGate/1"
    assert payload["ready"] is True
    assert payload["dependencies"]["producer_handoff"] == "SHIFT.Fun00765c40ResidualProducerHandoff/2"
    assert payload["dependencies"]["composed_executor"] == "SHIFT.Fun00765c40ComposedResidualExecutor/1"
    receipts = payload["proof_receipts"]
    assert receipts["family_count"] == 8
    assert receipts["storage"] == "proof_contract_ids[8]"
    assert receipts["default"] == "all empty"
    assert receipts["empty_contract_id_rejected"] is True
    assert receipts["receipt_is_evidence"] is False
    assert receipts["named_contract_remains_authority"] is True
    rule = payload["promotion_rule"]
    assert rule["present_family_requires_named_independent_proof"] is True
    assert rule["absent_family_requires_proof"] is False
    assert rule["legacy_v1_all_family_witness_requires_all_eight_named_proofs"] is True
    assert rule["selective_v2_witness_can_promote_individual_family"] is True
    assert rule["known_invariant_validation_runs_before_promotion"] is True
    assert rule["direct_session_promotion_wired"] is False
    guards = payload["guards"]
    assert guards["presence_treated_as_proof"] is False
    assert guards["anonymous_boolean_authorization_allowed"] is False
    assert guards["empty_proof_contract_allowed"] is False
    assert guards["unproven_family_applied"] is False
    assert payload["scope"]["authorized_family_count_in_production"] == 0
    assert payload["scope"]["remaining_producer_owner_blockers"] == 9
    assert payload["scope"]["external_provider_count_after"] == 7
    assert payload["scope"]["complete_FUN_00765c40_internalized"] is False


def test_promotion_header_requires_named_contract_receipts() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00765c40ResidualProducerPromotionGate/2" in header
    assert "SHIFT.Fun00765c40ResidualProducerPromotionGate/1" in header
    assert "Fun00765c40ResidualProducerProofMask" in header
    assert "proof_contract_ids{}" in header
    assert "std::string_view proof_contract_id" in header
    assert "proof contract id must be non-empty" in header
    assert "fun_00765c40_residual_producer_family_proof_contract" in header
    assert "fun_00765c40_residual_producer_family_is_proven" in header
    assert "fun_00765c40_residual_producer_family_is_present" in header
    assert "present without named independent proof contract" in header
    assert "validate_fun_00765c40_residual_producer_handoff_known_invariants" in header
    assert "apply_proven_fun_00765c40_residual_producer_handoff" in header
    assert "std::array<bool" not in header


def test_native_regression_covers_named_selective_and_legacy_promotion() -> None:
    source = NATIVE_TEST.read_text(encoding="utf-8")
    for witness in (
        "unproven_rejected",
        "empty_contract_rejected",
        "kWheelStateTestProof",
        "proof_contract_receipt_preserved",
        "partial_legacy_proof_rejected",
        "legacy_promoted",
        "empty_selective",
    ):
        assert witness in source
    assert "TEST.Fun00765c40WheelStateSourceProof/1" in source
    assert "TEST.Fun00765c40ProducerProof/1" in source
    assert '\\"external_provider_count_after\\":7' in source
    assert '\\"complete_fun_00765c40_internalized\\":false' in source


def test_stable_p2_4_cmake_and_docs_keep_session_unwired() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00765c40_residual_producer_promotion_gate_check" in cmake
    assert "native-physics-phase" not in cmake
    doc = DOC.read_text(encoding="utf-8")
    assert "receipt" in doc.lower()
    assert "not itself evidence" in doc.lower()
    assert "does not wire the gate into the active session" in doc
    assert "external provider count remains **7**" in doc
    assert "0x00c133ac" in doc
