#!/usr/bin/env python3
"""Build subsystem-scoped manifests from direct SHIFT Ghidra evidence.

Only functions.jsonl, callgraph.jsonl and strings_xrefs.jsonl are used for
semantic promotion. Heuristic vtable/constructor/factory datasets are excluded.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraSubsystemManifest/1"
INDEX_FORMAT = "SHIFT.GhidraSubsystemManifestIndex/1"

ALIASES: dict[str, list[dict[str, Any]]] = {
    "renderer": [
        {
            "address": "0x00854d30",
            "alias": "CMeshPrimitiveType::ApplyVertexDeclaration",
            "strings": ["CMeshPrimitiveType::ApplyVertexDeclaration"],
            "calls": ["0x0082e510"],
        },
        {
            "address": "0x00854da0",
            "alias": "CMeshPrimitiveType::SetVertexBufferAsStreamSource",
            "strings": ["CMeshPrimitiveType::SetVertexBufferAsStreamSource"],
            "calls": ["0x0082e110"],
        },
        {
            "address": "0x00854e10",
            "alias": "CMeshPrimitiveType::SetIndexBufferAsSource",
            "strings": ["CMeshPrimitiveType::SetIndexBufferAsSource"],
            "calls": ["0x0082e110"],
        },
        {
            "address": "0x00854e70",
            "alias": "MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers",
            "strings": ["MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers"],
            "calls": ["0x00830f80", "0x00853c40"],
        },
        {
            "address": "0x00856030",
            "alias": "CInstancedMeshPrimitiveType::ApplyVertexDeclaration",
            "strings": ["CInstancedMeshPrimitiveType::ApplyVertexDeclaration"],
            "calls": ["0x0082e510"],
        },
        {
            "address": "0x00856750",
            "alias": "CLightweightMeshPrimitiveType::ApplyVertexDeclaration",
            "strings": ["CLightweightMeshPrimitiveType::ApplyVertexDeclaration"],
            "calls": ["0x0082e510"],
        },
        {
            "address": "0x008587e0",
            "alias": "MWL::Renderer::WinRenderer::CMeshPrimitiveType::LoadXMLMeshFromResource",
            "strings": ["MWL::Renderer::WinRenderer::CMeshPrimitiveType::LoadXMLMeshFromResource"],
            "calls": [],
        },
    ],
    "physics": [
        {
            "address": "0x0074ddc3",
            "alias": "MWL::Core::PhysicsParticipant::Restart",
            "strings": ["MWL::Core::PhysicsParticipant::Restart"],
            "calls": [],
        },
        {
            "address": "0x00750080",
            "alias": "MWL::Core::LoadCollisionStream",
            "strings": ["MWL::Core::LoadCollisionStream"],
            "calls": [],
        },
        {
            "address": "0x007506b0",
            "alias": "MWL::Core::PhysicsInit",
            "strings": ["MWL::Core::PhysicsInit"],
            "calls": [],
        },
    ],
    "vehicle": [
        {
            "address": "0x00798df0",
            "alias": "MWL::Core::Vehicle::InitVehicle",
            "strings": ["MWL::Core::Vehicle::InitVehicle"],
            "calls": [],
        },
    ],
    "scene_graph": [
        {
            "address": "0x0068ba9e",
            "alias": "MWL::GraphicsEngine::CSceneGraph::AddUpdate",
            "strings": ["MWL::GraphicsEngine::CSceneGraph::AddUpdate"],
            "calls": [],
        },
    ],
}

AI_REGISTRATIONS = [
    ("0x00a84220", "AIPolylinePath"),
    ("0x00a84460", "AISpline"),
    ("0x00a844f0", "AISplineInfo"),
    ("0x00a84580", "AISegmentPath"),
    ("0x00a84610", "AIPolyPathNode"),
    ("0x00a846a0", "AIPathNode"),
    ("0x00a84730", "AIPath"),
    ("0x00a847b0", "AIMarker"),
    ("0x00a84840", "AICamera"),
    ("0x00a848d0", "AISmartObjectBase"),
    ("0x00a84960", "AISmartObjectObj"),
]
AI_REQUIRED_CALLS = {"0x00631740", "0x00630fe0", "0x006310c0", "0x00900fb3"}


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


def build_indexes(root: Path):
    required = ["binary.json", "manifest.json", "functions.jsonl", "callgraph.jsonl", "strings_xrefs.jsonl"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required export files: " + ", ".join(missing))

    functions = {row["address"]: row for row in read_jsonl(root / "functions.jsonl")}
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        target = row.get("to")
        if isinstance(source, str):
            outgoing[source].append(row)
        if isinstance(target, str):
            incoming[target].append(row)

    strings_by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "strings_xrefs.jsonl"):
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function[function].append(row)

    return (
        read_json(root / "binary.json"),
        read_json(root / "manifest.json"),
        functions,
        outgoing,
        incoming,
        strings_by_function,
    )


def direct_targets(edges: list[dict[str, Any]]) -> set[str]:
    return {
        row["to"]
        for row in edges
        if row.get("indirect") is False and isinstance(row.get("to"), str)
    }


def promote_alias(spec, functions, outgoing, strings_by_function):
    address = spec["address"]
    values = {
        row.get("value")
        for row in strings_by_function.get(address, [])
        if isinstance(row.get("value"), str)
    }
    targets = direct_targets(outgoing.get(address, []))
    string_checks = {value: value in values for value in spec["strings"]}
    call_checks = {target: target in targets for target in spec["calls"]}
    promoted = address in functions and all(string_checks.values()) and all(call_checks.values())
    return {
        "address": address,
        "ghidra_name": (functions.get(address) or {}).get("name"),
        "alias": spec["alias"],
        "promoted": promoted,
        "evidence_kind": "exact-string-plus-callshape" if spec["calls"] else "exact-string-xref",
        "checks": {
            "function_present": address in functions,
            "strings": string_checks,
            "direct_calls": call_checks,
        },
    }


def edge_slice(addresses: set[str], outgoing, incoming):
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for address in sorted(addresses):
        for row in outgoing.get(address, []) + incoming.get(address, []):
            if row.get("indirect") is not False:
                continue
            key = (row.get("from_function"), row.get("instruction"), row.get("to"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows.sort(key=lambda row: (str(row.get("from_function")), str(row.get("instruction"))))
    return rows


def ai_manifest(functions, outgoing, incoming, strings_by_function):
    registrations = []
    for address, class_name in AI_REGISTRATIONS:
        values = {
            row.get("value")
            for row in strings_by_function.get(address, [])
            if isinstance(row.get("value"), str)
        }
        targets = direct_targets(outgoing.get(address, []))
        checks = {
            "function_present": address in functions,
            "class_string": class_name in values,
            "registration_call_shape": AI_REQUIRED_CALLS.issubset(targets),
        }
        registrations.append(
            {
                "address": address,
                "ghidra_name": (functions.get(address) or {}).get("name"),
                "class_name": class_name,
                "kind": "class-registration-stub",
                "promoted": all(checks.values()),
                "checks": checks,
            }
        )
    addresses = {row["address"] for row in registrations if row["promoted"]}
    return {
        "format": FORMAT,
        "subsystem": "ai",
        "semantic_aliases": [],
        "class_registrations": registrations,
        "direct_call_edges": edge_slice(addresses, outgoing, incoming),
        "scope": {
            "semantic_function_aliases_assigned": False,
            "note": "AI class strings identify registration stubs; they are not promoted to constructors or runtime method names.",
        },
    }


def build(root: Path) -> dict[str, Any]:
    binary, export_manifest, functions, outgoing, incoming, strings_by_function = build_indexes(root)
    manifests: dict[str, Any] = {}
    all_aliases = []

    for subsystem, specs in ALIASES.items():
        checks = [promote_alias(spec, functions, outgoing, strings_by_function) for spec in specs]
        promoted = [row for row in checks if row["promoted"]]
        addresses = {row["address"] for row in promoted}
        all_aliases.extend({**row, "subsystem": subsystem} for row in promoted)
        manifests[subsystem] = {
            "format": FORMAT,
            "subsystem": subsystem,
            "semantic_aliases": checks,
            "class_registrations": [],
            "direct_call_edges": edge_slice(addresses, outgoing, incoming),
            "scope": {
                "heuristic_vtables_used": False,
                "heuristic_constructors_used": False,
                "heuristic_factories_used": False,
            },
        }

    manifests["ai"] = ai_manifest(functions, outgoing, incoming, strings_by_function)

    source = {
        "program": binary.get("program_name") or export_manifest.get("program"),
        "executable_md5": binary.get("executable_md5"),
        "language_id": binary.get("language_id"),
        "image_base": binary.get("image_base"),
        "pointer_size": binary.get("pointer_size"),
        "export_counts": export_manifest.get("counts"),
    }
    for manifest in manifests.values():
        manifest["source"] = source

    return {
        "format": INDEX_FORMAT,
        "source": source,
        "subsystems": manifests,
        "semantic_aliases": sorted(all_aliases, key=lambda row: row["address"]),
    }


def write_bundle(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, manifest in report["subsystems"].items():
        (output_dir / f"{name}.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    index = {key: value for key, value in report.items() if key != "subsystems"}
    index["files"] = [f"{name}.json" for name in sorted(report["subsystems"])]
    (output_dir / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    report = build(args.export_dir)
    write_bundle(report, args.output_dir)

    failed = []
    for subsystem, manifest in report["subsystems"].items():
        for row in manifest["semantic_aliases"]:
            if not row["promoted"]:
                failed.append(f"{subsystem}: {row['address']} {row['alias']}")
        for row in manifest["class_registrations"]:
            if not row["promoted"]:
                failed.append(f"{subsystem}: {row['address']} register {row['class_name']}")

    print(f"format: {report['format']}")
    print(f"program: {report['source']['program']}")
    print(f"semantic aliases: {len(report['semantic_aliases'])}")
    print(
        "AI registrations: "
        + str(sum(1 for row in report["subsystems"]["ai"]["class_registrations"] if row["promoted"]))
    )
    if failed:
        for item in failed:
            print("FAIL", item)
        return 1
    print("subsystem manifests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
