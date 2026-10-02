#!/usr/bin/env python3
"""Extract conservative factory-to-initializer links from SHIFT static evidence.

A link requires a source function that references a class RTTI descriptor and
directly calls another recovered function that references the class's unique
PE vtable symbol. The target is called an initializer candidate, not a
constructor, because a vtable write plus a factory call does not by itself prove
full constructor semantics.

When a Ghidra export is supplied, the same caller->target edge must also be
present in callgraph.jsonl before the link is independently cross-checked.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from extract_shift_rtti_registry import extract_registry

FORMAT = "SHIFT-FACTORY-INITIALIZER-LINKS/1"
_FUNCTION_START = re.compile(r"\b(FUN_[0-9a-fA-F]+)\s*\([^;{}]*\)\s*\{", re.MULTILINE)
_DIRECT_CALL = re.compile(r"\b(FUN_[0-9a-fA-F]+)\s*\(")
_DAT_SYMBOL = re.compile(r"\b_?(DAT_[0-9a-fA-F]{8})\b")
_VTABLE_SYMBOL = re.compile(r"\b(PTR_FUN_[0-9a-fA-F]{8})\b")


def _extract_functions(text: str) -> dict[str, str]:
    """Extract Ghidra-style FUN_x definitions in one forward pass."""
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
        out.setdefault(name, text[match.start():end])
        cursor = end
    return out


def _function_address(name: str | None) -> str | None:
    if not name or not name.startswith("FUN_"):
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


def _ghidra_edges(root: Path | None) -> set[tuple[str, str]] | None:
    if root is None:
        return None
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing Ghidra callgraph: {path}")
    edges: set[tuple[str, str]] = set()
    for row in _read_jsonl(path):
        source = row.get("from_function")
        target = row.get("to")
        if row.get("indirect") is False and isinstance(source, str) and isinstance(target, str):
            edges.add((source, target))
    return edges


def extract_links(
    source: Path,
    exe: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8", errors="replace")
    functions = _extract_functions(text)
    registry = extract_registry(source, exe)

    direct_calls: dict[str, set[str]] = {}
    descriptor_users: dict[str, set[str]] = defaultdict(set)
    vtable_users: dict[str, set[str]] = defaultdict(set)
    for name, body in functions.items():
        direct_calls[name] = set(_DIRECT_CALL.findall(body))
        for symbol in _DAT_SYMBOL.findall(body):
            descriptor_users[symbol].add(name)
        for symbol in _VTABLE_SYMBOL.findall(body):
            vtable_users[symbol].add(name)

    ghidra_edges = _ghidra_edges(ghidra_export)
    rows: list[dict[str, Any]] = []

    for class_row in registry.get("classes") or []:
        class_name = class_row.get("name")
        descriptor_symbol = class_row.get("descriptor_symbol")
        unique_vtable = class_row.get("unique_vtable")
        if not isinstance(descriptor_symbol, str) or not isinstance(unique_vtable, int):
            continue
        vtable_symbol = f"PTR_FUN_{unique_vtable:08x}"
        writers = set(vtable_users.get(vtable_symbol, ()))
        if not writers:
            continue
        for factory in sorted(descriptor_users.get(descriptor_symbol, ())):
            targets = sorted(direct_calls.get(factory, set()) & writers)
            for target in targets:
                factory_address = _function_address(factory)
                target_address = _function_address(target)
                ghidra_match = None
                if ghidra_edges is not None:
                    ghidra_match = bool(
                        factory_address
                        and target_address
                        and (factory_address, target_address) in ghidra_edges
                    )
                rows.append(
                    {
                        "class": class_name,
                        "descriptor": class_row.get("descriptor"),
                        "descriptor_symbol": descriptor_symbol,
                        "unique_vtable": unique_vtable,
                        "vtable_symbol": vtable_symbol,
                        "factory_function": factory,
                        "factory_address": factory_address,
                        "initializer_candidate": target,
                        "initializer_address": target_address,
                        "source_descriptor_reference": True,
                        "source_direct_call": True,
                        "source_vtable_reference": True,
                        "ghidra_direct_call": ghidra_match,
                        "evidence_kind": (
                            "descriptor-user-direct-call-to-unique-vtable-writer"
                        ),
                    }
                )

    rows.sort(
        key=lambda row: (
            row.get("class") is None,
            row.get("class") or "",
            row["factory_function"],
            row["initializer_candidate"],
        )
    )
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_class[str(row.get("class"))].append(row)

    summaries = []
    for class_name, class_rows in sorted(by_class.items()):
        factories = sorted({row["factory_function"] for row in class_rows})
        initializers = sorted({row["initializer_candidate"] for row in class_rows})
        ghidra_states = [row["ghidra_direct_call"] for row in class_rows]
        summaries.append(
            {
                "class": class_name,
                "link_count": len(class_rows),
                "factory_functions": factories,
                "initializer_candidates": initializers,
                "unambiguous_initializer": (
                    initializers[0] if len(initializers) == 1 else None
                ),
                "all_ghidra_edges_confirmed": (
                    None
                    if ghidra_edges is None
                    else all(state is True for state in ghidra_states)
                ),
            }
        )

    return {
        "format": FORMAT,
        "source": str(source),
        "exe": str(exe),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "class_count": registry.get("class_count"),
        "unique_vtable_count": registry.get("unique_vtable_count"),
        "linked_class_count": len(summaries),
        "link_count": len(rows),
        "unambiguous_initializer_class_count": sum(
            row["unambiguous_initializer"] is not None for row in summaries
        ),
        "ghidra_confirmed_link_count": sum(
            row["ghidra_direct_call"] is True for row in rows
        ),
        "ghidra_mismatch_link_count": sum(
            row["ghidra_direct_call"] is False for row in rows
        ),
        "class_summaries": summaries,
        "links": rows,
        "scope": {
            "constructor_semantics_proven": False,
            "ownership_proven": False,
            "allocation_site_proven": False,
            "heuristic_constructor_export_used": False,
            "heuristic_factory_export_used": False,
            "note": (
                "A target is an initializer candidate because the source factory "
                "references the class descriptor, directly calls it, and the target "
                "references the class's unique PE vtable. Constructor naming requires "
                "additional initialization/lifetime evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, required=True, help="retail SHIFT.exe")
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = extract_links(args.source, args.exe, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"linked classes: {report['linked_class_count']}")
    print(f"links: {report['link_count']}")
    print(
        "unambiguous initializer classes: "
        f"{report['unambiguous_initializer_class_count']}"
    )
    if args.ghidra_export:
        print(f"Ghidra-confirmed links: {report['ghidra_confirmed_link_count']}")
        print(f"Ghidra mismatches: {report['ghidra_mismatch_link_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 1 if report["ghidra_mismatch_link_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
