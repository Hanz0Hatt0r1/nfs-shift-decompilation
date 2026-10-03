#!/usr/bin/env python3
"""Summarize proven source-level semantic roles for retail memory wrappers.

This report consumes the independently proven allocation-size and
released-pointer joins. It aggregates those roles per wrapper and verifies that
source argument indices remain consistent across all proven callsites. Release
byte behavior is recorded separately and is never promoted to a flag role here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"
STATIC_FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
ALLOCATION_FORMAT = "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1"
RELEASED_FORMAT = "SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _proven_rows(report: dict[str, Any], flag: str) -> list[dict[str, Any]]:
    return [
        row
        for row in (report.get("rows") or [])
        if isinstance(row, dict) and row.get(flag) is True
    ]


def _role_by_wrapper(
    rows: list[dict[str, Any]],
    *,
    index_key: str,
    expression_key: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        wrapper = row.get("wrapper")
        if isinstance(wrapper, str) and wrapper:
            grouped.setdefault(wrapper, []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for wrapper, wrapper_rows in sorted(grouped.items()):
        indices = sorted(
            {
                int(row[index_key])
                for row in wrapper_rows
                if isinstance(row.get(index_key), int)
            }
        )
        expressions = sorted(
            {
                str(row[expression_key])
                for row in wrapper_rows
                if row.get(expression_key) is not None
            }
        )
        callers = sorted(
            {
                str(row.get("caller"))
                for row in wrapper_rows
                if row.get("caller") is not None
            }
        )
        result[wrapper] = {
            "proven_callsite_count": len(wrapper_rows),
            "source_argument_indices": indices,
            "source_argument_index_consistent": len(indices) == 1,
            "source_argument_index": indices[0] if len(indices) == 1 else None,
            "observed_source_expressions": expressions,
            "caller_count": len(callers),
            "callers": callers,
        }
    return result


def summarize_memory_source_semantics(
    static_summary_path: Path,
    allocation_role_path: Path,
    released_pointer_role_path: Path,
) -> dict[str, Any]:
    static_summary = _load(static_summary_path, STATIC_FORMAT)
    allocation = _load(allocation_role_path, ALLOCATION_FORMAT)
    released = _load(released_pointer_role_path, RELEASED_FORMAT)

    allocation_rows = _proven_rows(allocation, "allocation_size_role_proven")
    released_rows = _proven_rows(released, "released_pointer_role_proven")

    allocation_by_wrapper = _role_by_wrapper(
        allocation_rows,
        index_key="allocation_size_source_argument_index",
        expression_key="allocation_size_source_argument_expression",
    )
    released_by_wrapper = _role_by_wrapper(
        released_rows,
        index_key="released_pointer_source_argument_index",
        expression_key="released_pointer_source_argument_expression",
    )

    wrappers = sorted(set(allocation_by_wrapper) | set(released_by_wrapper))
    profiles: list[dict[str, Any]] = []
    blockers: list[str] = []
    for wrapper in wrappers:
        allocation_role = allocation_by_wrapper.get(wrapper)
        released_role = released_by_wrapper.get(wrapper)
        role_blockers: list[str] = []
        if allocation_role and not allocation_role["source_argument_index_consistent"]:
            role_blockers.append("allocation_size_source_index_conflict")
        if released_role and not released_role["source_argument_index_consistent"]:
            role_blockers.append("released_pointer_source_index_conflict")
        if role_blockers:
            blockers.extend(f"{wrapper}:{item}" for item in role_blockers)
        profiles.append(
            {
                "wrapper": wrapper,
                "allocation_size": allocation_role,
                "released_pointer": released_role,
                "proven_source_roles": [
                    role
                    for role, value in (
                        ("allocation-size", allocation_role),
                        ("released-pointer", released_role),
                    )
                    if value is not None and value["source_argument_index_consistent"]
                ],
                "unresolved_source_roles": [
                    "pool-selector",
                    "alignment",
                    "release-flag",
                    "delete-kind",
                    "ownership",
                ],
                "blockers": role_blockers,
            }
        )

    allocation_scope = allocation.get("scope") or {}
    released_scope = released.get("scope") or {}
    static_scope = static_summary.get("scope") or {}
    release_byte = static_summary.get("release_byte_behavior") or {}

    allocation_proven = bool(
        allocation_scope.get("allocation_size_role_proven") is True and allocation_rows
    )
    released_proven = bool(
        released_scope.get("released_pointer_role_proven") is True and released_rows
    )
    semantic_profiles_consistent = not blockers

    return {
        "format": FORMAT,
        "inputs": {
            "static_summary": str(static_summary_path),
            "allocation_size_role_join": str(allocation_role_path),
            "released_pointer_role_join": str(released_pointer_role_path),
        },
        "allocation_size_role_proven": allocation_proven,
        "allocation_size_proven_callsite_count": len(allocation_rows),
        "released_pointer_role_proven": released_proven,
        "released_pointer_proven_callsite_count": len(released_rows),
        "wrapper_profile_count": len(profiles),
        "wrapper_profiles": profiles,
        "semantic_profiles_consistent": semantic_profiles_consistent,
        "release_byte_behavior": {
            "analysis_complete": release_byte.get("analysis_complete") is True,
            "thunk_forwarded_to_release_backend": (
                release_byte.get("thunk_forwarded_to_release_backend") is True
            ),
            "release_backend_observed": release_byte.get("release_backend_observed") is True,
            "controls_conditional_branch": (
                release_byte.get("controls_conditional_branch") is True
            ),
            "bitwise_transformed": release_byte.get("bitwise_transformed") is True,
            "semantic_role_assigned": False,
        },
        "blockers": blockers,
        "scope": {
            "static_retail_chain_required": (
                static_summary.get("static_evidence_chain_complete") is True
            ),
            "source_allocation_size_role_proven": allocation_proven,
            "source_released_pointer_role_proven": released_proven,
            "source_role_indices_consistent": semantic_profiles_consistent,
            "release_byte_behavior_observed": (
                static_scope.get("release_byte_behavior_observed") is True
            ),
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "Only roles already proven by diagnostic-backed instruction tracing and "
                "source-to-storage joins are aggregated. Stable source argument indices do "
                "not imply semantics for any unresolved parameter."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-summary", type=Path, required=True)
    parser.add_argument("--allocation-size-role", type=Path, required=True)
    parser.add_argument("--released-pointer-role", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = summarize_memory_source_semantics(
        args.static_summary,
        args.allocation_size_role,
        args.released_pointer_role,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"allocation-size callsites: {report['allocation_size_proven_callsite_count']}")
    print(f"released-pointer callsites: {report['released_pointer_proven_callsite_count']}")
    print(f"wrapper profiles: {report['wrapper_profile_count']}")
    print(f"profiles consistent: {report['semantic_profiles_consistent']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
