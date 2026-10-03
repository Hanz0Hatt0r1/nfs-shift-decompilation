#!/usr/bin/env python3
"""Run the joined SHIFT class-evidence pipeline in one command.

The pipeline preserves the existing evidence layers as separate JSON artifacts:
RTTI/reflection class manifest, factory-to-initializer links, create-wrapper
value-flow evidence, structural audit, the non-numeric evidence scorecard,
source-level lifecycle observations, deleting-wrapper shapes, paired lifetime
shapes, recurring helper-family evidence, diagnostic-backed memory-pool paths,
memory-wrapper ABI shapes, source wrapper call-site evidence, and one-hop Ghidra
lifecycle slices.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from audit_shift_class_candidates import audit_candidates
from build_class_evidence_scorecard import build_scorecard
from build_class_lifetime_pair_evidence import build_lifetime_pairs
from build_shift_class_manifest import build_manifest
from extract_class_lifecycle_source_evidence import extract_lifecycle_evidence
from extract_create_wrapper_evidence import extract_create_wrappers
from extract_deleting_wrapper_evidence import extract_deleting_wrappers
from extract_factory_initializer_links import extract_links
from extract_memory_wrapper_callsites import extract_memory_wrapper_callsites

FORMAT = "SHIFT-CLASS-EVIDENCE-PIPELINE/1"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_ghidra_module(filename: str, module_name: str):
    path = Path(__file__).resolve().parents[1] / "ghidra" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Ghidra postprocessor: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_lifecycle_targets(scorecard_path: Path, ghidra_export: Path) -> dict[str, Any]:
    module = _load_ghidra_module(
        "build_lifecycle_investigation_targets.py",
        "build_lifecycle_investigation_targets",
    )
    return module.build_targets(scorecard_path, ghidra_export)


def _build_lifetime_helper_families(
    pair_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    module = _load_ghidra_module(
        "build_lifetime_helper_families.py",
        "build_lifetime_helper_families",
    )
    return module.build_helper_families(pair_path, ghidra_export)


def _build_memory_helper_semantics(
    helper_families_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    module = _load_ghidra_module(
        "build_memory_helper_semantics.py",
        "build_memory_helper_semantics",
    )
    return module.build_memory_helper_semantics(helper_families_path, ghidra_export)


def _build_memory_wrapper_family(
    memory_semantics_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    module = _load_ghidra_module(
        "build_memory_wrapper_family.py",
        "build_memory_wrapper_family",
    )
    return module.build_memory_wrapper_family(memory_semantics_path, ghidra_export)


def run_pipeline(
    source: Path,
    exe: Path,
    ghidra_export: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    class_manifest_path = output_dir / "class_manifest.json"
    initializer_links_path = output_dir / "factory_initializer_links.json"
    create_wrapper_path = output_dir / "create_wrapper_evidence.json"
    class_audit_path = output_dir / "class_audit.json"
    scorecard_path = output_dir / "class_evidence_scorecard.json"
    lifecycle_source_path = output_dir / "class_lifecycle_source_evidence.json"
    deleting_wrapper_path = output_dir / "deleting_wrapper_evidence.json"
    lifetime_pair_path = output_dir / "class_lifetime_pair_evidence.json"
    helper_families_path = output_dir / "lifetime_helper_families.json"
    memory_semantics_path = output_dir / "memory_helper_semantics.json"
    memory_wrapper_path = output_dir / "memory_wrapper_family.json"
    memory_wrapper_callsites_path = output_dir / "memory_wrapper_callsites.json"
    lifecycle_targets_path = output_dir / "lifecycle_investigation_targets.json"

    class_manifest = build_manifest(source, exe, ghidra_export)
    _write_json(class_manifest_path, class_manifest)

    initializer_links = extract_links(source, exe, ghidra_export)
    _write_json(initializer_links_path, initializer_links)

    create_wrappers = extract_create_wrappers(
        source,
        initializer_links_path,
        ghidra_export,
    )
    _write_json(create_wrapper_path, create_wrappers)

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

    deleting_wrappers = extract_deleting_wrappers(
        source,
        lifecycle_source_path,
        ghidra_export,
    )
    _write_json(deleting_wrapper_path, deleting_wrappers)

    lifetime_pairs = build_lifetime_pairs(
        create_wrapper_path,
        deleting_wrapper_path,
        lifecycle_source_path,
    )
    _write_json(lifetime_pair_path, lifetime_pairs)

    helper_families = _build_lifetime_helper_families(
        lifetime_pair_path,
        ghidra_export,
    )
    _write_json(helper_families_path, helper_families)

    memory_semantics = _build_memory_helper_semantics(
        helper_families_path,
        ghidra_export,
    )
    _write_json(memory_semantics_path, memory_semantics)

    memory_wrapper_family = _build_memory_wrapper_family(
        memory_semantics_path,
        ghidra_export,
    )
    _write_json(memory_wrapper_path, memory_wrapper_family)

    memory_wrapper_callsites = extract_memory_wrapper_callsites(source, ghidra_export)
    _write_json(memory_wrapper_callsites_path, memory_wrapper_callsites)

    lifecycle_targets = _build_lifecycle_targets(scorecard_path, ghidra_export)
    _write_json(lifecycle_targets_path, lifecycle_targets)

    artifacts = {
        "class_manifest": class_manifest_path.name,
        "factory_initializer_links": initializer_links_path.name,
        "create_wrapper_evidence": create_wrapper_path.name,
        "class_audit": class_audit_path.name,
        "class_evidence_scorecard": scorecard_path.name,
        "class_lifecycle_source_evidence": lifecycle_source_path.name,
        "deleting_wrapper_evidence": deleting_wrapper_path.name,
        "class_lifetime_pair_evidence": lifetime_pair_path.name,
        "lifetime_helper_families": helper_families_path.name,
        "memory_helper_semantics": memory_semantics_path.name,
        "memory_wrapper_family": memory_wrapper_path.name,
        "memory_wrapper_callsites": memory_wrapper_callsites_path.name,
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
            "create_wrapper_links": create_wrappers.get("link_count"),
            "source_create_wrapper_shapes": create_wrappers.get(
                "source_create_wrapper_shape_count"
            ),
            "create_wrapper_shapes": create_wrappers.get(
                "create_wrapper_shape_count"
            ),
            "distinct_preinitializer_helpers": create_wrappers.get(
                "distinct_preinitializer_helper_count"
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
            "deleting_wrapper_candidates": deleting_wrappers.get(
                "wrapper_candidate_count"
            ),
            "deleting_wrapper_shapes": deleting_wrappers.get(
                "deleting_wrapper_shape_count"
            ),
            "deleting_wrapper_ghidra_confirmed_shapes": deleting_wrappers.get(
                "ghidra_confirmed_shape_count"
            ),
            "paired_lifetime_classes": lifetime_pairs.get(
                "paired_lifetime_shape_count"
            ),
            "ghidra_paired_lifetime_classes": lifetime_pairs.get(
                "ghidra_paired_lifetime_shape_count"
            ),
            "unambiguous_lifetime_helper_pairs": lifetime_pairs.get(
                "unambiguous_helper_pair_count"
            ),
            "lifetime_helper_families": helper_families.get("helper_family_count"),
            "recurrent_lifetime_helper_pairs": helper_families.get(
                "recurrent_helper_pair_count"
            ),
            "crosschecked_recurrent_helper_family_candidates": helper_families.get(
                "crosschecked_recurrent_helper_family_candidate_count"
            ),
            "pool_allocation_path_families": memory_semantics.get(
                "allocation_path_family_count"
            ),
            "pool_free_path_families": memory_semantics.get("free_path_family_count"),
            "diagnostic_backed_pool_lifetime_families": memory_semantics.get(
                "diagnostic_backed_pool_lifetime_family_count"
            ),
            "memory_wrapper_members": memory_wrapper_family.get("wrapper_count"),
            "confirmed_memory_wrapper_shapes": memory_wrapper_family.get(
                "confirmed_wrapper_shape_count"
            ),
            "memory_wrapper_family_candidates": int(
                memory_wrapper_family.get("memory_wrapper_family_candidate") is True
            ),
            "memory_wrapper_callsites": memory_wrapper_callsites.get("callsite_count"),
            "memory_wrapper_callers": memory_wrapper_callsites.get("caller_count"),
            "parsed_memory_wrapper_callsites": memory_wrapper_callsites.get(
                "parsed_callsite_count"
            ),
            "unparsed_memory_wrapper_callsites": memory_wrapper_callsites.get(
                "unparsed_callsite_count"
            ),
            "memory_wrapper_ghidra_confirmed_callsites": memory_wrapper_callsites.get(
                "ghidra_confirmed_callsite_count"
            ),
            "memory_wrapper_ghidra_rejected_callsites": memory_wrapper_callsites.get(
                "ghidra_rejected_callsite_count"
            ),
            "lifecycle_target_slices": lifecycle_targets.get("target_count"),
            "lifecycle_complete_slices": lifecycle_targets.get("complete_slice_count"),
            "lifecycle_incomplete_slices": lifecycle_targets.get("incomplete_slice_count"),
        },
        "scorecard_tiers": scorecard.get("tier_counts", {}),
        "next_evidence_blockers": scorecard.get("next_evidence_blocker_counts", {}),
        "scope": {
            "pool_memory_path_diagnostics_used": True,
            "memory_wrapper_physical_storage_used": True,
            "memory_wrapper_source_callsites_used": True,
            "memory_wrapper_callsite_ghidra_edges_crosschecked": True,
            "ghidra_semantic_parameter_types_trusted": False,
            "allocation_helper_semantics_proven": False,
            "shared_allocator_family_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "argument_roles_proven": False,
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "deleting_destructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "behavior_semantics_proven": False,
            "note": (
                "This pipeline composes direct source/Ghidra evidence through bounded "
                "paths to retail pool allocation/free diagnostics, records robust "
                "wrapper calling-convention/storage shapes, and preserves source "
                "wrapper call-site argument expressions. Ghidra semantic auto-types do "
                "not participate in promotion, and argument roles/allocator ABI, "
                "ownership and C++ lifecycle identities remain unproven."
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
            "exit non-zero if registration/factory/wrapper-callsite Ghidra checks "
            "mismatch or a lifecycle-ready target cannot be resolved in the same "
            "Ghidra export"
        ),
    )
    args = parser.parse_args()

    report = run_pipeline(args.source, args.exe, args.ghidra_export, args.out)
    counts = report["counts"]
    print(f"format: {report['format']}")
    print(f"registered classes: {counts['registered_classes']}")
    print(f"structural-ready classes: {counts['structural_ready_classes']}")
    print(f"create-wrapper shapes: {counts['create_wrapper_shapes']}")
    print(f"paired lifetime classes: {counts['paired_lifetime_classes']}")
    print(
        "diagnostic-backed pool lifetime families: "
        f"{counts['diagnostic_backed_pool_lifetime_families']}"
    )
    print(f"confirmed memory wrapper shapes: {counts['confirmed_memory_wrapper_shapes']}")
    print(f"memory wrapper callsites: {counts['memory_wrapper_callsites']}")
    print(f"lifecycle target slices: {counts['lifecycle_target_slices']}")
    print(f"output: {args.out}")

    mismatches = (
        int(counts.get("ghidra_registration_mismatches") or 0)
        + int(counts.get("initializer_ghidra_mismatch_links") or 0)
        + int(counts.get("memory_wrapper_ghidra_rejected_callsites") or 0)
        + int(counts.get("lifecycle_incomplete_slices") or 0)
    )
    if args.fail_on_ghidra_mismatch and mismatches:
        print(f"Ghidra mismatches/incomplete slices: {mismatches}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
