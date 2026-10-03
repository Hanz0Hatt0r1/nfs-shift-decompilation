#!/usr/bin/env python3
"""Extract conservative source call-site evidence for retail memory wrappers.

This scanner records every direct source call to the five established wrapper
functions, preserving raw argument expressions and literal positions. Optional
Ghidra callgraph evidence cross-checks only caller->wrapper identity. No argument
position is assigned a semantic role by this layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from extract_class_lifecycle_source_evidence import (
    _edge_confirmed,
    _extract_functions,
    _load_ghidra_edges,
)

FORMAT = "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1"
WRAPPERS = (
    "FUN_008868c0",
    "FUN_008868d0",
    "FUN_00886900",
    "FUN_00886930",
    "FUN_00886950",
)

_CALL_START = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in WRAPPERS) + r")\s*\("
)
_INTEGER_LITERAL = re.compile(
    r"(?<![A-Za-z0-9_])(?P<sign>[+-]?)(?P<value>0[xX][0-9a-fA-F]+|[0-9]+)(?P<suffix>[uUlL]*)(?![A-Za-z0-9_])"
)
_EXACT_INTEGER_LITERAL = re.compile(
    r"^\s*(?P<sign>[+-]?)(?P<value>0[xX][0-9a-fA-F]+|[0-9]+)(?P<suffix>[uUlL]*)\s*$"
)
_SIMPLE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _integer_value(match: re.Match[str]) -> int:
    value = int(match.group("value"), 0)
    return -value if match.group("sign") == "-" else value


def _literal_values(expression: str) -> list[int]:
    values: list[int] = []
    for match in _INTEGER_LITERAL.finditer(expression):
        try:
            values.append(_integer_value(match))
        except ValueError:
            continue
    return values


def _exact_integer_value(expression: str) -> int | None:
    match = _EXACT_INTEGER_LITERAL.match(expression)
    if match is None:
        return None
    try:
        return _integer_value(match)
    except ValueError:
        return None


def _statement_for_position(body: str, position: int) -> str:
    """Return a compact semicolon-bounded source statement around a call."""
    start = body.rfind(";", 0, position)
    brace_open = body.rfind("{", 0, position)
    brace_close = body.rfind("}", 0, position)
    start = max(start, brace_open, brace_close) + 1
    end = body.find(";", position)
    if end < 0:
        end = len(body)
    return " ".join(body[start : end + 1].split())


def _find_matching_paren(text: str, open_index: int) -> int | None:
    """Find the closing paren while respecting nested strings/comments."""
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = open_index
    while index < len(text):
        ch = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if ch == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            index += 1
            continue

        if ch == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if ch in {'"', "'"}:
            quote = ch
            index += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _split_top_level_arguments(arguments: str) -> list[str]:
    if not arguments.strip():
        return []
    rows: list[str] = []
    start = 0
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = 0
    while index < len(arguments):
        ch = arguments[index]
        nxt = arguments[index + 1] if index + 1 < len(arguments) else ""

        if line_comment:
            if ch == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            index += 1
            continue

        if ch == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if ch in {'"', "'"}:
            quote = ch
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        elif ch == "," and paren == 0 and bracket == 0 and brace == 0:
            rows.append(arguments[start:index].strip())
            start = index + 1
        index += 1
    rows.append(arguments[start:].strip())
    return rows


def _argument_record(index: int, expression: str) -> dict[str, Any]:
    exact = _exact_integer_value(expression)
    return {
        "index": index,
        "expression": expression,
        "integer_literals": _literal_values(expression),
        "is_exact_integer_literal": exact is not None,
        "exact_integer_value": exact,
        "is_simple_identifier": bool(_SIMPLE_IDENTIFIER.fullmatch(expression.strip())),
    }


def _extract_calls_from_body(caller: str, body: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    occurrence_by_wrapper: Counter[str] = Counter()
    for match in _CALL_START.finditer(body):
        wrapper = match.group(1)
        open_index = body.find("(", match.start(), match.end())
        if open_index < 0:
            continue
        close_index = _find_matching_paren(body, open_index)
        if close_index is None:
            calls.append(
                {
                    "caller": caller,
                    "wrapper": wrapper,
                    "occurrence": occurrence_by_wrapper[wrapper],
                    "source_position": match.start(),
                    "source_statement": _statement_for_position(body, match.start()),
                    "arguments_parse_complete": False,
                    "raw_arguments": None,
                    "argument_count": None,
                    "arguments": [],
                }
            )
            occurrence_by_wrapper[wrapper] += 1
            continue

        raw_arguments = body[open_index + 1 : close_index].strip()
        expressions = _split_top_level_arguments(raw_arguments)
        calls.append(
            {
                "caller": caller,
                "wrapper": wrapper,
                "occurrence": occurrence_by_wrapper[wrapper],
                "source_position": match.start(),
                "source_statement": _statement_for_position(body, match.start()),
                "arguments_parse_complete": True,
                "raw_arguments": raw_arguments,
                "argument_count": len(expressions),
                "arguments": [
                    _argument_record(index, expression)
                    for index, expression in enumerate(expressions)
                ],
            }
        )
        occurrence_by_wrapper[wrapper] += 1
    return calls


def _wrapper_summary(wrapper: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    callers = sorted({str(row["caller"]) for row in rows})
    argument_count_histogram: Counter[int] = Counter()
    literal_values_by_position: dict[int, set[int]] = defaultdict(set)
    exact_literal_counts_by_position: Counter[int] = Counter()
    any_literal_counts_by_position: Counter[int] = Counter()

    for row in rows:
        count = row.get("argument_count")
        if isinstance(count, int):
            argument_count_histogram[count] += 1
        for argument in row.get("arguments") or []:
            index = int(argument["index"])
            literals = argument.get("integer_literals") or []
            if literals:
                any_literal_counts_by_position[index] += 1
                literal_values_by_position[index].update(int(value) for value in literals)
            if argument.get("is_exact_integer_literal") is True:
                exact_literal_counts_by_position[index] += 1

    positions = sorted(
        set(literal_values_by_position)
        | set(exact_literal_counts_by_position)
        | set(any_literal_counts_by_position)
    )
    literal_positions = [
        {
            "index": index,
            "callsite_count_with_any_integer_literal": any_literal_counts_by_position[index],
            "callsite_count_with_exact_integer_literal": exact_literal_counts_by_position[index],
            "distinct_integer_literals": sorted(literal_values_by_position[index]),
        }
        for index in positions
    ]

    edge_states = [row.get("ghidra_direct_edge") for row in rows]
    return {
        "wrapper": wrapper,
        "callsite_count": len(rows),
        "caller_count": len(callers),
        "callers": callers,
        "argument_count_histogram": [
            {"argument_count": count, "callsite_count": argument_count_histogram[count]}
            for count in sorted(argument_count_histogram)
        ],
        "literal_positions": literal_positions,
        "ghidra_crosscheck_available": any(state is not None for state in edge_states),
        "ghidra_confirmed_callsite_count": sum(state is True for state in edge_states),
        "ghidra_rejected_callsite_count": sum(state is False for state in edge_states),
    }


def extract_memory_wrapper_callsites(
    source: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    ghidra_edges = _load_ghidra_edges(ghidra_export)

    rows: list[dict[str, Any]] = []
    for caller, body in functions.items():
        for row in _extract_calls_from_body(caller, body):
            row["ghidra_direct_edge"] = _edge_confirmed(
                ghidra_edges,
                caller,
                str(row["wrapper"]),
            )
            rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row["wrapper"]),
            str(row["caller"]),
            int(row["occurrence"]),
            int(row["source_position"]),
        )
    )
    grouped: dict[str, list[dict[str, Any]]] = {wrapper: [] for wrapper in WRAPPERS}
    for row in rows:
        grouped[str(row["wrapper"])].append(row)
    wrappers = [_wrapper_summary(wrapper, grouped[wrapper]) for wrapper in WRAPPERS]

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": _sha256(source),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "wrapper_count": len(WRAPPERS),
        "callsite_count": len(rows),
        "caller_count": len({row["caller"] for row in rows}),
        "parsed_callsite_count": sum(row["arguments_parse_complete"] is True for row in rows),
        "unparsed_callsite_count": sum(row["arguments_parse_complete"] is not True for row in rows),
        "ghidra_crosscheck_available": ghidra_edges is not None,
        "ghidra_confirmed_callsite_count": sum(row["ghidra_direct_edge"] is True for row in rows),
        "ghidra_rejected_callsite_count": sum(row["ghidra_direct_edge"] is False for row in rows),
        "wrappers": wrappers,
        "callsites": rows,
        "scope": {
            "direct_source_calls_observed": True,
            "raw_argument_expressions_observed": True,
            "integer_literal_positions_observed": True,
            "ghidra_call_edges_crosschecked": ghidra_edges is not None,
            "argument_roles_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "Rows preserve direct source calls, raw argument expressions and literal "
                "positions. Optional Ghidra evidence confirms only caller-to-wrapper "
                "edges. Argument positions are not named as size, alignment, pool, tag, "
                "delete kind or ownership state by this layer."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = extract_memory_wrapper_callsites(args.source, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"callsites: {report['callsite_count']}")
    print(f"callers: {report['caller_count']}")
    print(f"Ghidra-confirmed callsites: {report['ghidra_confirmed_callsite_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
