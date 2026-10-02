#!/usr/bin/env python3
"""Extract conservative deleting-wrapper shapes from class lifecycle evidence.

A wrapper candidate must directly call an already-discovered teardown-transition
candidate and a configured release helper.  A stronger deleting-wrapper shape
also requires the teardown call to precede the release call and a source-level
bit-0 guard in the wrapper body.  Even that stronger shape is reported as
evidence, not automatically renamed as a C++ deleting destructor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from extract_class_lifecycle_source_evidence import (
    _DIRECT_CALL,
    _edge_confirmed,
    _extract_functions,
    _load_ghidra_edges,
)

FORMAT = "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1"
LIFECYCLE_FORMAT = "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"
DEFAULT_RELEASE_HELPERS = ("FUN_00886930",)

# Retail decompiler output commonly renders scalar-delete flags as
# `(param_N & 1) != 0`.  Keep the detector deliberately narrow: it is better to
# leave a wrapper unclassified than infer a delete flag from an arbitrary test.
_BIT0_GUARD = re.compile(
    r"(?:\bparam_[0-9]+\b|\bdelete_flag\b|\bflags?\b)"
    r"[^;{}\n]{0,96}&\s*(?:0x0*1|1)\b",
    re.IGNORECASE,
)


def _load_lifecycle(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != LIFECYCLE_FORMAT:
        raise ValueError(f"{path}: expected {LIFECYCLE_FORMAT}")
    return report


def _actual_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call_position(body: str, function: str) -> int:
    return body.find(function + "(")


def extract_deleting_wrappers(
    source: Path,
    lifecycle_path: Path,
    ghidra_export: Path | None = None,
    release_helpers: tuple[str, ...] = DEFAULT_RELEASE_HELPERS,
) -> dict[str, Any]:
    lifecycle = _load_lifecycle(lifecycle_path)
    actual_source_sha256 = _actual_sha256(source)
    expected_source_sha256 = lifecycle.get("source_sha256")
    if (
        isinstance(expected_source_sha256, str)
        and expected_source_sha256
        and actual_source_sha256 != expected_source_sha256
    ):
        raise ValueError(
            "source identity mismatch: "
            f"lifecycle={expected_source_sha256}, actual={actual_source_sha256}"
        )

    if not release_helpers:
        raise ValueError("at least one release helper is required")
    release_helper_set = set(release_helpers)

    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    direct_calls = {
        name: set(_DIRECT_CALL.findall(body)) for name, body in functions.items()
    }
    incoming: dict[str, list[str]] = {}
    for target in {
        item.get("function")
        for row in lifecycle.get("targets") or []
        for item in row.get("teardown_transition_candidates") or []
        if isinstance(item.get("function"), str)
    }:
        incoming[target] = sorted(
            caller for caller, callees in direct_calls.items() if target in callees
        )

    ghidra_edges = _load_ghidra_edges(ghidra_export)
    class_rows: list[dict[str, Any]] = []
    flat_wrappers: list[dict[str, Any]] = []

    for target in lifecycle.get("targets") or []:
        class_name = target.get("class_name")
        descriptor = target.get("descriptor")
        rows: list[dict[str, Any]] = []
        for teardown in target.get("teardown_transition_candidates") or []:
            teardown_function = teardown.get("function")
            if not isinstance(teardown_function, str):
                continue
            for wrapper in incoming.get(teardown_function, []):
                if wrapper == teardown_function:
                    continue
                body = functions.get(wrapper, "")
                calls = direct_calls.get(wrapper, set())
                helper_calls = sorted(calls & release_helper_set)
                if not helper_calls:
                    continue
                teardown_position = _call_position(body, teardown_function)
                bit0_guard = _BIT0_GUARD.search(body)
                for helper in helper_calls:
                    release_position = _call_position(body, helper)
                    teardown_before_release = (
                        teardown_position >= 0
                        and release_position >= 0
                        and teardown_position < release_position
                    )
                    row = {
                        "class_name": class_name,
                        "descriptor": descriptor,
                        "wrapper_function": wrapper,
                        "teardown_transition_function": teardown_function,
                        "release_helper": helper,
                        "source_direct_call_to_teardown": True,
                        "source_direct_call_to_release_helper": True,
                        "teardown_before_release": teardown_before_release,
                        "bit0_delete_guard": bit0_guard is not None,
                        "bit0_guard_expression": (
                            bit0_guard.group(0).strip() if bit0_guard else None
                        ),
                        "ghidra_teardown_edge": _edge_confirmed(
                            ghidra_edges, wrapper, teardown_function
                        ),
                        "ghidra_release_edge": _edge_confirmed(
                            ghidra_edges, wrapper, helper
                        ),
                        "deleting_wrapper_shape": bool(
                            teardown_before_release and bit0_guard is not None
                        ),
                        "evidence_kind": (
                            "teardown-call-plus-release-helper-with-bit0-guard"
                            if teardown_before_release and bit0_guard is not None
                            else "teardown-call-plus-release-helper"
                        ),
                    }
                    rows.append(row)
                    flat_wrappers.append(row)

        rows.sort(
            key=lambda row: (
                row["deleting_wrapper_shape"] is not True,
                row["wrapper_function"],
                row["teardown_transition_function"],
                row["release_helper"],
            )
        )
        class_rows.append(
            {
                "class_name": class_name,
                "descriptor": descriptor,
                "wrapper_candidate_count": len(rows),
                "deleting_wrapper_shape_count": sum(
                    row["deleting_wrapper_shape"] is True for row in rows
                ),
                "wrappers": rows,
            }
        )

    class_rows.sort(
        key=lambda row: (
            -row["deleting_wrapper_shape_count"],
            row.get("class_name") is None,
            row.get("class_name") or "",
            int(row.get("descriptor") or 0),
        )
    )
    flat_wrappers.sort(
        key=lambda row: (
            row["deleting_wrapper_shape"] is not True,
            row.get("class_name") is None,
            row.get("class_name") or "",
            row["wrapper_function"],
        )
    )

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": actual_source_sha256,
        "lifecycle_source": str(lifecycle_path),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "release_helpers": list(release_helpers),
        "target_class_count": len(class_rows),
        "wrapper_candidate_count": len(flat_wrappers),
        "deleting_wrapper_shape_count": sum(
            row["deleting_wrapper_shape"] is True for row in flat_wrappers
        ),
        "ghidra_confirmed_shape_count": sum(
            row["deleting_wrapper_shape"] is True
            and row["ghidra_teardown_edge"] is True
            and row["ghidra_release_edge"] is True
            for row in flat_wrappers
        ),
        "classes": class_rows,
        "wrappers": flat_wrappers,
        "scope": {
            "deleting_destructor_semantics_proven": False,
            "release_helper_semantics_reproven_here": False,
            "note": (
                "The default release helper is inherited from prior project-wide "
                "static/runtime reconstruction. This artifact proves the wrapper "
                "call/guard shape only; it does not independently re-prove allocator "
                "ABI or rename the wrapper as a C++ deleting destructor."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--lifecycle", type=Path, required=True)
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument(
        "--release-helper",
        action="append",
        default=[],
        help="FUN_x release helper; repeat to add more (default: FUN_00886930)",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    helpers = tuple(args.release_helper) if args.release_helper else DEFAULT_RELEASE_HELPERS
    report = extract_deleting_wrappers(
        args.source,
        args.lifecycle,
        args.ghidra_export,
        helpers,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrapper candidates: {report['wrapper_candidate_count']}")
    print(f"deleting-wrapper shapes: {report['deleting_wrapper_shape_count']}")
    print(f"Ghidra-confirmed shapes: {report['ghidra_confirmed_shape_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
