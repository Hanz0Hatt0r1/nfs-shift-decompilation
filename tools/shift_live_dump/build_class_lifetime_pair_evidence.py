#!/usr/bin/env python3
"""Join create-side and release-side class lifetime evidence conservatively.

The builder only pairs rows already promoted by the underlying source-shape
extractors.  It does not infer constructor/destructor semantics.  A class gets
`paired_lifetime_shape=true` when at least one cross-checked create-wrapper shape
and at least one deleting-wrapper shape exist for the same recovered class
descriptor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"
CREATE_FORMAT = "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1"
DELETE_FORMAT = "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1"
LIFECYCLE_FORMAT = "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"


def _load(path: Path, expected: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return report


def _identity(
    create: dict[str, Any],
    deleting: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    create_source = create.get("source")
    delete_source = deleting.get("source")
    lifecycle_source = lifecycle.get("source")
    source_paths = [
        value for value in (create_source, delete_source, lifecycle_source)
        if isinstance(value, str) and value
    ]
    path_match = len(set(source_paths)) <= 1

    known_hashes = [
        value
        for value in (
            create.get("source_sha256"),
            deleting.get("source_sha256"),
            lifecycle.get("source_sha256"),
        )
        if isinstance(value, str) and value
    ]
    known_hash_match = len(set(known_hashes)) <= 1

    resolved_path = Path(source_paths[0]) if source_paths and path_match else None
    actual_hash = None
    actual_hash_matches = None
    if resolved_path is not None and resolved_path.is_file():
        actual_hash = hashlib.sha256(resolved_path.read_bytes()).hexdigest()
        actual_hash_matches = all(actual_hash == value for value in known_hashes)

    if not path_match:
        raise ValueError(f"source path mismatch across lifetime evidence: {source_paths}")
    if not known_hash_match:
        raise ValueError(f"source SHA-256 mismatch across lifetime evidence: {known_hashes}")
    if actual_hash_matches is False:
        raise ValueError(
            "current source bytes do not match lifetime evidence SHA-256: "
            f"actual={actual_hash}, evidence={known_hashes}"
        )

    return {
        "source": source_paths[0] if source_paths else None,
        "source_sha256": known_hashes[0] if known_hashes else actual_hash,
        "source_path_match": path_match,
        "known_hash_match": known_hash_match,
        "current_source_checked": actual_hash is not None,
        "current_source_sha256": actual_hash,
        "current_source_matches": actual_hash_matches,
    }


def _descriptor(row: dict[str, Any]) -> int | None:
    value = row.get("descriptor")
    return value if isinstance(value, int) else None


def _unique(values: list[Any]) -> Any | None:
    present = {value for value in values if value is not None}
    return next(iter(present)) if len(present) == 1 else None


def _strong_create(row: dict[str, Any]) -> bool:
    return row.get("create_wrapper_shape") is True


def _strong_delete(row: dict[str, Any]) -> bool:
    return row.get("deleting_wrapper_shape") is True


def _create_ghidra_confirmed(row: dict[str, Any]) -> bool:
    return (
        row.get("create_wrapper_shape") is True
        and row.get("ghidra_factory_to_helper") is True
        and row.get("ghidra_factory_to_initializer") is True
    )


def _delete_ghidra_confirmed(row: dict[str, Any]) -> bool:
    return (
        row.get("deleting_wrapper_shape") is True
        and row.get("ghidra_teardown_edge") is True
        and row.get("ghidra_release_edge") is True
    )


def build_lifetime_pairs(
    create_path: Path,
    deleting_path: Path,
    lifecycle_path: Path,
) -> dict[str, Any]:
    create = _load(create_path, CREATE_FORMAT)
    deleting = _load(deleting_path, DELETE_FORMAT)
    lifecycle = _load(lifecycle_path, LIFECYCLE_FORMAT)
    identity = _identity(create, deleting, lifecycle)

    create_by_descriptor: dict[int, list[dict[str, Any]]] = defaultdict(list)
    delete_by_descriptor: dict[int, list[dict[str, Any]]] = defaultdict(list)
    lifecycle_by_descriptor: dict[int, dict[str, Any]] = {}

    for row in create.get("links") or []:
        descriptor = _descriptor(row)
        if descriptor is not None and _strong_create(row):
            create_by_descriptor[descriptor].append(row)
    for row in deleting.get("wrappers") or []:
        descriptor = _descriptor(row)
        if descriptor is not None and _strong_delete(row):
            delete_by_descriptor[descriptor].append(row)
    for row in lifecycle.get("targets") or []:
        descriptor = _descriptor(row)
        if descriptor is not None:
            lifecycle_by_descriptor[descriptor] = row

    descriptors = sorted(set(create_by_descriptor) | set(delete_by_descriptor))
    rows: list[dict[str, Any]] = []
    for descriptor in descriptors:
        creates = create_by_descriptor.get(descriptor, [])
        deletes = delete_by_descriptor.get(descriptor, [])
        lifecycle_row = lifecycle_by_descriptor.get(descriptor, {})
        class_names = [
            row.get("class_name") for row in creates + deletes
            if isinstance(row.get("class_name"), str)
        ]
        if isinstance(lifecycle_row.get("class_name"), str):
            class_names.append(lifecycle_row["class_name"])
        class_name = _unique(class_names)

        create_helpers = sorted({
            row["immediate_preinitializer_helper"]
            for row in creates
            if isinstance(row.get("immediate_preinitializer_helper"), str)
        })
        release_helpers = sorted({
            row["release_helper"]
            for row in deletes
            if isinstance(row.get("release_helper"), str)
        })
        factories = sorted({
            row["factory_function"]
            for row in creates
            if isinstance(row.get("factory_function"), str)
        })
        initializers = sorted({
            row["initializer_candidate"]
            for row in creates
            if isinstance(row.get("initializer_candidate"), str)
        })
        deleting_wrappers = sorted({
            row["wrapper_function"]
            for row in deletes
            if isinstance(row.get("wrapper_function"), str)
        })
        teardowns = sorted({
            row["teardown_transition_function"]
            for row in deletes
            if isinstance(row.get("teardown_transition_function"), str)
        })
        helper_literal_argument_sets = sorted({
            tuple(row.get("helper_literal_arguments") or []) for row in creates
        })

        paired = bool(creates and deletes)
        ghidra_paired = bool(
            paired
            and any(_create_ghidra_confirmed(row) for row in creates)
            and any(_delete_ghidra_confirmed(row) for row in deletes)
        )

        blockers = []
        if not creates:
            blockers.append("no_create_wrapper_shape")
        if not deletes:
            blockers.append("no_deleting_wrapper_shape")
        if paired and not any(_create_ghidra_confirmed(row) for row in creates):
            blockers.append("create_shape_not_ghidra_confirmed")
        if paired and not any(_delete_ghidra_confirmed(row) for row in deletes):
            blockers.append("delete_shape_not_ghidra_confirmed")

        rows.append(
            {
                "class_name": class_name,
                "descriptor": descriptor,
                "paired_lifetime_shape": paired,
                "ghidra_paired_lifetime_shape": ghidra_paired,
                "create_shape_count": len(creates),
                "delete_shape_count": len(deletes),
                "factory_functions": factories,
                "initializer_candidates": initializers,
                "preinitializer_helpers": create_helpers,
                "unambiguous_preinitializer_helper": _unique(create_helpers),
                "helper_literal_argument_sets": [
                    list(values) for values in helper_literal_argument_sets
                ],
                "deleting_wrapper_functions": deleting_wrappers,
                "teardown_transition_functions": teardowns,
                "release_helpers": release_helpers,
                "unambiguous_release_helper": _unique(release_helpers),
                "nearest_ancestor_with_unique_vtable": lifecycle_row.get(
                    "nearest_ancestor_with_unique_vtable"
                ),
                "own_vtable": lifecycle_row.get("own_vtable"),
                "ancestor_vtable": lifecycle_row.get("ancestor_vtable"),
                "lifetime_evidence_blockers": blockers,
                "create_shapes": creates,
                "delete_shapes": deletes,
            }
        )

    rows.sort(
        key=lambda row: (
            row["ghidra_paired_lifetime_shape"] is not True,
            row["paired_lifetime_shape"] is not True,
            row.get("class_name") is None,
            row.get("class_name") or "",
            row["descriptor"],
        )
    )

    return {
        "format": FORMAT,
        "create_evidence": str(create_path),
        "deleting_evidence": str(deleting_path),
        "lifecycle_evidence": str(lifecycle_path),
        "identity": identity,
        "class_count": len(rows),
        "paired_lifetime_shape_count": sum(
            row["paired_lifetime_shape"] is True for row in rows
        ),
        "ghidra_paired_lifetime_shape_count": sum(
            row["ghidra_paired_lifetime_shape"] is True for row in rows
        ),
        "unambiguous_helper_pair_count": sum(
            row["paired_lifetime_shape"] is True
            and row["unambiguous_preinitializer_helper"] is not None
            and row["unambiguous_release_helper"] is not None
            for row in rows
        ),
        "classes": rows,
        "scope": {
            "allocator_semantics_proven": False,
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "object_size_semantics_proven": False,
            "note": (
                "A paired lifetime shape joins already-proven create-side value flow "
                "with an already-proven deleting-wrapper source shape for the same "
                "class descriptor. It is a prioritization/lifetime-boundary artifact, "
                "not a compiler-ABI semantic rename."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", type=Path, required=True)
    parser.add_argument("--deleting", type=Path, required=True)
    parser.add_argument("--lifecycle", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_lifetime_pairs(args.create, args.deleting, args.lifecycle)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"classes: {report['class_count']}")
    print(f"paired lifetime shapes: {report['paired_lifetime_shape_count']}")
    print(
        "Ghidra-paired lifetime shapes: "
        f"{report['ghidra_paired_lifetime_shape_count']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
