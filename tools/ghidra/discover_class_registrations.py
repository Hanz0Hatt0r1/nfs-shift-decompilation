#!/usr/bin/env python3
"""Discover SHIFT class-registration stubs from direct Ghidra evidence.

This tool deliberately does not use the heuristic vtable/constructor/factory
exports. A registration candidate must have the direct call shape observed in
the retail class registry and is then associated with exact string xrefs from
the same function. An optional SHIFT-CLASS-MANIFEST/1 report can be supplied to
cross-check the Ghidra discovery in the opposite direction.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraClassRegistrationDiscovery/1"
REGISTRATION_CALLS = {
    "0x00631740",
    "0x00630fe0",
    "0x006310c0",
    "0x00900fb3",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
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


def normalize_function_address(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("FUN_") or value.startswith("thunk_FUN_"):
        value = value.rsplit("FUN_", 1)[-1]
    elif value.startswith("0x"):
        value = value[2:]
    else:
        return None
    try:
        return f"0x{int(value, 16):08x}"
    except ValueError:
        return None


def build_indexes(root: Path):
    required = [
        "binary.json",
        "manifest.json",
        "functions.jsonl",
        "callgraph.jsonl",
        "strings_xrefs.jsonl",
    ]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required export files: " + ", ".join(missing))

    functions = {row["address"]: row for row in read_jsonl(root / "functions.jsonl")}
    calls: dict[str, set[str]] = defaultdict(set)
    call_edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        target = row.get("to")
        if row.get("indirect") is False and isinstance(source, str) and isinstance(target, str):
            calls[source].add(target)
            call_edges[source].append(row)

    strings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "strings_xrefs.jsonl"):
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings[function].append(row)

    return (
        read_json(root / "binary.json"),
        read_json(root / "manifest.json"),
        functions,
        calls,
        call_edges,
        strings,
    )


def discover(root: Path, class_manifest: Path | None = None) -> dict[str, Any]:
    binary, export_manifest, functions, calls, call_edges, strings = build_indexes(root)

    candidates = []
    for address, targets in calls.items():
        if not REGISTRATION_CALLS.issubset(targets):
            continue
        function = functions.get(address) or {}
        values = sorted(
            {
                row.get("value")
                for row in strings.get(address, [])
                if isinstance(row.get("value"), str) and row.get("value")
            }
        )
        candidates.append(
            {
                "address": address,
                "ghidra_name": function.get("name"),
                "size": function.get("size"),
                "mnemonic_sha256": function.get("mnemonic_sha256"),
                "strings": values,
                "single_string_name": values[0] if len(values) == 1 else None,
                "registration_call_shape": True,
                "required_calls": sorted(REGISTRATION_CALLS),
                "direct_call_edges": sorted(
                    call_edges.get(address, []),
                    key=lambda row: str(row.get("instruction")),
                ),
            }
        )
    candidates.sort(key=lambda row: row["address"])

    fingerprint_counts = Counter(
        row["mnemonic_sha256"]
        for row in candidates
        if isinstance(row.get("mnemonic_sha256"), str)
    )

    comparison = None
    if class_manifest is not None:
        manifest = read_json(class_manifest)
        if manifest.get("format") != "SHIFT-CLASS-MANIFEST/1":
            raise ValueError(f"{class_manifest}: expected SHIFT-CLASS-MANIFEST/1")
        discovered = {row["address"]: row for row in candidates}
        rows = []
        for class_row in manifest.get("classes") or []:
            class_name = class_row.get("name")
            address = normalize_function_address(class_row.get("registration_function"))
            candidate = discovered.get(address) if address else None
            exact_name_match = bool(
                candidate is not None
                and isinstance(class_name, str)
                and class_name in candidate["strings"]
            )
            rows.append(
                {
                    "class": class_name,
                    "registration_function": class_row.get("registration_function"),
                    "address": address,
                    "ghidra_candidate_found": candidate is not None,
                    "exact_class_string_found": exact_name_match,
                    "verified": candidate is not None and exact_name_match,
                    "ghidra_strings": candidate["strings"] if candidate else [],
                    "mnemonic_sha256": candidate.get("mnemonic_sha256") if candidate else None,
                }
            )
        manifest_addresses = {row["address"] for row in rows if row["address"]}
        extras = [row for row in candidates if row["address"] not in manifest_addresses]
        comparison = {
            "class_manifest": str(class_manifest),
            "class_count": len(rows),
            "verified_count": sum(row["verified"] for row in rows),
            "missing_candidate_count": sum(not row["ghidra_candidate_found"] for row in rows),
            "name_mismatch_count": sum(
                row["ghidra_candidate_found"] and not row["exact_class_string_found"]
                for row in rows
            ),
            "extra_ghidra_candidate_count": len(extras),
            "rows": rows,
            "extra_ghidra_candidates": extras,
        }

    return {
        "format": FORMAT,
        "source": {
            "program": binary.get("program_name") or export_manifest.get("program"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": binary.get("pointer_size"),
        },
        "method": {
            "required_direct_calls": sorted(REGISTRATION_CALLS),
            "uses_heuristic_vtables": False,
            "uses_heuristic_constructors": False,
            "uses_heuristic_factories": False,
            "name_policy": (
                "exact string xrefs are reported; a single string is not treated "
                "as a constructor or runtime-method name"
            ),
        },
        "candidate_count": len(candidates),
        "single_string_candidate_count": sum(
            row["single_string_name"] is not None for row in candidates
        ),
        "fingerprint_clusters": [
            {"mnemonic_sha256": fingerprint, "count": count}
            for fingerprint, count in sorted(
                fingerprint_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "candidates": candidates,
        "class_manifest_comparison": comparison,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("--class-manifest", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = discover(args.export_dir, args.class_manifest)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"registration candidates: {report['candidate_count']}")
    print(f"single-string candidates: {report['single_string_candidate_count']}")
    comparison = report["class_manifest_comparison"]
    if comparison is not None:
        print(f"class manifest verified: {comparison['verified_count']}/{comparison['class_count']}")
        print(f"missing candidates: {comparison['missing_candidate_count']}")
        print(f"name mismatches: {comparison['name_mismatch_count']}")
        print(f"extra Ghidra candidates: {comparison['extra_ghidra_candidate_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
