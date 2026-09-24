"""Compare the committed BMW M3 golden manifest with exact parsed MEB evidence."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3MEBEvidenceParity/1"

def _norm(value: Any) -> str:
    return str(value or "").replace("\\","/").strip("/").lower()

def validate_bmw_meb_evidence(evidence: Mapping[str, Any], golden: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []
    source = evidence.get("source") or {}
    mesh = evidence.get("mesh") or {}
    golden_source = golden.get("golden") or {}
    golden_mesh = golden.get("mesh") or {}

    expected = {
        "resource": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
        "sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
        "archive": "Pakfiles/Vehicles/BMW_M3_E36.bff",
        "entry_index": 863,
        "resource_size": 300764,
        "compressed_size": 170520,
        "uncompressed_size": 300764,
        "vertex_count": 3550,
        "triangle_count": 5034,
    }
    observed = {
        "resource": source.get("root_relative_path") or evidence.get("resource"),
        "sha256": source.get("resource_sha256") or evidence.get("resource_sha256"),
        "archive": source.get("archive"),
        "entry_index": source.get("entry_index"),
        "resource_size": source.get("resource_size") or evidence.get("resource_size"),
        "compressed_size": source.get("entry_compressed_size"),
        "uncompressed_size": source.get("entry_uncompressed_size"),
        "vertex_count": mesh.get("vertex_count"),
        "triangle_count": mesh.get("triangle_count"),
    }
    for key, want in expected.items():
        got = observed.get(key)
        ok = str(got).lower() == str(want).lower()
        checks.append({"field": key, "expected": want, "observed": got, "status": "match" if ok else "mismatch"})
        if not ok:
            reasons.append(f"meb:{key}:mismatch")

    golden_obs = {
        "resource": golden_source.get("resource"),
        "sha256": golden_source.get("resource_sha256"),
        "vertex_count": golden_mesh.get("vertex_count"),
        "triangle_count": golden_mesh.get("triangle_count"),
    }
    for key in ("resource", "sha256", "vertex_count", "triangle_count"):
        ok = str(observed.get(key)).lower() == str(golden_obs.get(key)).lower()
        if not ok:
            reasons.append(f"golden:{key}:mismatch")

    if _norm(observed["resource"]) != _norm(expected["resource"]):
        reasons.append("meb:resource-path-mismatch")

    evidence_primitives = list(mesh.get("primitives") or [])
    golden_primitives = list(golden_mesh.get("primitives") or [])
    if evidence_primitives != golden_primitives:
        reasons.append("meb:primitive-definition-mismatch")

    evidence_descriptors = list(mesh.get("property_descriptors") or [])
    golden_descriptors = list(golden_mesh.get("property_descriptors") or [])
    if evidence_descriptors != golden_descriptors:
        reasons.append("meb:descriptor-definition-mismatch")

    evidence_layouts = list(mesh.get("property_layouts") or [])
    golden_layouts = list(golden_mesh.get("property_layouts") or [])
    if golden_layouts and evidence_layouts != golden_layouts:
        reasons.append("meb:property-layout-mismatch")

    return {
        "format": FORMAT,
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "checks": checks,
        "property_descriptors": evidence_descriptors,
        "property_layouts": evidence_layouts,
        "primitives": evidence_primitives,
    }
