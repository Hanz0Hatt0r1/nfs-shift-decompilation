#!/usr/bin/env python3
"""Audit a track_path_analysis.json against the current analyzer evidence schema."""
from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path

FORMAT = "SHIFT-TRACK-PATH-ANALYSIS-PROVENANCE-AUDIT/1"


def _normalize_vtable(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def _vtable_differences(observed: dict, current: dict) -> list[dict]:
    rows = []
    for class_name in sorted(set(observed) | set(current)):
        observed_value = _normalize_vtable(observed.get(class_name))
        current_value = _normalize_vtable(current.get(class_name))
        if observed_value == current_value:
            continue
        rows.append({
            "class": class_name,
            "observed": (
                f"0x{observed_value:08x}" if observed_value is not None else None
            ),
            "current": (
                f"0x{current_value:08x}" if current_value is not None else None
            ),
            "kind": (
                "missing-in-analysis"
                if class_name not in observed
                else "removed-from-current"
                if class_name not in current
                else "changed"
            ),
        })
    return rows


def audit(analysis_path: Path, analyzer_path: Path) -> dict:
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    namespace = runpy.run_path(str(analyzer_path))
    manifest_fn = namespace.get("analyzer_evidence_manifest")
    fingerprint_fn = namespace.get("analyzer_evidence_fingerprint")
    if not callable(manifest_fn) or not callable(fingerprint_fn):
        raise ValueError(
            f"{analyzer_path}: analyzer evidence manifest/fingerprint helpers not found"
        )

    current_manifest = manifest_fn()
    current_fingerprint = fingerprint_fn(current_manifest)
    evidence = analysis.get("analyzer_evidence")
    observed_fingerprint = None
    observed_manifest = None
    if isinstance(evidence, dict):
        observed_fingerprint = evidence.get("fingerprint")
        observed_manifest = evidence.get("manifest")

    current_vtables = current_manifest.get("known_vtables", {})
    if isinstance(observed_manifest, dict):
        observed_vtables = observed_manifest.get("known_vtables", {})
    else:
        observed_vtables = analysis.get("known_vtables", {})
    if not isinstance(observed_vtables, dict):
        observed_vtables = {}

    vtable_differences = _vtable_differences(observed_vtables, current_vtables)

    changed_sections: list[str] = []
    if isinstance(observed_manifest, dict):
        for section in (
            "format",
            "analysis_format",
            "known_vtables",
            "layouts",
            "array_contracts",
            "identity_policies",
            "relations",
        ):
            if observed_manifest.get(section) != current_manifest.get(section):
                changed_sections.append(section)

    if observed_fingerprint == current_fingerprint:
        status = "current"
        ready = True
    elif observed_fingerprint is not None:
        status = "stale"
        ready = False
    elif any(row["kind"] == "changed" for row in vtable_differences):
        status = "legacy-stale"
        ready = False
    else:
        status = "legacy-unversioned"
        ready = False

    return {
        "format": FORMAT,
        "analysis": str(analysis_path),
        "analysis_format": analysis.get("format"),
        "analyzer": str(analyzer_path),
        "status": status,
        "ready": ready,
        "observed_fingerprint": observed_fingerprint,
        "current_fingerprint": current_fingerprint,
        "changed_manifest_sections": changed_sections,
        "vtable_differences": vtable_differences,
        "notes": [
            (
                "A matching fingerprint proves that the output was produced with "
                "the same vtable/layout/array/identity evidence schema."
            ),
            (
                "Legacy outputs without a fingerprint cannot prove layout parity; "
                "overlapping vtable changes are reported explicitly."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path, help="track_path_analysis.json")
    parser.add_argument(
        "--analyzer",
        type=Path,
        default=Path(__file__).with_name("analyze_track_paths.py"),
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = audit(args.analysis, args.analyzer)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
