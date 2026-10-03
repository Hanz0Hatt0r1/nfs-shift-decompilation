#!/usr/bin/env python3
"""Inventory source call sites for the recovered retail memory-wrapper family.

The extractor records only source-level observations: caller identity, wrapper
identity, raw argument expressions, observed arity, literal tokens and simple
assignment flow.  When a Ghidra evidence database is supplied, each source call
is independently cross-checked against a direct callgraph edge.

Argument positions are deliberately not assigned semantic names such as size,
pool, alignment or flags.  Those roles require a later join with instruction
forwarding and independent allocation/free evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from extract_class_lifecycle_source_evidence import (
    _edge_confirmed,
    _extract_functions,
    _load_ghidra_edges,
)

FORMAT = "SHIFT-MEMORY-WRAPPER-CALLSITES/1"

WRAPPER_SPECS: dict[str, dict[str, Any]] = {
    "FUN_008868c0": {
        "address": "0x008868c0",
        "side": "create",
        "physical_parameter_count": 1,
    },
    "FUN_008868d0": {
        "address": "0x008868d0",
        "side": "create",
        "physical_parameter_count": 2,
    },
    "FUN_00886900": {
        "address": "0x00886900",
        "side": "create",
        "physical_parameter_count": 3,
    },
    "FUN_00886930": {
        "address": "0x00886930",
        "side": "release",
        "physical_parameter_count": 3,
    },
    "FUN_00886950": {
        "address": "0x00886950",
        "side": "release",
        "physical_parameter_count": 4,
    },
}

_ASSIGNMENT = re.compile(r"(?<![=!<>])=(?!=)")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INTEGER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?P<value>0x[0-9a-fA-F]+|[0-9]+)(?P<suffix>[uUlL]*)(?![A-Za-z0-9_])"
)
_FULL_INTEGER = re.compile(r"^[+-]?(?:0x[0-9a-fA-F]+|[0-9]+)[uUlL]*$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(text: str) -> str:
    return " ".join(text.split())


def _find_closing_paren(text: str, open_index: int) -> int | None:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(open_index, len(text)):
        ch = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {'"', "'"}:
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _split_arguments(raw: str) -> list[str]:
    if not raw.strip():
        return []
    out: list[str] = []
    start = 0
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    for index, ch in enumerate(raw):
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {'"', "'"}:
            quote = ch
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(paren - 1, 0)
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket = max(bracket - 1, 0)
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace = max(brace - 1, 0)
        elif ch == "," and paren == bracket == brace == 0:
            out.append(raw[start:index].strip())
            start = index + 1
    out.append(raw[start:].strip())
    return out


def _statement_for_call(body: str, position: int, close_index: int) -> str:
    start = body.rfind(";", 0, position)
    brace_open = body.rfind("{", 0, position)
    brace_close = body.rfind("}", 0, position)
    start = max(start, brace_open, brace_close) + 1
    end = body.find(";", close_index)
    if end < 0:
        end = close_index
    else:
        end += 1
    return _compact(body[start:end])


def _assigned_local(statement: str, wrapper: str) -> str | None:
    call_pos = statement.find(wrapper + "(")
    if call_pos < 0:
        # Ghidra occasionally inserts whitespace between a function name and '('.
        match = re.search(rf"\b{re.escape(wrapper)}\s*\(", statement)
        call_pos = match.start() if match else -1
    if call_pos < 0:
        return None
    prefix = statement[:call_pos]
    assignments = list(_ASSIGNMENT.finditer(prefix))
    if not assignments:
        return None
    lhs = prefix[: assignments[-1].start()]
    identifiers = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", lhs)
    if not identifiers:
        return None
    candidate = identifiers[-1]
    if candidate in {"if", "while", "for", "return"}:
        return None
    return candidate


def _integer_literals(expression: str) -> list[int]:
    values: list[int] = []
    for match in _INTEGER_TOKEN.finditer(expression):
        try:
            values.append(int(match.group("value"), 0))
        except ValueError:
            pass
    return values


def _simple_integer(expression: str) -> int | None:
    token = expression.strip()
    if not _FULL_INTEGER.fullmatch(token):
        return None
    token = re.sub(r"[uUlL]+$", "", token)
    try:
        return int(token, 0)
    except ValueError:
        return None


def _expression_kind(expression: str) -> str:
    value = expression.strip()
    if not value:
        return "empty"
    if _FULL_INTEGER.fullmatch(value):
        return "integer-literal"
    if _IDENTIFIER.fullmatch(value):
        return "identifier"
    if re.search(r"\bFUN_[0-9a-fA-F]+\s*\(", value):
        return "call-expression"
    if value.startswith("&"):
        return "address-expression"
    if re.search(r"(?:<<|>>|[+\-*/%&|^])", value):
        return "arithmetic-expression"
    if value.startswith("("):
        return "cast-or-parenthesized-expression"
    return "compound-expression"


def _call_matches(body: str, wrapper: str) -> Iterable[tuple[int, int, str]]:
    pattern = re.compile(rf"\b{re.escape(wrapper)}\s*\(")
    for match in pattern.finditer(body):
        open_index = body.find("(", match.start(), match.end())
        if open_index < 0:
            continue
        close_index = _find_closing_paren(body, open_index)
        if close_index is None:
            continue
        yield match.start(), close_index, body[open_index + 1 : close_index]


def extract_memory_wrapper_callsites(
    source: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    ghidra_edges = _load_ghidra_edges(ghidra_export)

    rows: list[dict[str, Any]] = []
    per_wrapper_callers: dict[str, set[str]] = defaultdict(set)
    per_wrapper_arities: dict[str, Counter[int]] = defaultdict(Counter)
    per_wrapper_first_literals: dict[str, Counter[int]] = defaultdict(Counter)

    for caller, body in functions.items():
        for wrapper, spec in WRAPPER_SPECS.items():
            occurrence = 0
            for position, close_index, raw_arguments in _call_matches(body, wrapper):
                arguments = _split_arguments(raw_arguments)
                statement = _statement_for_call(body, position, close_index)
                argument_rows = []
                for index, expression in enumerate(arguments):
                    simple_integer = _simple_integer(expression)
                    argument_rows.append(
                        {
                            "index": index,
                            "expression": _compact(expression),
                            "kind": _expression_kind(expression),
                            "integer_literals": _integer_literals(expression),
                            "simple_integer_value": simple_integer,
                        }
                    )
                edge = _edge_confirmed(ghidra_edges, caller, wrapper)
                expected_count = int(spec["physical_parameter_count"])
                row = {
                    "caller": caller,
                    "wrapper": wrapper,
                    "wrapper_address": spec["address"],
                    "side": spec["side"],
                    "occurrence": occurrence,
                    "statement": statement,
                    "assigned_local": _assigned_local(statement, wrapper),
                    "observed_argument_count": len(arguments),
                    "physical_parameter_count": expected_count,
                    "arity_matches_physical_parameter_count": len(arguments) == expected_count,
                    "arguments": argument_rows,
                    "ghidra_direct_edge": edge,
                    "evidence_kind": "source-wrapper-callsite",
                }
                rows.append(row)
                per_wrapper_callers[wrapper].add(caller)
                per_wrapper_arities[wrapper][len(arguments)] += 1
                if argument_rows and argument_rows[0]["simple_integer_value"] is not None:
                    per_wrapper_first_literals[wrapper][
                        int(argument_rows[0]["simple_integer_value"])
                    ] += 1
                occurrence += 1

    rows.sort(
        key=lambda row: (
            row["wrapper"],
            row["caller"],
            int(row["occurrence"]),
        )
    )

    wrappers: list[dict[str, Any]] = []
    for wrapper, spec in WRAPPER_SPECS.items():
        wrapper_rows = [row for row in rows if row["wrapper"] == wrapper]
        arities = per_wrapper_arities[wrapper]
        first_literals = per_wrapper_first_literals[wrapper]
        wrappers.append(
            {
                "wrapper": wrapper,
                "address": spec["address"],
                "side": spec["side"],
                "physical_parameter_count": spec["physical_parameter_count"],
                "callsite_count": len(wrapper_rows),
                "caller_count": len(per_wrapper_callers[wrapper]),
                "callers": sorted(per_wrapper_callers[wrapper]),
                "observed_arities": [
                    {"arity": arity, "count": count}
                    for arity, count in sorted(arities.items())
                ],
                "first_argument_simple_integer_values": [
                    {"value": value, "count": count}
                    for value, count in sorted(first_literals.items())
                ],
                "ghidra_confirmed_callsite_count": sum(
                    row["ghidra_direct_edge"] is True for row in wrapper_rows
                ),
                "ghidra_mismatch_callsite_count": sum(
                    row["ghidra_direct_edge"] is False for row in wrapper_rows
                ),
            }
        )

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": _sha256(source),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "function_count": len(functions),
        "callsite_count": len(rows),
        "wrapper_count": len(WRAPPER_SPECS),
        "ghidra_checked_callsite_count": sum(
            row["ghidra_direct_edge"] is not None for row in rows
        ),
        "ghidra_confirmed_callsite_count": sum(
            row["ghidra_direct_edge"] is True for row in rows
        ),
        "ghidra_mismatch_callsite_count": sum(
            row["ghidra_direct_edge"] is False for row in rows
        ),
        "arity_match_callsite_count": sum(
            row["arity_matches_physical_parameter_count"] is True for row in rows
        ),
        "wrappers": wrappers,
        "callsites": rows,
        "scope": {
            "source_argument_expressions_observed": True,
            "ghidra_direct_edges_optional": True,
            "argument_semantic_roles_proven": False,
            "allocation_size_role_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "allocator_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "This artifact inventories raw recovered-source call expressions and "
                "optionally checks caller->wrapper edges in Ghidra. Parameter-count "
                "agreement is ABI-shape consistency only. Argument meanings require "
                "a separate join with instruction forwarding and independent call-site "
                "or runtime semantics."
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
    print(f"functions scanned: {report['function_count']}")
    print(f"wrapper callsites: {report['callsite_count']}")
    print(f"arity matches: {report['arity_match_callsite_count']}")
    print(f"Ghidra confirmed callsites: {report['ghidra_confirmed_callsite_count']}")
    print(f"Ghidra mismatches: {report['ghidra_mismatch_callsite_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
