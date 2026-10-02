#!/usr/bin/env python3
"""Build an evidence scorecard for SHIFT class decompilation work.

The scorecard does not assign a numeric confidence score. It keeps independent
static-evidence gates visible and derives workflow tiers for prioritizing the
next reverse-engineering step.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-CLASS-EVIDENCE-SCORECARD/1"
AUDIT_FORMAT = "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1"
CLASS_MANIFEST_FORMAT = "SHIFT-CLASS-MANIFEST/1"


def _load_class_manifest(path: Path | None, audit: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if path is None:
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != CLASS_MANIFEST_FORMAT:
        raise ValueError(f"{path}: expected {CLASS_MANIFEST_FORMAT}")
    for key in ("source_sha256", "exe_sha256"):
        audit_value = audit.get(key)
        manifest_value = report.get(key)
        if audit_value and manifest_value and audit_value != manifest_value:
            raise ValueError(
                f"{path}: {key} does not match audit "
                f"({manifest_value} != {audit_value})"
            )
    out: dict[int, dict[str, Any]] = {}
    for row in report.get("classes") or []:
        descriptor = row.get("descriptor")
        if isinstance(descriptor, int):
            out[descriptor] = row
    return out


def _registration_evidence(
    audit_row: dict[str, Any],
    manifest_index: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    descriptor = audit_row.get("descriptor")
    if not isinstance(descriptor, int):
        return None
    manifest_row = manifest_index.get(descriptor)
    if not manifest_row:
        return None
    evidence = manifest_row.get("ghidra_registration")
    return evidence if isinstance(evidence, dict) else None


def _registration_state(evidence: dict[str, Any] | None) -> bool | None:
    if evidence is None:
        return None
    value = evidence.get("verified")
    return value if isinstance(value, bool) else None


def _initializer_state(row: dict[str, Any]) -> bool | None:
    value = row.get("initializer_ghidra_confirmed")
    return value if isinstance(value, bool) else None


def classify(
    row: dict[str, Any],
    registration: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    structural = bool(row.get("structural_ready"))
    registration_state = _registration_state(registration)
    linked = bool(row.get("initializer_linked"))
    unambiguous = isinstance(row.get("unambiguous_initializer"), str)
    initializer_call = _initializer_state(row)

    blockers: list[str] = []
    if not structural:
        blockers.append("structural_not_ready")
    if registration_state is not True:
        blockers.append(
            "registration_not_checked"
            if registration_state is None
            else "registration_mismatch"
        )
    if not linked:
        blockers.append("no_initializer_link")
    elif not unambiguous:
        blockers.append("ambiguous_initializer")
    if linked and initializer_call is not True:
        blockers.append(
            "initializer_call_not_checked"
            if initializer_call is None
            else "initializer_call_mismatch"
        )

    if (
        structural
        and registration_state is True
        and linked
        and unambiguous
        and initializer_call is True
    ):
        return "lifecycle-investigation-ready", blockers
    if structural and registration_state is True and linked and unambiguous:
        return "initializer-linked", blockers
    if structural and registration_state is True:
        return "registration-crosschecked", blockers
    if structural:
        return "structural-ready", blockers
    return "structural-blocked", blockers


def build_scorecard(
    audit_path: Path,
    class_manifest_path: Path | None = None,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("format") != AUDIT_FORMAT:
        raise ValueError(f"{audit_path}: expected {AUDIT_FORMAT}")
    manifest_index = _load_class_manifest(class_manifest_path, audit)

    rows: list[dict[str, Any]] = []
    for source in audit.get("candidates") or []:
        registration = _registration_evidence(source, manifest_index)
        registration_state = _registration_state(registration)
        tier, next_blockers = classify(source, registration)
        rows.append(
            {
                "class_name": source.get("class_name"),
                "descriptor": source.get("descriptor"),
                "parent_class": source.get("parent_class"),
                "field_count": int(source.get("field_count", 0)),
                "unique_vtable": source.get("unique_vtable"),
                "structural_ready": bool(source.get("structural_ready")),
                "ghidra_registration_verified": registration_state,
                "ghidra_registration_address": (
                    registration.get("address") if registration else None
                ),
                "ghidra_registration_fingerprint": (
                    registration.get("mnemonic_sha256") if registration else None
                ),
                "initializer_linked": bool(source.get("initializer_linked")),
                "unambiguous_initializer": source.get("unambiguous_initializer"),
                "initializer_ghidra_confirmed": _initializer_state(source),
                "evidence_tier": tier,
                "next_evidence_blockers": next_blockers,
            }
        )

    order = {
        "lifecycle-investigation-ready": 0,
        "initializer-linked": 1,
        "registration-crosschecked": 2,
        "structural-ready": 3,
        "structural-blocked": 4,
    }
    rows.sort(
        key=lambda row: (
            order[row["evidence_tier"]],
            -row["field_count"],
            row["class_name"] is None,
            row["class_name"] or "",
            int(row.get("descriptor") or 0),
        )
    )
    tier_counts = Counter(row["evidence_tier"] for row in rows)
    blocker_counts = Counter(
        blocker for row in rows for blocker in row["next_evidence_blockers"]
    )

    return {
        "format": FORMAT,
        "source_audit": str(audit_path),
        "source_class_manifest": (
            str(class_manifest_path) if class_manifest_path is not None else None
        ),
        "source": audit.get("source"),
        "source_sha256": audit.get("source_sha256"),
        "exe": audit.get("exe"),
        "exe_sha256": audit.get("exe_sha256"),
        "class_count": len(rows),
        "registration_joined_count": sum(
            row["ghidra_registration_verified"] is not None for row in rows
        ),
        "registration_verified_count": sum(
            row["ghidra_registration_verified"] is True for row in rows
        ),
        "registration_mismatch_count": sum(
            row["ghidra_registration_verified"] is False for row in rows
        ),
        "tier_counts": dict(sorted(tier_counts.items())),
        "next_evidence_blocker_counts": dict(sorted(blocker_counts.items())),
        "rows": rows,
        "scope": {
            "numeric_confidence_score_used": False,
            "constructor_semantics_proven": False,
            "behavior_semantics_proven": False,
            "note": (
                "lifecycle-investigation-ready means the class has source/PE-backed "
                "structure, an independently verified Ghidra registration, one unique "
                "initializer candidate, and a Ghidra-confirmed factory-to-initializer "
                "edge. It prioritizes the next investigation; it does not rename the "
                "initializer as a constructor or prove runtime behavior."
            ),
        },
    }


def _select(
    report: dict[str, Any],
    tiers: list[str],
    prefixes: list[str],
    top: int | None,
) -> list[dict[str, Any]]:
    rows = report["rows"]
    if tiers:
        wanted = set(tiers)
        rows = [row for row in rows if row["evidence_tier"] in wanted]
    if prefixes:
        rows = [
            row
            for row in rows
            if any((row.get("class_name") or "").startswith(prefix) for prefix in prefixes)
        ]
    if top is not None:
        rows = rows[:top]
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "class_name",
        "descriptor",
        "parent_class",
        "field_count",
        "unique_vtable",
        "structural_ready",
        "ghidra_registration_verified",
        "ghidra_registration_address",
        "ghidra_registration_fingerprint",
        "initializer_linked",
        "unambiguous_initializer",
        "initializer_ghidra_confirmed",
        "evidence_tier",
        "next_evidence_blockers",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            rendered = {key: row.get(key) for key in columns}
            rendered["next_evidence_blockers"] = ";".join(row["next_evidence_blockers"])
            writer.writerow(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "audit",
        type=Path,
        help="SHIFT-CLASS-DECOMPILATION-CANDIDATES/1 JSON",
    )
    parser.add_argument(
        "--class-manifest",
        type=Path,
        help=(
            "optional SHIFT-CLASS-MANIFEST/1 generated with --ghidra-export; "
            "registration evidence is joined by class descriptor"
        ),
    )
    parser.add_argument("--tier", action="append", default=[])
    parser.add_argument("--prefix", action="append", default=[])
    parser.add_argument("--top", type=int)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    if args.top is not None and args.top < 1:
        parser.error("--top must be >= 1")

    report = build_scorecard(args.audit, args.class_manifest)
    selected = _select(report, args.tier, args.prefix, args.top)
    rendered = dict(report)
    rendered["selected_count"] = len(selected)
    rendered["rows"] = selected
    payload = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.csv_out:
        _write_csv(args.csv_out, selected)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
