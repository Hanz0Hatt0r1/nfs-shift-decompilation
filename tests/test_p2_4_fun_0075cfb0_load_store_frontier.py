import json
from pathlib import Path

from src.physics import native_vehicle_external_provider_frontier_p2_4_current as p2_4

ROOT = Path(__file__).resolve().parents[1]
CURRENT_EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_current_frontier.json"
LOAD_STORE_HEADER = ROOT / "native_runtime/include/shift_fun_0075cfb0_load_store_surface.hpp"


def test_current_frontier_exposes_native_load_store_surface_without_formula_promotion() -> None:
    report = p2_4.build_current_frontier()
    fun = report["fun_00765c40"]

    assert p2_4.WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT == "SHIFT.Fun0075cfb0LoadStoreSurface/1"
    assert fun["wheel_job_load_store_surface_contract"] == p2_4.WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT
    assert fun["wheel_job_load_store_surface_native"] is True
    assert fun["wheel_job_load_store_site_count"] == 3
    assert fun["wheel_job_load_store_payload_bit_preserved"] is True
    assert fun["wheel_job_formula_internalized"] is False
    assert fun["wheel_job_branch_predicates_internalized"] is False
    assert fun["residual_producer_promotion_authorized_family_count"] == 0
    assert "wheel_job_formula_FUN_0075cfb0" in fun["remaining_explicit_producers"]
    assert report["external_provider_count"] == 7
    assert report["guards"]["wheel_job_commit_surface_treated_as_formula_proof"] is False


def test_current_frontier_evidence_matches_load_store_contract() -> None:
    payload = json.loads(CURRENT_EVIDENCE.read_text(encoding="utf-8"))
    fun = payload["fun_00765c40"]
    header = LOAD_STORE_HEADER.read_text(encoding="utf-8")

    assert fun["wheel_job_load_store_surface_contract"] in header
    assert fun["wheel_job_load_store_surface_native"] is True
    assert fun["wheel_job_load_store_site_count"] == 3
    assert fun["wheel_job_formula_internalized"] is False
    assert fun["wheel_job_branch_predicates_internalized"] is False
    assert payload["guards"]["wheel_job_commit_surface_treated_as_formula_proof"] is False
    assert payload["external_provider_count"] == 7


def test_contract_keeps_wheel_job_formula_fail_closed() -> None:
    contract = p2_4.contract()
    assert contract["wheel_job_load_store_surface_contract"] == p2_4.WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT
    assert contract["wheel_job_load_store_surface_native"] is True
    assert contract["wheel_job_load_store_site_count"] == 3
    assert contract["wheel_job_formula_internalized"] is False
    assert contract["wheel_job_branch_predicates_internalized"] is False
    assert "wheel_job_formula_FUN_0075cfb0" in contract["remaining_explicit_producers"]
    assert contract["residual_producer_promotion_authorized_family_count"] == 0
