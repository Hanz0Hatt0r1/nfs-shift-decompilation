#!/usr/bin/env python3
"""Cross-check high-value static anchors in a SHIFT Ghidra evidence export.

The exporter intentionally contains both direct observations and heuristic
candidate sets.  This analyzer consumes only the direct function/call/string
layers for semantic anchor checks, plus a mnemonic fingerprint cluster for the
known RTTI registration stub shape.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraCrosscheckEvidence/1"

ANCHORS: dict[str, dict[str, Any]] = {
    "mesh_apply_vertex_declaration": {
        "address": "0x00854d30",
        "expected_strings": ["CMeshPrimitiveType::ApplyVertexDeclaration"],
        "expected_calls": ["0x0082e510"],
    },
    "mesh_create_memory_buffers": {
        "address": "0x00854e70",
        "expected_strings": [
            "MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers"
        ],
        "expected_calls": ["0x00830f80", "0x00853c40"],
    },
    "physics_load_collision_stream": {
        "address": "0x00750080",
        "expected_strings": ["MWL::Core::LoadCollisionStream"],
        "expected_calls": [],
    },
    "physics_init": {
        "address": "0x007506b0",
        "expected_strings": ["MWL::Core::PhysicsInit"],
        "expected_calls": [],
    },
    "vehicle_reflection_cluster": {
        "address": "0x00703f10",
        "expected_strings": [
            "Vehicle Chassis",
            "Vehicle Gearbox",
            "Vehicle Suspension",
            "Vehicle Collision",
            "Vehicle Tyres",
        ],
        "expected_calls": ["0x00631740", "0x0063a280", "0x006310c0"],
    },
}

# Four independently named class-registration stubs from the path/AI registry.
REGISTRY_SEEDS = ["0x00a84220", "0x00a84460", "0x00a84580", "0x00a846a0"]
REGISTRY_REQUIRED_CALLS = {
    "0x00631740",  # registration core
    "0x00630fe0",
    "0x006310c0",
    "0x00900fb3",  # atexit
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
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def require_files(root: Path) -> dict[str, Path]:
    names = [
        "binary.json",
        "manifest.json",
        "functions.jsonl",
        "callgraph.jsonl",
        "strings_xrefs.jsonl",
    ]
    result = {name: root / name for name in names}
    missing = [name for name, path in result.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing required export files: " + ", ".join(missing))
    return result


def build_indexes(paths: dict[str, Path]) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    functions = {row["address"]: row for row in read_jsonl(paths["functions.jsonl"])}

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(paths["callgraph.jsonl"]):
        source = row.get("from_function")
        target = row.get("to")
        if isinstance(source, str):
            outgoing[source].append(row)
        if isinstance(target, str):
            incoming[target].append(row)

    strings_by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(paths["strings_xrefs.jsonl"]):
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function[function].append(row)

    return functions, outgoing, incoming, strings_by_function


def anchor_report(
    key: str,
    spec: dict[str, Any],
    functions: dict[str, dict[str, Any]],
    outgoing: dict[str, list[dict[str, Any]]],
    incoming: dict[str, list[dict[str, Any]]],
    strings_by_function: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    address = spec["address"]
    function = functions.get(address)
    strings = strings_by_function.get(address, [])
    string_values = [row.get("value") for row in strings if isinstance(row.get("value"), str)]
    direct_edges = [row for row in outgoing.get(address, []) if row.get("indirect") is False]
    direct_targets = [row.get("to") for row in direct_edges if isinstance(row.get("to"), str)]

    expected_strings = list(spec.get("expected_strings") or [])
    expected_calls = list(spec.get("expected_calls") or [])
    return {
        "key": key,
        "address": address,
        "function": function,
        "string_values": string_values,
        "outgoing_direct_calls": direct_edges,
        "incoming_direct_calls": [row for row in incoming.get(address, []) if row.get("indirect") is False],
        "checks": {
            "function_present": function is not None,
            "expected_strings": {
                value: value in string_values for value in expected_strings
            },
            "expected_calls": {
                value: value in direct_targets for value in expected_calls
            },
        },
    }


def registry_fingerprint_report(
    functions: dict[str, dict[str, Any]],
    outgoing: dict[str, list[dict[str, Any]]],
    strings_by_function: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    seed_rows = [functions.get(address) for address in REGISTRY_SEEDS]
    hashes = {
        row.get("mnemonic_sha256")
        for row in seed_rows
        if isinstance(row, dict) and isinstance(row.get("mnemonic_sha256"), str)
    }
    fingerprint = next(iter(hashes)) if len(hashes) == 1 else None

    matches: list[dict[str, Any]] = []
    if fingerprint is not None:
        for address, row in functions.items():
            if row.get("mnemonic_sha256") != fingerprint:
                continue
            calls = {
                edge.get("to")
                for edge in outgoing.get(address, [])
                if edge.get("indirect") is False and isinstance(edge.get("to"), str)
            }
            strings = [
                item.get("value")
                for item in strings_by_function.get(address, [])
                if isinstance(item.get("value"), str)
            ]
            matches.append(
                {
                    "address": address,
                    "name": row.get("name"),
                    "size": row.get("size"),
                    "calls": sorted(calls),
                    "strings": strings,
                    "has_registration_call_shape": REGISTRY_REQUIRED_CALLS.issubset(calls),
                }
            )

    matches.sort(key=lambda row: row["address"])
    return {
        "seed_addresses": REGISTRY_SEEDS,
        "seed_fingerprints": sorted(value for value in hashes if value),
        "shared_fingerprint": fingerprint,
        "matching_function_count": len(matches),
        "registration_shape_match_count": sum(
            1 for row in matches if row["has_registration_call_shape"]
        ),
        "matches": matches,
    }


def analyze(root: Path) -> dict[str, Any]:
    paths = require_files(root)
    binary = read_json(paths["binary.json"])
    manifest = read_json(paths["manifest.json"])
    functions, outgoing, incoming, strings_by_function = build_indexes(paths)

    anchors = [
        anchor_report(key, spec, functions, outgoing, incoming, strings_by_function)
        for key, spec in ANCHORS.items()
    ]
    registry = registry_fingerprint_report(functions, outgoing, strings_by_function)

    return {
        "format": FORMAT,
        "source": {
            "program": binary.get("program_name") or manifest.get("program"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": binary.get("pointer_size"),
            "export_counts": manifest.get("counts"),
        },
        "anchors": anchors,
        "rtti_registration_fingerprint": registry,
        "scope": {
            "direct_layers": ["functions.jsonl", "callgraph.jsonl", "strings_xrefs.jsonl"],
            "heuristic_vtables_used": False,
            "heuristic_constructors_used": False,
            "note": (
                "Semantic checks are based on direct Ghidra observations. "
                "The generic vtable/constructor candidate datasets are intentionally excluded."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report = analyze(args.export_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failed = []
    for anchor in report["anchors"]:
        checks = anchor["checks"]
        if not checks["function_present"]:
            failed.append(f"{anchor['key']}: function missing")
        failed.extend(
            f"{anchor['key']}: missing string {value!r}"
            for value, ok in checks["expected_strings"].items()
            if not ok
        )
        failed.extend(
            f"{anchor['key']}: missing direct call {value}"
            for value, ok in checks["expected_calls"].items()
            if not ok
        )

    print(f"format: {report['format']}")
    print(f"program: {report['source']['program']}")
    print(
        "registration fingerprint matches: "
        f"{report['rtti_registration_fingerprint']['matching_function_count']}"
    )
    if failed:
        for item in failed:
            print("FAIL", item)
        return 1
    print("anchor checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
