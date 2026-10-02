#!/usr/bin/env python3
"""Extract conservative lifecycle evidence for class investigation targets.

The extractor joins an existing class manifest and evidence scorecard back to
recovered SHIFT.exe.c.  It records literal vtable writes, direct calls to
functions that write the nearest ancestor vtable, and simple literal field
assignments in the selected initializer body.

These observations are intentionally not promoted to C++ constructor or
destructor identities.  A function that rewrites the class vtable and then
calls an ancestor-vtable writer is reported as a teardown-transition candidate;
additional lifetime evidence is still required before semantic naming.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"
MANIFEST_FORMAT = "SHIFT-CLASS-MANIFEST/1"
SCORECARD_FORMAT = "SHIFT-CLASS-EVIDENCE-SCORECARD/1"

_FUNCTION_START = re.compile(
    r"\b(FUN_[0-9a-fA-F]+)\s*\([^;{}]*\)\s*\{", re.MULTILINE
)
_DIRECT_CALL = re.compile(r"\b(FUN_[0-9a-fA-F]+)\s*\(")
_VTABLE_WRITE = re.compile(
    r"(?P<statement>[^;\n]*=\s*&(?P<symbol>PTR_FUN_[0-9a-fA-F]{8})\s*;)",
    re.MULTILINE,
)
_THIS_OFFSET_ASSIGNMENT = re.compile(
    r"(?P<statement>[^;\n]*(?:\bthis\b|\bparam_1\b)[^;\n]*"
    r"\+\s*(?P<offset>0x[0-9a-fA-F]+|[0-9]+)[^;\n]*"
    r"=\s*(?P<value>[^;\n]+);)",
    re.MULTILINE,
)


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return report


def _extract_functions(text: str) -> dict[str, str]:
    """Extract Ghidra-style FUN_x function bodies in one forward pass."""
    out: dict[str, str] = {}
    cursor = 0
    while True:
        match = _FUNCTION_START.search(text, cursor)
        if match is None:
            break
        name = match.group(1)
        brace = text.find("{", match.start(), match.end())
        if brace < 0:
            cursor = match.end()
            continue
        depth = 0
        end = None
        for index in range(brace, len(text)):
            ch = text[index]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            break
        # Store only the body.  This prevents the function declaration itself
        # from being misread as a self-call.
        out.setdefault(name, text[brace + 1 : end - 1])
        cursor = end
    return out


def _function_address(name: object) -> str | None:
    if not isinstance(name, str) or not name.startswith("FUN_"):
        return None
    try:
        return f"0x{int(name[4:], 16):08x}"
    except ValueError:
        return None


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _load_ghidra_edges(root: Path | None) -> set[tuple[str, str]] | None:
    if root is None:
        return None
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing Ghidra callgraph: {path}")
    edges: set[tuple[str, str]] = set()
    for row in _read_jsonl(path):
        source = row.get("from_function")
        target = row.get("to")
        if (
            row.get("indirect") is False
            and isinstance(source, str)
            and isinstance(target, str)
        ):
            edges.add((source, target))
    return edges


def _vtable_symbol(value: object) -> str | None:
    return f"PTR_FUN_{value:08x}" if isinstance(value, int) else None


def _simple_field_assignments(body: str, own_vtable_symbol: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in _THIS_OFFSET_ASSIGNMENT.finditer(body):
        statement = " ".join(match.group("statement").split())
        if own_vtable_symbol and own_vtable_symbol in statement:
            continue
        offset_text = match.group("offset")
        rows.append(
            {
                "offset": int(offset_text, 0),
                "value_expression": match.group("value").strip(),
                "statement": statement,
            }
        )
    rows.sort(key=lambda row: (row["offset"], row["statement"]))
    return rows


def _edge_confirmed(
    ghidra_edges: set[tuple[str, str]] | None,
    caller: str,
    callee: str,
) -> bool | None:
    if ghidra_edges is None:
        return None
    caller_address = _function_address(caller)
    callee_address = _function_address(callee)
    if caller_address is None or callee_address is None:
        return False
    return (caller_address, callee_address) in ghidra_edges


def extract_lifecycle_evidence(
    source: Path,
    manifest_path: Path,
    scorecard_path: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    manifest = _load_json(manifest_path, MANIFEST_FORMAT)
    scorecard = _load_json(scorecard_path, SCORECARD_FORMAT)

    for key in ("source_sha256", "exe_sha256"):
        left = manifest.get(key)
        right = scorecard.get(key)
        if left and right and left != right:
            raise ValueError(
                f"source identity mismatch for {key}: manifest={left}, scorecard={right}"
            )

    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    ghidra_edges = _load_ghidra_edges(ghidra_export)

    direct_calls = {
        name: set(_DIRECT_CALL.findall(body)) for name, body in functions.items()
    }
    writes_by_function: dict[str, set[str]] = defaultdict(set)
    writers_by_vtable: dict[str, set[str]] = defaultdict(set)
    write_statements: dict[str, list[dict[str, str]]] = defaultdict(list)
    for name, body in functions.items():
        for match in _VTABLE_WRITE.finditer(body):
            symbol = match.group("symbol")
            statement = " ".join(match.group("statement").split())
            writes_by_function[name].add(symbol)
            writers_by_vtable[symbol].add(name)
            write_statements[name].append(
                {"vtable_symbol": symbol, "statement": statement}
            )

    manifest_by_descriptor = {
        int(row["descriptor"]): row
        for row in manifest.get("classes") or []
        if isinstance(row.get("descriptor"), int)
    }
    manifest_by_name = {
        row["name"]: row
        for row in manifest.get("classes") or []
        if isinstance(row.get("name"), str)
    }

    targets = [
        row
        for row in scorecard.get("rows") or []
        if row.get("evidence_tier") == "lifecycle-investigation-ready"
    ]
    results: list[dict[str, Any]] = []

    for target in targets:
        descriptor = target.get("descriptor")
        class_name = target.get("class_name")
        class_row = (
            manifest_by_descriptor.get(int(descriptor))
            if isinstance(descriptor, int)
            else manifest_by_name.get(class_name)
        )
        if class_row is None:
            results.append(
                {
                    "class_name": class_name,
                    "descriptor": descriptor,
                    "complete": False,
                    "missing": ["class_manifest_row"],
                }
            )
            continue

        own_vtable = class_row.get("unique_vtable")
        own_vtable_symbol = _vtable_symbol(own_vtable)
        initializer = target.get("unambiguous_initializer")
        initializer_body = functions.get(initializer) if isinstance(initializer, str) else None

        ancestor_row = None
        for ancestor_name in class_row.get("ancestry") or []:
            candidate = manifest_by_name.get(ancestor_name)
            if candidate is not None and isinstance(candidate.get("unique_vtable"), int):
                ancestor_row = candidate
                break
        ancestor_vtable_symbol = _vtable_symbol(
            ancestor_row.get("unique_vtable") if ancestor_row else None
        )
        ancestor_writers = (
            set(writers_by_vtable.get(ancestor_vtable_symbol, ()))
            if ancestor_vtable_symbol
            else set()
        )

        initializer_calls = sorted(
            direct_calls.get(initializer, set()) if isinstance(initializer, str) else set()
        )
        base_initializer_candidates = sorted(set(initializer_calls) & ancestor_writers)
        base_initializer_edges = [
            {
                "target": callee,
                "ghidra_direct_call": _edge_confirmed(ghidra_edges, initializer, callee),
            }
            for callee in base_initializer_candidates
            if isinstance(initializer, str)
        ]

        own_writers = sorted(
            writers_by_vtable.get(own_vtable_symbol, ()) if own_vtable_symbol else ()
        )
        teardown_candidates = []
        for function in own_writers:
            if function == initializer:
                continue
            base_calls = sorted(direct_calls.get(function, set()) & ancestor_writers)
            if not base_calls:
                continue
            teardown_candidates.append(
                {
                    "function": function,
                    "own_vtable_write_statements": [
                        row
                        for row in write_statements.get(function, [])
                        if row["vtable_symbol"] == own_vtable_symbol
                    ],
                    "ancestor_transition_calls": [
                        {
                            "target": callee,
                            "ghidra_direct_call": _edge_confirmed(
                                ghidra_edges, function, callee
                            ),
                        }
                        for callee in base_calls
                    ],
                    "evidence_kind": (
                        "own-vtable-write-followed-by-call-to-ancestor-vtable-writer"
                    ),
                }
            )

        incoming_initializer_callers = sorted(
            caller
            for caller, callees in direct_calls.items()
            if isinstance(initializer, str) and initializer in callees
        )

        missing = []
        if own_vtable_symbol is None:
            missing.append("unique_vtable")
        if initializer_body is None:
            missing.append("initializer_body")
        if (
            isinstance(initializer, str)
            and own_vtable_symbol
            and own_vtable_symbol not in writes_by_function.get(initializer, set())
        ):
            missing.append("initializer_own_vtable_write")

        results.append(
            {
                "class_name": class_name,
                "descriptor": descriptor,
                "parent_class": class_row.get("parent_class"),
                "nearest_ancestor_with_unique_vtable": (
                    ancestor_row.get("name") if ancestor_row else None
                ),
                "own_vtable": own_vtable,
                "own_vtable_symbol": own_vtable_symbol,
                "ancestor_vtable": (
                    ancestor_row.get("unique_vtable") if ancestor_row else None
                ),
                "ancestor_vtable_symbol": ancestor_vtable_symbol,
                "initializer_candidate": initializer,
                "initializer_present": initializer_body is not None,
                "initializer_writes_own_vtable": (
                    isinstance(initializer, str)
                    and own_vtable_symbol is not None
                    and own_vtable_symbol in writes_by_function.get(initializer, set())
                ),
                "initializer_own_vtable_write_statements": [
                    row
                    for row in write_statements.get(initializer, [])
                    if row["vtable_symbol"] == own_vtable_symbol
                ]
                if isinstance(initializer, str)
                else [],
                "initializer_direct_calls": initializer_calls,
                "base_initializer_candidates": base_initializer_edges,
                "literal_field_assignments": (
                    _simple_field_assignments(initializer_body, own_vtable_symbol)
                    if initializer_body is not None
                    else []
                ),
                "initializer_callers": [
                    {
                        "function": caller,
                        "ghidra_direct_call": _edge_confirmed(
                            ghidra_edges, caller, initializer
                        ),
                    }
                    for caller in incoming_initializer_callers
                    if isinstance(initializer, str)
                ],
                "own_vtable_writer_functions": own_writers,
                "teardown_transition_candidates": teardown_candidates,
                "complete": not missing,
                "missing": missing,
            }
        )

    results.sort(
        key=lambda row: (
            row.get("complete") is not True,
            row.get("class_name") is None,
            row.get("class_name") or "",
            int(row.get("descriptor") or 0),
        )
    )
    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": manifest.get("source_sha256"),
        "exe_sha256": manifest.get("exe_sha256"),
        "manifest": str(manifest_path),
        "scorecard": str(scorecard_path),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "target_count": len(results),
        "complete_target_count": sum(row.get("complete") is True for row in results),
        "initializer_own_vtable_write_count": sum(
            row.get("initializer_writes_own_vtable") is True for row in results
        ),
        "base_initializer_link_count": sum(
            len(row.get("base_initializer_candidates") or []) for row in results
        ),
        "teardown_transition_candidate_count": sum(
            len(row.get("teardown_transition_candidates") or []) for row in results
        ),
        "targets": results,
        "scope": {
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "allocation_semantics_proven": False,
            "field_meanings_proven": False,
            "note": (
                "Vtable writes, ancestor-writer calls and literal field assignments "
                "are direct source observations. Lifecycle role names remain "
                "candidates until supported by stronger lifetime/call-site evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scorecard", type=Path, required=True)
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = extract_lifecycle_evidence(
        args.source,
        args.manifest,
        args.scorecard,
        args.ghidra_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"targets: {report['target_count']}")
    print(f"complete targets: {report['complete_target_count']}")
    print(
        "teardown transition candidates: "
        f"{report['teardown_transition_candidate_count']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
