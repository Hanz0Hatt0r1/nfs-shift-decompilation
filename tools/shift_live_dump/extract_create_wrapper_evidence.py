#!/usr/bin/env python3
"""Extract conservative factory create-wrapper shapes from recovered source.

The extractor starts from already-established factory->initializer links.  It
looks at source call order inside each factory and records the direct call
immediately before the initializer.  A strong create-wrapper shape additionally
requires that the previous call's return value is assigned to a local variable
and that the same local is passed to the initializer.

No helper is pre-labelled as an allocator.  Repeated immediate-preinitializer
helpers are aggregated so the evidence itself can reveal likely allocation
primitives such as the retail helper adjacent to multiple class initializers.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from extract_class_lifecycle_source_evidence import (
    _DIRECT_CALL,
    _edge_confirmed,
    _extract_functions,
    _load_ghidra_edges,
)

FORMAT = "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1"
INITIALIZER_FORMAT = "SHIFT-FACTORY-INITIALIZER-LINKS/1"
_ASSIGNMENT = re.compile(r"(?<![=!<>])=(?!=)")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INTEGER_LITERAL = re.compile(r"(?<![A-Za-z0-9_])(0x[0-9a-fA-F]+|[0-9]+)(?![A-Za-z0-9_])")


def _load_links(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != INITIALIZER_FORMAT:
        raise ValueError(f"{path}: expected {INITIALIZER_FORMAT}")
    return report


def _statement_for_position(body: str, position: int) -> str:
    """Return a compact semicolon-bounded source statement around position."""
    start = body.rfind(";", 0, position)
    brace_open = body.rfind("{", 0, position)
    brace_close = body.rfind("}", 0, position)
    start = max(start, brace_open, brace_close) + 1
    end = body.find(";", position)
    if end < 0:
        end = len(body)
    return " ".join(body[start : end + 1].split())


def _assigned_local(statement: str, function: str) -> str | None:
    function_pos = statement.find(function + "(")
    if function_pos < 0:
        return None
    prefix = statement[:function_pos]
    matches = list(_ASSIGNMENT.finditer(prefix))
    if not matches:
        return None
    lhs = prefix[: matches[-1].start()]
    identifiers = _IDENTIFIER.findall(lhs)
    if not identifiers:
        return None
    candidate = identifiers[-1]
    if candidate in {"if", "while", "for", "return"}:
        return None
    return candidate


def _call_arguments(statement: str, function: str) -> str | None:
    start = statement.find(function + "(")
    if start < 0:
        return None
    cursor = start + len(function) + 1
    depth = 1
    begin = cursor
    while cursor < len(statement):
        ch = statement[cursor]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return statement[begin:cursor].strip()
        cursor += 1
    return None


def _literal_arguments(arguments: str | None) -> list[int]:
    if not arguments:
        return []
    out: list[int] = []
    for match in _INTEGER_LITERAL.finditer(arguments):
        token = match.group(1)
        try:
            out.append(int(token, 0))
        except ValueError:
            pass
    return out


def _local_flows_to_initializer(
    initializer_statement: str,
    initializer: str,
    local: str | None,
) -> bool:
    if not local:
        return False
    arguments = _call_arguments(initializer_statement, initializer)
    if arguments is None:
        return False
    return re.search(rf"\b{re.escape(local)}\b", arguments) is not None


def extract_create_wrappers(
    source: Path,
    initializer_links_path: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    links = _load_links(initializer_links_path)
    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    ghidra_edges = _load_ghidra_edges(ghidra_export)

    rows: list[dict[str, Any]] = []
    helper_class_sets: dict[str, set[str]] = defaultdict(set)
    helper_factory_sets: dict[str, set[str]] = defaultdict(set)
    helper_flow_counts: Counter[str] = Counter()

    for link in links.get("links") or []:
        factory = link.get("factory_function")
        initializer = link.get("initializer_candidate")
        if not isinstance(factory, str) or not isinstance(initializer, str):
            continue
        body = functions.get(factory)
        if body is None:
            rows.append(
                {
                    "class_name": link.get("class"),
                    "descriptor": link.get("descriptor"),
                    "factory_function": factory,
                    "initializer_candidate": initializer,
                    "source_factory_present": False,
                    "create_wrapper_shape": False,
                    "missing": ["factory_body"],
                }
            )
            continue

        ordered_calls = [
            (match.start(), match.group(1)) for match in _DIRECT_CALL.finditer(body)
        ]
        initializer_indices = [
            index
            for index, (_, name) in enumerate(ordered_calls)
            if name == initializer
        ]
        if not initializer_indices:
            rows.append(
                {
                    "class_name": link.get("class"),
                    "descriptor": link.get("descriptor"),
                    "factory_function": factory,
                    "initializer_candidate": initializer,
                    "source_factory_present": True,
                    "source_initializer_call_present": False,
                    "create_wrapper_shape": False,
                    "missing": ["initializer_call"],
                }
            )
            continue

        # The initializer-link extractor proves the semantic source edge.  If a
        # decompiled factory calls the same initializer more than once, preserve
        # every occurrence rather than silently selecting one branch.
        for occurrence, call_index in enumerate(initializer_indices):
            initializer_pos, _ = ordered_calls[call_index]
            initializer_statement = _statement_for_position(body, initializer_pos)
            previous = ordered_calls[call_index - 1] if call_index > 0 else None
            helper = previous[1] if previous else None
            helper_statement = (
                _statement_for_position(body, previous[0]) if previous else None
            )
            assigned_local = (
                _assigned_local(helper_statement, helper)
                if helper_statement is not None and helper is not None
                else None
            )
            local_flows = _local_flows_to_initializer(
                initializer_statement,
                initializer,
                assigned_local,
            )
            helper_arguments = (
                _call_arguments(helper_statement, helper)
                if helper_statement is not None and helper is not None
                else None
            )
            literal_arguments = _literal_arguments(helper_arguments)
            source_shape = bool(helper and assigned_local and local_flows)

            row = {
                "class_name": link.get("class"),
                "descriptor": link.get("descriptor"),
                "factory_function": factory,
                "initializer_candidate": initializer,
                "initializer_occurrence": occurrence,
                "source_factory_present": True,
                "source_initializer_call_present": True,
                "initializer_statement": initializer_statement,
                "immediate_preinitializer_helper": helper,
                "helper_statement": helper_statement,
                "helper_assigned_local": assigned_local,
                "helper_arguments": helper_arguments,
                "helper_literal_arguments": literal_arguments,
                "helper_result_flows_to_initializer": local_flows,
                "source_create_wrapper_shape": source_shape,
                "ghidra_factory_to_initializer": _edge_confirmed(
                    ghidra_edges, factory, initializer
                ),
                "ghidra_factory_to_helper": (
                    _edge_confirmed(ghidra_edges, factory, helper)
                    if helper is not None
                    else None
                ),
                "create_wrapper_shape": bool(
                    source_shape
                    and (
                        ghidra_edges is None
                        or (
                            _edge_confirmed(ghidra_edges, factory, initializer) is True
                            and _edge_confirmed(ghidra_edges, factory, helper) is True
                        )
                    )
                ),
                "missing": [],
                "evidence_kind": (
                    "immediate-helper-result-flows-to-initializer"
                    if source_shape
                    else "ordered-factory-call-context"
                ),
            }
            rows.append(row)

            if helper is not None:
                class_name = link.get("class")
                helper_class_sets[helper].add(str(class_name))
                helper_factory_sets[helper].add(factory)
                if local_flows:
                    helper_flow_counts[helper] += 1

    rows.sort(
        key=lambda row: (
            row.get("create_wrapper_shape") is not True,
            row.get("class_name") is None,
            row.get("class_name") or "",
            row.get("factory_function") or "",
            int(row.get("initializer_occurrence") or 0),
        )
    )

    helpers = []
    for helper in sorted(
        helper_class_sets,
        key=lambda name: (
            -helper_flow_counts[name],
            -len(helper_class_sets[name]),
            name,
        ),
    ):
        helpers.append(
            {
                "function": helper,
                "linked_class_count": len(helper_class_sets[helper]),
                "factory_count": len(helper_factory_sets[helper]),
                "result_flow_count": helper_flow_counts[helper],
                "classes": sorted(helper_class_sets[helper]),
                "factories": sorted(helper_factory_sets[helper]),
                "evidence_kind": "immediate-preinitializer-helper-aggregate",
            }
        )

    return {
        "format": FORMAT,
        "source": str(source),
        "initializer_links": str(initializer_links_path),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "link_count": len(rows),
        "source_create_wrapper_shape_count": sum(
            row.get("source_create_wrapper_shape") is True for row in rows
        ),
        "create_wrapper_shape_count": sum(
            row.get("create_wrapper_shape") is True for row in rows
        ),
        "distinct_preinitializer_helper_count": len(helpers),
        "helpers": helpers,
        "links": rows,
        "scope": {
            "allocation_helper_semantics_proven": False,
            "object_allocation_proven": False,
            "constructor_semantics_proven": False,
            "note": (
                "A create-wrapper shape proves source call order and local-value flow "
                "from the immediate preinitializer helper into the initializer. It "
                "does not by itself prove that the helper allocates memory or that "
                "the initializer is a C++ constructor. Repeated helper aggregation "
                "is discovery evidence, not semantic promotion."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--initializer-links", type=Path, required=True)
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = extract_create_wrappers(
        args.source,
        args.initializer_links,
        args.ghidra_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"links: {report['link_count']}")
    print(f"source create-wrapper shapes: {report['source_create_wrapper_shape_count']}")
    print(f"cross-checked create-wrapper shapes: {report['create_wrapper_shape_count']}")
    print(f"distinct preceding helpers: {report['distinct_preinitializer_helper_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
