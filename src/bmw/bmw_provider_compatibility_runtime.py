"""Provider compatibility gate for the real BMW M3 E36 SDF seed evidence.

The gate distinguishes dimension-incompatible, seed-mask-incompatible and
runtime-provider-match-unproven. It never promotes the seed matrix to the
final runtime matrix because numeric coupling may add non-zero coefficients.
"""
from __future__ import annotations

from typing import Any, Mapping

from specialized_provider_runtime import get_provider, provider_signature

FORMAT = "SHIFT.BMWM3ProviderCompatibility/1"

BMW_SEED = {
    "archive_sha256": "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70",
    "sdf_sha256": "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed",
    "runtime_constraint_records": 28,
    "solver_scalar_count": 40,
    "matrix_cells": 1600,
    "nonzero_cells": 700,
    "zero_cells": 900,
    "symmetric": True,
    "diagonal_one": True,
}

def derive_strict_upper_seed_nonzero(evidence: Mapping[str, Any]) -> int:
    n = int(evidence["solver_scalar_count"])
    nonzero = int(evidence["nonzero_cells"])
    if n < 0 or nonzero < 0:
        raise ValueError("solver and non-zero counts must be non-negative")
    if not bool(evidence.get("symmetric")):
        raise ValueError("strict-upper derivation requires symmetric evidence")
    if not bool(evidence.get("diagonal_one")):
        raise ValueError("strict-upper derivation requires the diagonal-one invariant")
    diagonal = n
    off_diagonal = nonzero - diagonal
    if off_diagonal < 0 or off_diagonal % 2:
        raise ValueError("symmetric off-diagonal count must be non-negative and even")
    return off_diagonal // 2

def classify_bmw_seed_against_provider(provider_id: int, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(BMW_SEED if evidence is None else evidence)
    provider = get_provider(provider_id)
    actual_dimension = int(source["solver_scalar_count"])
    seed_upper_nonzero = derive_strict_upper_seed_nonzero(source)
    expected = int(sum(bool(bit) for bit in provider_signature(provider_id)))
    if actual_dimension != provider.scalar_count:
        return {
            "format": FORMAT, "version": 1, "provider_id": provider_id,
            "status": "dimension-incompatible", "runtime_match_status": "unproven",
            "dimension": {"expected": provider.scalar_count, "actual": actual_dimension, "compatible": False},
            "seed_upper_nonzero": seed_upper_nonzero,
            "provider_expected_upper_nonzero": expected, "evidence": source,
        }
    if seed_upper_nonzero != expected:
        return {
            "format": FORMAT, "version": 1, "provider_id": provider_id,
            "status": "seed-mask-incompatible", "runtime_match_status": "requires-capture",
            "dimension": {"expected": provider.scalar_count, "actual": actual_dimension, "compatible": True},
            "seed_upper_nonzero": seed_upper_nonzero, "provider_expected_upper_nonzero": expected,
            "additional_upper_nonzero_cells_required_to_match": expected - seed_upper_nonzero,
            "evidence": source,
        }
    return {
        "format": FORMAT, "version": 1, "provider_id": provider_id,
        "status": "seed-count-compatible", "runtime_match_status": "requires-capture",
        "dimension": {"expected": provider.scalar_count, "actual": actual_dimension, "compatible": True},
        "seed_upper_nonzero": seed_upper_nonzero, "provider_expected_upper_nonzero": expected,
        "additional_upper_nonzero_cells_required_to_match": 0, "evidence": source,
    }

def build_bmw_provider_compatibility_gate(evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(BMW_SEED if evidence is None else evidence)
    return {
        "format": FORMAT, "version": 1,
        "bmw_seed_upper_nonzero": derive_strict_upper_seed_nonzero(source),
        "results": {
            "provider_0": classify_bmw_seed_against_provider(0, source),
            "provider_1": classify_bmw_seed_against_provider(1, source),
        },
        "runtime_selection": {
            "provider_0": "unproven-until-final-pre-solve-capture",
            "provider_1": "dimension-incompatible-with-BMW-40-scalar-domain",
            "generic_fallback": "still-possible",
        },
        "status": "capture-gated",
        "limitations": [
            "Seed-mask incompatibility only proves the provider pattern cannot match the pre-numeric seed.",
            "Final provider selection occurs after the matrix has been populated numerically.",
            "No provider is assigned to BMW without a real frame-entry/pre-solve capture.",
        ],
    }

def validate_bmw_provider_gate(gate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if int(gate.get("bmw_seed_upper_nonzero", -1)) != 330:
        errors.append("unexpected-bmw-seed-upper-nonzero")
    p0 = (gate.get("results") or {}).get("provider_0") or {}
    p1 = (gate.get("results") or {}).get("provider_1") or {}
    if p0.get("status") != "seed-mask-incompatible":
        errors.append("provider0-status-mismatch")
    if p0.get("provider_expected_upper_nonzero") != 450:
        errors.append("provider0-expected-count-mismatch")
    if p0.get("additional_upper_nonzero_cells_required_to_match") != 120:
        errors.append("provider0-delta-mismatch")
    if p1.get("status") != "dimension-incompatible":
        errors.append("provider1-status-mismatch")
    return {"format": FORMAT.replace("/1", "Validation/1"), "version": 1, "ready": not errors, "errors": errors}

if __name__ == "__main__":
    import json
    gate = build_bmw_provider_compatibility_gate()
    print(json.dumps(gate, indent=2, sort_keys=True))
