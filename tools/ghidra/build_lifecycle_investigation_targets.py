#!/usr/bin/env python3
"""Build one-hop Ghidra slices for lifecycle-investigation-ready SHIFT classes."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.LifecycleInvestigationTargets/1"
SCORECARD_FORMAT = "SHIFT-CLASS-EVIDENCE-SCORECARD/1"
_FUN_NAME = re.compile(r"^FUN_([0-9a-fA-F]{8})$")


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


def _fun_address(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    match = _FUN_NAME.fullmatch(name)
    if match is None:
        return None
    return "0x" + match.group(1).lower()


def _load_ghidra(root: Path):
    required = ["functions.jsonl", "callgraph.jsonl", "strings_xrefs.jsonl"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing Ghidra export files: " + ", ".join(missing))

    functions = {
        row["address"]: row
        for row in _read_jsonl(root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is not False:
            continue
        source = row.get("from_function")
        target = row.get("to")
        if isinstance(source, str):
            outgoing[source].append(row)
        if isinstance(target, str):
            incoming[target].append(row)

    strings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings[function].append(row)

    return functions, outgoing, incoming, strings


def _edge_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
    }


def _function_slice(address, functions, outgoing, incoming, strings):
    function = functions.get(address) if isinstance(address, str) else None
    return {
        "address": address,
        "present": function is not None,
        "ghidra_name": function.get("name") if function else None,
        "size": function.get("size") if function else None,
        "calling_convention": function.get("calling_convention") if function else None,
        "signature": function.get("signature") if function else None,
        "mnemonic_sha256": function.get("mnemonic_sha256") if function else None,
        "strings": sorted(
            {
                row.get("value")
                for row in strings.get(address, [])
                if isinstance(row.get("value"), str)
            }
        ) if isinstance(address, str) else [],
        "outgoing_direct_calls": [
            _edge_view(row) for row in outgoing.get(address, [])
        ] if isinstance(address, str) else [],
        "incoming_direct_calls": [
            _edge_view(row) for row in incoming.get(address, [])
        ] if isinstance(address, str) else [],
    }


def build_targets(
    scorecard_path: Path,
    ghidra_export: Path,
    prefixes: list[str] | None = None,
    top: int | None = None,
) -> dict[str, Any]:
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    if scorecard.get("format") != SCORECARD_FORMAT:
        raise ValueError(f"{scorecard_path}: expected {SCORECARD_FORMAT}")
    functions, outgoing, incoming, strings = _load_ghidra(ghidra_export)

    selected = [
        row
        for row in scorecard.get("rows") or []
        if row.get("evidence_tier") == "lifecycle-investigation-ready"
    ]
    if prefixes:
        selected = [
            row
            for row in selected
            if any((row.get("class_name") or "").startswith(prefix) for prefix in prefixes)
        ]
    if top is not None:
        selected = selected[:top]

    targets: list[dict[str, Any]] = []
    for row in selected:
        initializer_name = row.get("unambiguous_initializer")
        initializer_address = _fun_address(initializer_name)
        registration_address = row.get("ghidra_registration_address")
        initializer = _function_slice(
            initializer_address, functions, outgoing, incoming, strings
        )
        registration = _function_slice(
            registration_address, functions, outgoing, incoming, strings
        )
        checks = {
            "scorecard_lifecycle_ready": True,
            "initializer_name_resolved": initializer_address is not None,
            "initializer_present_in_ghidra": initializer["present"],
            "registration_address_present": isinstance(registration_address, str),
            "registration_present_in_ghidra": registration["present"],
        }
        targets.append(
            {
                "class_name": row.get("class_name"),
                "descriptor": row.get("descriptor"),
                "parent_class": row.get("parent_class"),
                "field_count": row.get("field_count"),
                "unique_vtable": row.get("unique_vtable"),
                "initializer_candidate": initializer_name,
                "initializer": initializer,
                "registration": registration,
                "checks": checks,
                "slice_complete": all(checks.values()),
            }
        )

    return {
        "format": FORMAT,
        "source_scorecard": str(scorecard_path),
        "ghidra_export": str(ghidra_export),
        "target_count": len(targets),
        "complete_slice_count": sum(row["slice_complete"] for row in targets),
        "incomplete_slice_count": sum(not row["slice_complete"] for row in targets),
        "targets": targets,
        "scope": {
            "callgraph_depth": 1,
            "direct_calls_only": True,
            "destructor_identity_inferred": False,
            "constructor_identity_inferred": False,
            "note": (
                "Targets are selected from the scorecard's lifecycle-investigation-ready "
                "tier. The Ghidra slice only exposes immediate static context around the "
                "registration and initializer candidate; it does not infer lifecycle roles "
                "for neighboring functions."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scorecard", type=Path)
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--prefix", action="append", default=[])
    parser.add_argument("--top", type=int)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if args.top is not None and args.top < 1:
        parser.error("--top must be >= 1")
    report = build_targets(args.scorecard, args.ghidra_export, args.prefix, args.top)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"targets: {report['target_count']}")
    print(f"complete slices: {report['complete_slice_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 1 if report["incomplete_slice_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
