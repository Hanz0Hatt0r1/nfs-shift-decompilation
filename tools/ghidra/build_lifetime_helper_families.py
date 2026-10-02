#!/usr/bin/env python3
"""Aggregate recurring create/release helper pairs across recovered classes.

The input already contains paired create/delete source evidence.  This builder
only groups unambiguous helper pairs and optionally attaches direct Ghidra
function/callgraph context.  Recurrence is discovery evidence for a shared
lifetime helper family; it does not assign allocator/free ABI semantics.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1"
PAIR_FORMAT = "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"


def _load_pair(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != PAIR_FORMAT:
        raise ValueError(f"{path}: expected {PAIR_FORMAT}")
    return report


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


def _address(function: str | None) -> str | None:
    if not isinstance(function, str) or not function.startswith("FUN_"):
        return None
    try:
        return f"0x{int(function[4:], 16):08x}"
    except ValueError:
        return None


def _load_ghidra(root: Path | None) -> dict[str, Any] | None:
    if root is None:
        return None
    functions_path = root / "functions.jsonl"
    callgraph_path = root / "callgraph.jsonl"
    missing = [
        str(path.name)
        for path in (functions_path, callgraph_path)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "missing required Ghidra files: " + ", ".join(missing)
        )

    functions = {
        row["address"]: row
        for row in _read_jsonl(functions_path)
        if isinstance(row.get("address"), str)
    }
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(callgraph_path):
        source = row.get("from_function")
        target = row.get("to")
        if (
            row.get("indirect") is False
            and isinstance(source, str)
            and isinstance(target, str)
        ):
            outgoing[source].append(
                {
                    "instruction": row.get("instruction"),
                    "target": target,
                    "target_name": row.get("to_name"),
                }
            )
    for rows in outgoing.values():
        rows.sort(key=lambda row: (row.get("instruction") or "", row["target"]))
    return {"functions": functions, "outgoing": dict(outgoing)}


def _function_context(function: str, ghidra: dict[str, Any] | None) -> dict[str, Any] | None:
    if ghidra is None:
        return None
    address = _address(function)
    metadata = ghidra["functions"].get(address) if address else None
    return {
        "function": function,
        "address": address,
        "present": metadata is not None,
        "ghidra_name": metadata.get("name") if isinstance(metadata, dict) else None,
        "signature": metadata.get("signature") if isinstance(metadata, dict) else None,
        "calling_convention": (
            metadata.get("calling_convention") if isinstance(metadata, dict) else None
        ),
        "parameters": metadata.get("parameters") if isinstance(metadata, dict) else None,
        "mnemonic_sha256": (
            metadata.get("mnemonic_sha256") if isinstance(metadata, dict) else None
        ),
        "outgoing_direct_calls": list(ghidra["outgoing"].get(address, ())) if address else [],
    }


def build_helper_families(
    pair_path: Path,
    ghidra_export: Path | None = None,
) -> dict[str, Any]:
    pair = _load_pair(pair_path)
    ghidra = _load_ghidra(ghidra_export)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    incomplete_classes: list[dict[str, Any]] = []
    for row in pair.get("classes") or []:
        if row.get("paired_lifetime_shape") is not True:
            continue
        create_helper = row.get("unambiguous_preinitializer_helper")
        release_helper = row.get("unambiguous_release_helper")
        if isinstance(create_helper, str) and isinstance(release_helper, str):
            groups[(create_helper, release_helper)].append(row)
        else:
            incomplete_classes.append(
                {
                    "class_name": row.get("class_name"),
                    "descriptor": row.get("descriptor"),
                    "preinitializer_helpers": row.get("preinitializer_helpers") or [],
                    "release_helpers": row.get("release_helpers") or [],
                    "blocker": "ambiguous_lifetime_helper_pair",
                }
            )

    families: list[dict[str, Any]] = []
    for (create_helper, release_helper), rows in groups.items():
        rows = sorted(
            rows,
            key=lambda row: (
                row.get("class_name") is None,
                row.get("class_name") or "",
                int(row.get("descriptor") or 0),
            ),
        )
        create_context = _function_context(create_helper, ghidra)
        release_context = _function_context(release_helper, ghidra)
        all_classes_ghidra_paired = all(
            row.get("ghidra_paired_lifetime_shape") is True for row in rows
        )
        ghidra_helpers_present = (
            ghidra is not None
            and isinstance(create_context, dict)
            and create_context.get("present") is True
            and isinstance(release_context, dict)
            and release_context.get("present") is True
        )
        literal_argument_sets = sorted({
            tuple(values)
            for row in rows
            for values in (row.get("helper_literal_argument_sets") or [])
        })
        recurrent = len(rows) >= 2
        families.append(
            {
                "create_helper": create_helper,
                "release_helper": release_helper,
                "class_count": len(rows),
                "classes": [row.get("class_name") for row in rows],
                "descriptors": [row.get("descriptor") for row in rows],
                "helper_literal_argument_sets": [
                    list(values) for values in literal_argument_sets
                ],
                "all_classes_ghidra_paired": all_classes_ghidra_paired,
                "ghidra_helpers_present": ghidra_helpers_present,
                "recurrent_helper_pair": recurrent,
                "crosschecked_recurrent_helper_family_candidate": bool(
                    recurrent and all_classes_ghidra_paired and ghidra_helpers_present
                ),
                "create_helper_context": create_context,
                "release_helper_context": release_context,
            }
        )

    families.sort(
        key=lambda row: (
            row["crosschecked_recurrent_helper_family_candidate"] is not True,
            row["recurrent_helper_pair"] is not True,
            -row["class_count"],
            row["create_helper"],
            row["release_helper"],
        )
    )
    incomplete_classes.sort(
        key=lambda row: (
            row.get("class_name") is None,
            row.get("class_name") or "",
            int(row.get("descriptor") or 0),
        )
    )

    return {
        "format": FORMAT,
        "lifetime_pair_evidence": str(pair_path),
        "ghidra_export": str(ghidra_export) if ghidra_export else None,
        "paired_class_count": int(pair.get("paired_lifetime_shape_count") or 0),
        "unambiguous_helper_pair_class_count": sum(
            row["class_count"] for row in families
        ),
        "ambiguous_helper_pair_class_count": len(incomplete_classes),
        "helper_family_count": len(families),
        "recurrent_helper_pair_count": sum(
            row["recurrent_helper_pair"] is True for row in families
        ),
        "crosschecked_recurrent_helper_family_candidate_count": sum(
            row["crosschecked_recurrent_helper_family_candidate"] is True
            for row in families
        ),
        "families": families,
        "ambiguous_classes": incomplete_classes,
        "scope": {
            "allocator_semantics_proven": False,
            "release_semantics_reproven": False,
            "shared_allocator_family_proven": False,
            "argument_semantics_proven": False,
            "note": (
                "Recurrence of the same create/release helper pair across independent "
                "class lifetime shapes is family-discovery evidence. It does not prove "
                "allocator ABI, free ABI, arena identity, or the meaning of literal "
                "helper arguments."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pair", type=Path, help="SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1 JSON")
    parser.add_argument("--ghidra-export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_helper_families(args.pair, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"helper families: {report['helper_family_count']}")
    print(f"recurrent helper pairs: {report['recurrent_helper_pair_count']}")
    print(
        "crosschecked recurrent candidates: "
        f"{report['crosschecked_recurrent_helper_family_candidate_count']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
