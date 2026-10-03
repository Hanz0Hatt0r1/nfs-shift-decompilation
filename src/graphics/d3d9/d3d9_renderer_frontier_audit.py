"""Fold later exact offline evidence back into the renderer requirement frontier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.D3D9RendererFrontierAudit/1"
BASE_FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"
FXO_FORMAT = "SHIFT.IMBFXOPairProvenance/1"
MATERIAL_FORMAT = "SHIFT.IMBMaterialConstantCandidateJoin/1"


def _summary(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return report.get("summary") if isinstance(report, Mapping) and isinstance(report.get("summary"), Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def build_renderer_frontier_audit(
    base: Mapping[str, Any],
    *,
    fxo_provenance: Mapping[str, Any] | None = None,
    material_constants: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if base.get("format") != BASE_FORMAT:
        raise ValueError(f"base audit must be {BASE_FORMAT}")
    if fxo_provenance is not None and fxo_provenance.get("format") != FXO_FORMAT:
        raise ValueError(f"FXO provenance must be {FXO_FORMAT}")
    if material_constants is not None and material_constants.get("format") != MATERIAL_FORMAT:
        raise ValueError(f"material constants must be {MATERIAL_FORMAT}")

    requirements = [dict(row) for row in (base.get("requirements") or []) if isinstance(row, Mapping)]
    by_id = {str(row.get("requirement_id")): row for row in requirements}

    fxo_row = by_id.get("fx_fxo_exact_candidate_reduction")
    if fxo_row is not None and fxo_provenance is not None:
        summary = _summary(fxo_provenance)
        missing = _int(summary.get("missing_required_pair_count"))
        verified = _int(summary.get("verified_pair_count"))
        required = _int((fxo_provenance.get("ambiguity_filter") or {}).get("required_pair_count"))
        if fxo_provenance.get("ready") is True and missing == 0:
            fxo_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-byte-equality",
                "evidence": [
                    f"Phase 619 verified exact FXO VS/PS pairs={verified}",
                    f"required shader-provenance pairs={required}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            fxo_row.update({
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": [
                    f"Phase 619 verified exact FXO VS/PS pairs={verified}",
                    f"missing required pairs={missing}",
                ],
                "existing_next_step": "resolve the listed Phase 619 missing exact FXO pair provenance from the existing corpus before recapture",
            })

    material_row = by_id.get("material_bmt_correlation")
    if material_row is not None and material_constants is not None:
        summary = _summary(material_constants)
        total = _int(summary.get("material_distinct_draw_count"))
        resolved = _int(summary.get("single_candidate_draw_count"))
        remaining = _int(summary.get("remaining_ambiguous_draw_count"))
        if total == 0:
            material_row.update({
                "status": "no-active-blocker",
                "confidence": "deterministic-report-audit",
                "evidence": ["Phase 620 material-distinct draws=0"],
                "missing_observation": None,
                "existing_next_step": None,
            })
        elif remaining == 0 and resolved == total:
            material_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-f32-ctab-register-evidence",
                "evidence": [
                    f"Phase 620 material-distinct draws={total}",
                    f"resolved by exact material constants={resolved}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            material_row.update({
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": [
                    f"Phase 620 material-distinct draws={total}",
                    f"resolved by exact material constants={resolved}",
                    f"remaining material ambiguity={remaining}",
                ],
                "missing_observation": None,
                "existing_next_step": (
                    "apply exact BMT/DDS sampler descriptor/content evidence only to the remaining Phase 620 ambiguous rows; "
                    "do not request texture snapshots unless payload identity becomes a proven discriminator"
                ),
            })

    absent = [row for row in requirements if row.get("status") == "absent-in-capture"]
    tooling = [
        row for row in requirements
        if row.get("status") in {"present-needs-tooling", "ambiguous", "partial-capture-local"}
    ]
    capture_blockers = list(base.get("capture_blockers") or [])
    result = {
        "format": FORMAT,
        "version": 1,
        "status": "capture-required" if capture_blockers else "continue-offline",
        "summary": {
            "requirement_count": len(requirements),
            "closed_requirement_count": sum(
                str(row.get("status") or "").startswith("closed-") for row in requirements
            ),
            "present_needs_tooling_count": sum(
                row.get("status") == "present-needs-tooling" for row in requirements
            ),
            "ambiguous_requirement_count": sum(
                row.get("status") == "ambiguous" for row in requirements
            ),
            "absent_in_capture_count": len(absent),
            "capture_required_now": bool(capture_blockers),
            "phase619_applied": fxo_provenance is not None,
            "phase620_applied": material_constants is not None,
        },
        "requirements": requirements,
        "existing_data_requiring_tooling": [
            {
                "requirement_id": row.get("requirement_id"),
                "status": row.get("status"),
                "next_step": row.get("existing_next_step"),
            }
            for row in tooling
        ],
        "genuinely_absent_capture_observations": [
            {
                "requirement_id": row.get("requirement_id"),
                "missing_observation": row.get("missing_observation"),
            }
            for row in absent
        ],
        "capture_blockers": capture_blockers,
        "conditional_minimal_capture": list(base.get("conditional_minimal_capture") or []),
        "source_reports": {
            "base": BASE_FORMAT,
            "fxo_provenance": fxo_provenance.get("format") if fxo_provenance else None,
            "material_constants": material_constants.get("format") if material_constants else None,
        },
        "policy": {
            **dict(base.get("policy") or {}),
            "later_exact_offline_evidence_updates_frontier": True,
            "ambiguity_is_not_proof": True,
        },
    }
    return result


def _load(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"report is not a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_audit")
    parser.add_argument("output")
    parser.add_argument("--fxo-provenance")
    parser.add_argument("--material-constants")
    args = parser.parse_args(argv)
    base = _load(args.base_audit)
    assert base is not None
    report = build_renderer_frontier_audit(
        base,
        fxo_provenance=_load(args.fxo_provenance),
        material_constants=_load(args.material_constants),
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
