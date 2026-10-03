#!/usr/bin/env python3
"""Build the direct-observation Ghidra semantic index in one command.

This orchestration preserves every evidence layer as a separate artifact.  It
never consumes heuristic vtable/constructor/factory candidate sets for semantic
promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_shift_export import analyze as analyze_shift_export
from build_physics_allocator_boundary import build_physics_allocator_boundary
from build_subsystem_manifests import build as build_subsystem_manifests
from build_subsystem_manifests import write_bundle as write_subsystem_bundle
from discover_method_name_anchors import discover_method_name_anchors
from join_method_anchors_to_subsystems import join_method_anchors_to_subsystems

FORMAT = "SHIFT.GhidraStaticSemanticIndex/1"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _anchor_failure_count(report: dict[str, Any]) -> int:
    failures = 0
    for row in report.get("anchors") or []:
        checks = row.get("checks") or {}
        if checks.get("function_present") is not True:
            failures += 1
        failures += sum(value is not True for value in (checks.get("expected_strings") or {}).values())
        failures += sum(value is not True for value in (checks.get("expected_calls") or {}).values())
    return failures


def _subsystem_counts(report: dict[str, Any]) -> dict[str, int]:
    alias_rows = []
    registration_rows = []
    for manifest in (report.get("subsystems") or {}).values():
        alias_rows.extend(manifest.get("semantic_aliases") or [])
        registration_rows.extend(manifest.get("class_registrations") or [])
    return {
        "semantic_alias_candidates": len(alias_rows),
        "semantic_aliases_promoted": sum(row.get("promoted") is True for row in alias_rows),
        "semantic_alias_mismatches": sum(row.get("promoted") is not True for row in alias_rows),
        "class_registration_candidates": len(registration_rows),
        "class_registrations_promoted": sum(row.get("promoted") is True for row in registration_rows),
        "class_registration_mismatches": sum(row.get("promoted") is not True for row in registration_rows),
    }


def _validate_source_identity(*reports: dict[str, Any]) -> dict[str, Any]:
    sources = [report.get("source") for report in reports if isinstance(report.get("source"), dict)]
    programs = {source.get("program") for source in sources if source.get("program") is not None}
    md5s = {source.get("executable_md5") for source in sources if source.get("executable_md5") is not None}
    if len(programs) > 1:
        raise ValueError("semantic layers disagree on program identity: " + ", ".join(sorted(map(str, programs))))
    if len(md5s) > 1:
        raise ValueError("semantic layers disagree on executable MD5: " + ", ".join(sorted(map(str, md5s))))
    return sources[0] if sources else {}


def build_static_semantic_index(root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    crosscheck = analyze_shift_export(root)
    subsystem_report = build_subsystem_manifests(root)
    method_anchors = discover_method_name_anchors(root)
    subsystem_method_anchors = join_method_anchors_to_subsystems(root)
    physics_allocator = build_physics_allocator_boundary(root)

    source = _validate_source_identity(crosscheck, subsystem_report, subsystem_method_anchors)

    crosscheck_path = output_dir / "crosscheck.json"
    subsystem_dir = output_dir / "subsystems"
    method_anchor_path = output_dir / "method_name_anchors.json"
    subsystem_method_anchor_path = output_dir / "subsystem_method_anchors.json"
    physics_allocator_path = output_dir / "physics_allocator_boundary.json"

    _write_json(crosscheck_path, crosscheck)
    write_subsystem_bundle(subsystem_report, subsystem_dir)
    _write_json(method_anchor_path, method_anchors)
    _write_json(subsystem_method_anchor_path, subsystem_method_anchors)
    _write_json(physics_allocator_path, physics_allocator)

    subsystem_counts = _subsystem_counts(subsystem_report)
    anchor_failures = _anchor_failure_count(crosscheck)
    registry = crosscheck.get("rtti_registration_fingerprint") or {}
    allocator_members = int(physics_allocator.get("member_count") or 0)
    allocator_confirmed = int(physics_allocator.get("confirmed_member_count") or 0)
    allocator_mismatches = max(0, allocator_members - allocator_confirmed)

    counts = {
        "crosscheck_anchor_count": len(crosscheck.get("anchors") or []),
        "crosscheck_anchor_failure_count": anchor_failures,
        "registry_fingerprint_matches": int(registry.get("matching_function_count") or 0),
        "registry_callshape_matches": int(registry.get("registration_shape_match_count") or 0),
        **subsystem_counts,
        "method_string_anchors": int(method_anchors.get("method_string_anchor_count") or 0),
        "unique_method_name_candidates": int(method_anchors.get("unique_method_name_candidate_count") or 0),
        "ambiguous_method_anchor_functions": int(method_anchors.get("ambiguous_method_anchor_function_count") or 0),
        "subsystem_crosschecked_method_name_candidates": int(
            subsystem_method_anchors.get("promoted_method_name_candidate_count") or 0
        ),
        "namespace_only_method_name_candidates": int(
            subsystem_method_anchors.get("namespace_only_candidate_count") or 0
        ),
        "slice_only_unclassified_method_name_candidates": int(
            subsystem_method_anchors.get("slice_only_unclassified_candidate_count") or 0
        ),
        "physics_allocator_members": allocator_members,
        "physics_allocator_members_confirmed": allocator_confirmed,
        "physics_allocator_member_mismatches": allocator_mismatches,
        "physics_allocator_boundary_confirmed": int(
            physics_allocator.get("physics_allocator_boundary_confirmed") is True
        ),
    }

    direct_mismatch_count = (
        counts["crosscheck_anchor_failure_count"]
        + counts["semantic_alias_mismatches"]
        + counts["class_registration_mismatches"]
        + counts["physics_allocator_member_mismatches"]
    )
    counts["direct_evidence_mismatch_count"] = direct_mismatch_count

    report = {
        "format": FORMAT,
        "ghidra_export": str(root),
        "output_dir": str(output_dir),
        "source": source,
        "artifacts": {
            "crosscheck": crosscheck_path.name,
            "subsystem_directory": subsystem_dir.name,
            "subsystem_index": str(Path(subsystem_dir.name) / "index.json"),
            "method_name_anchors": method_anchor_path.name,
            "subsystem_method_anchors": subsystem_method_anchor_path.name,
            "physics_allocator_boundary": physics_allocator_path.name,
        },
        "counts": counts,
        "scope": {
            "functions_used": True,
            "callgraph_used": True,
            "string_xrefs_used": True,
            "physics_allocator_boundary_used": True,
            "heuristic_vtables_used": False,
            "heuristic_constructors_used": False,
            "heuristic_factories_used": False,
            "automatic_function_renaming_performed": False,
            "method_behavior_proven": False,
            "abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "This index orchestrates direct-observation static semantic layers from one "
                "Ghidra export. Individual artifacts retain their own evidence boundaries; "
                "namespace-only and ambiguous method anchors are not semantic promotions. "
                "The PhysicsAllocator boundary preserves physical entry storage but does not "
                "assign the explicit stack argument or return/ownership ABI."
            ),
        },
    }
    _write_json(output_dir / "manifest.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero when a direct anchor/alias/registration/boundary check fails",
    )
    args = parser.parse_args()

    report = build_static_semantic_index(args.ghidra_export, args.output_dir)
    counts = report["counts"]
    print(f"format: {report['format']}")
    print(f"program: {report['source'].get('program')}")
    print(f"semantic aliases promoted: {counts['semantic_aliases_promoted']}")
    print(f"class registrations promoted: {counts['class_registrations_promoted']}")
    print(f"unique method-name candidates: {counts['unique_method_name_candidates']}")
    print(
        "subsystem-crosschecked method-name candidates: "
        f"{counts['subsystem_crosschecked_method_name_candidates']}"
    )
    print(
        "physics allocator members confirmed: "
        f"{counts['physics_allocator_members_confirmed']}/{counts['physics_allocator_members']}"
    )
    print(f"direct evidence mismatches: {counts['direct_evidence_mismatch_count']}")
    print(f"output: {args.output_dir}")
    if args.fail_on_mismatch and counts["direct_evidence_mismatch_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
