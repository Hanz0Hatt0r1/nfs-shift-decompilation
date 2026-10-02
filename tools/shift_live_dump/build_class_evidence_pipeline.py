#!/usr/bin/env python3
"""Run the joined SHIFT class-evidence pipeline in one command.

The pipeline preserves the existing evidence layers as separate JSON artifacts:
RTTI/reflection class manifest, factory-to-initializer links, structural audit,
the non-numeric evidence scorecard, source-level lifecycle observations, and
one-hop Ghidra lifecycle investigation slices.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from audit_shift_class_candidates import audit_candidates
from build_class_evidence_scorecard import build_scorecard
from build_shift_class_manifest import build_manifest
from extract_class_lifecycle_source_evidence import extract_lifecycle_evidence
from extract_factory_initializer_links import extract_links

FORMAT = "SHIFT-CLASS-EVIDENCE-PIPELINE/1"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_lifecycle_targets(scorecard_path: Path, ghidra_export: Path) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "ghidra" / "build_lifecycle_investigation_targets.py"
    spec = importlib.util.spec_from_file_location("build_lifecycle_investigation_targets", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load lifecycle target builder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_targets(scorecard_path, ghidra_export)


def run_pipeline(
    source: Path,
    exe: Path,
    ghidra_export: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    class_manifest_path = output_dir / "class_manifest.json"
    initializer_links_path = output_dir / "factory_initializer_links.json"
    class_audit_path = output_dir / "class_audit.json"
    scorecard_path = output_dir / "class_evidence_scorecard.json"
    lifecycle_source_path = output_dir / "class_lifecycle_source_evidence.json"
    lifecycle_targets_path = output_dir / "lifecycle_investigation_targets.json"

    class_manifest = build_manifest(source, exe, ghidra_export)
    _write_json(class_manifest_path, class_manifest)

    initializer_links = extract_links(source, exe, ghidra_export)
    _write_json(initializer_links_path, initializer_links)

    class_audit = audit_candidates(source, exe, initializer_links_path)
    _write_json(class_audit_path, class_audit)

    scorecard = build_scorecard(class_audit_path, class_manifest_path)
    _write_json(scorecard_path, scorecard)

    lifecycle_source = extract_lifecycle_evidence(
        source,
        class_manifest_path,
        scorecard_path,
        ghidra_export,
    )
    _write_json(lifecycle_source_path, lifecycle_source)

    lifecycle_targets = _build_lifecycle_targets(scorecard_path, ghidra_export)
    _write_json(lifecycle_targets_path, lifecycle_targets)

    artifacts = {
        "class_manifest": class_manifest_path.name,
        "factory_initializer_links": initializer_links_path.name,
        "class_audit": class_audit_path.name,
        "class_evidence_scorecard": scorecard_path.name,
        "class_lifecycle_source_evidence": lifecycle_source_path.name,
        "lifecycle_investigation_targets": lifecycle_targets_path.name,
    }
    report = {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": class_manifest.get("source_sha256"),
        "exe": str(exe),
        "exe_sha256": class_manifest.get("exe_sha256"),
        "ghidra_export": str(ghidra_export),
        "output_dir": str(output_dir),
        "artifacts": artifacts,
        "counts": {
            "registered_classes": class_manifest.get("class_count"),
            "reflected_classes": class_manifest.get("reflected_class_count"),
            "unique_vtable_classes": class_manifest.get("unique_vtable_count"),
            "ghidra_registration_checked": class_manifest.get(
                "ghidra_registration_checked_count"
            ),
            "ghidra_registration_verified": class_manifest.get(
                "ghidra_registration_verified_count"
            ),
            "ghidra_registration_mismatches": class_manifest.get(
                "ghidra_registration_mismatch_count"
            ),
            "factory_initializer_links": initializer_links.get("link_count"),
            "initializer_linked_classes": initializer_links.get("linked_class_count"),
            "initializer_ghidra_confirmed_links": initializer_links.get(
                "ghidra_confirmed_link_count"
            ),
            "initializer_ghidra_mismatch_links": initializer_links.get(
                "ghidra_mismatch_link_count"
            ),
            "structural_ready_classes": class_audit.get("structural_ready_count"),
            "lifecycle_investigation_ready_classes": (
                scorecard.get("tier_counts", {}).get("lifecycle-investigation-ready", 0)
            ),
            "lifecycle_source_targets": lifecycle_source.get("target_count"),
            "lifecycle_source_complete_targets": lifecycle_source.get(
                "complete_target_count"
            ),
            "lifecycle_source_base_initializer_links": lifecycle_source.get(
                "base_initializer_link_count"
            ),
            "lifecycle_source_teardown_candidates": lifecycle_source.get(
                "teardown_transition_candidate_count"
            ),
            "lifecycle_target_slices": lifecycle_targets.get("target_count"),
            "lifecycle_complete_slices": lifecycle_targets.get("complete_slice_count"),
            "lifecycle_incomplete_slices": lifecycle_targets.get("incomplete_slice_count"),
        },
        "scorecard_tiers": scorecard.get("tier_counts", {}),
        "next_evidence_blockers": scorecard.get("next_evidence_blocker_counts", {}),
        "scope": {
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "behavior_semantics_proven": False,
            "note": (
                "This pipeline composes existing evidence artifacts, direct source "
                "lifecycle observations and Ghidra context slices. It does not promote "
                "initializer/teardown candidates to constructors/destructors or infer "
                "missing class behavior."
            ),
        },
    }
    _write_json(output_dir / "pipeline_manifest.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, required=True, help="retail SHIFT.exe")
    parser.add_argument(
        "--ghidra-export",
        type=Path,
        required=True,
        help="SHIFT.GhidraEvidenceDatabase/1 directory",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--fail-on-ghidra-mismatch",
        action="store_true",
        help=(
            "exit non-zero if registration/factory Ghidra checks mismatch or a "
            "lifecycle-ready target cannot be resolved in the same Ghidra export"
        ),
    )
    args = parser.parse_args()

    report = run_pipeline(args.source, args.exe, args.ghidra_export, args.out)
    counts = report["counts"]
    print(f"format: {report['format']}")
    print(f"registered classes: {counts['registered_classes']}")
    print(f"structural-ready classes: {counts['structural_ready_classes']}")
    print(
        "lifecycle-investigation-ready classes: "
        f"{counts['lifecycle_investigation_ready_classes']}"
    )
    print(f"lifecycle source targets: {counts['lifecycle_source_targets']}")
    print(f"lifecycle target slices: {counts['lifecycle_target_slices']}")
    print(f"output: {args.out}")

    mismatches = (
        int(counts.get("ghidra_registration_mismatches") or 0)
        + int(counts.get("initializer_ghidra_mismatch_links") or 0)
        + int(counts.get("lifecycle_incomplete_slices") or 0)
    )
    if args.fail_on_ghidra_mismatch and mismatches:
        print(f"Ghidra mismatches/incomplete slices: {mismatches}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
