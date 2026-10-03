#!/usr/bin/env python3
"""Join exact method-name anchors to already proven Ghidra subsystem slices.

This layer deliberately requires two independent signals before a method-name
candidate is promoted into a subsystem-specific candidate:

1. the exact unique method-name string maps to a narrow namespace/class prefix;
2. the containing function is already present in that subsystem's direct
   evidence slice (promoted aliases/registrations plus their one-hop direct-call
   endpoints).

Namespace-only and slice-only observations remain visible but are not promoted.
Ambiguous functions from the method-anchor inventory are never promoted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_subsystem_manifests import build as build_subsystem_manifests
from discover_method_name_anchors import discover_method_name_anchors

FORMAT = "SHIFT.GhidraSubsystemMethodAnchors/1"

# Narrow, reviewable rules.  Broad MWL::Core::* is intentionally not assigned.
SUBSYSTEM_PREFIXES: dict[str, tuple[str, ...]] = {
    "renderer": (
        "MWL::Renderer::",
    ),
    "physics": (
        "MWL::Physics::",
        "MWL::Core::Physics",
        "MWL::Core::cPhysics",
        "MWL::Core::LoadCollision",
    ),
    "vehicle": (
        "MWL::Vehicle::",
        "MWL::Core::Vehicle",
    ),
    "scene_graph": (
        "MWL::GraphicsEngine::CSceneGraph::",
    ),
    "ai": (
        "MWL::AI::",
    ),
}


def _namespace_subsystem(method_name: str) -> str | None:
    matches = [
        subsystem
        for subsystem, prefixes in SUBSYSTEM_PREFIXES.items()
        if any(method_name.startswith(prefix) for prefix in prefixes)
    ]
    return matches[0] if len(matches) == 1 else None


def _subsystem_slice_addresses(manifest: dict[str, Any]) -> set[str]:
    addresses: set[str] = set()
    for row in manifest.get("semantic_aliases") or []:
        if row.get("promoted") is True and isinstance(row.get("address"), str):
            addresses.add(row["address"])
    for row in manifest.get("class_registrations") or []:
        if row.get("promoted") is True and isinstance(row.get("address"), str):
            addresses.add(row["address"])
    for edge in manifest.get("direct_call_edges") or []:
        source = edge.get("from_function")
        target = edge.get("to")
        if isinstance(source, str):
            addresses.add(source)
        if isinstance(target, str):
            addresses.add(target)
    return addresses


def _slice_memberships(address: str, slices: dict[str, set[str]]) -> list[str]:
    return sorted(subsystem for subsystem, members in slices.items() if address in members)


def join_method_anchors_to_subsystems(root: Path) -> dict[str, Any]:
    subsystem_report = build_subsystem_manifests(root)
    anchor_report = discover_method_name_anchors(root)
    subsystem_manifests = subsystem_report["subsystems"]
    slices = {
        subsystem: _subsystem_slice_addresses(manifest)
        for subsystem, manifest in subsystem_manifests.items()
    }

    unique_rows: list[dict[str, Any]] = []
    ambiguous_rows: list[dict[str, Any]] = []

    for row in anchor_report.get("functions") or []:
        address = row.get("address")
        if not isinstance(address, str):
            continue
        memberships = _slice_memberships(address, slices)
        candidate = row.get("unique_method_name_candidate")
        if isinstance(candidate, str):
            namespace_subsystem = _namespace_subsystem(candidate)
            promoted_subsystem = (
                namespace_subsystem
                if namespace_subsystem is not None and namespace_subsystem in memberships
                else None
            )
            if promoted_subsystem is not None:
                status = "subsystem-crosschecked-method-name-candidate"
            elif namespace_subsystem is not None:
                status = "namespace-only-method-name-candidate"
            elif memberships:
                status = "slice-only-unclassified-method-name-candidate"
            else:
                status = "unclassified-method-name-candidate"
            unique_rows.append(
                {
                    "address": address,
                    "ghidra_name": row.get("name"),
                    "method_name": candidate,
                    "namespace_subsystem": namespace_subsystem,
                    "slice_memberships": memberships,
                    "promoted_subsystem": promoted_subsystem,
                    "promoted": promoted_subsystem is not None,
                    "status": status,
                    "calling_convention": row.get("calling_convention"),
                    "size": row.get("size"),
                    "mnemonic_sha256": row.get("mnemonic_sha256"),
                    "anchor_string_addresses": row.get("anchor_string_addresses") or [],
                }
            )
            continue

        anchors = [
            value
            for value in (row.get("method_anchors") or [])
            if isinstance(value, str)
        ]
        namespace_subsystems = sorted(
            {
                subsystem
                for value in anchors
                if (subsystem := _namespace_subsystem(value)) is not None
            }
        )
        ambiguous_rows.append(
            {
                "address": address,
                "ghidra_name": row.get("name"),
                "method_anchors": anchors,
                "namespace_subsystems": namespace_subsystems,
                "slice_memberships": memberships,
                "promoted": False,
                "status": "ambiguous-method-name-anchors",
            }
        )

    unique_rows.sort(key=lambda row: (row["address"], row["method_name"]))
    ambiguous_rows.sort(key=lambda row: row["address"])

    subsystem_rows: dict[str, dict[str, Any]] = {}
    for subsystem in sorted(subsystem_manifests):
        promoted = [
            row for row in unique_rows if row["promoted_subsystem"] == subsystem
        ]
        namespace_only = [
            row
            for row in unique_rows
            if row["namespace_subsystem"] == subsystem and row["promoted"] is False
        ]
        ambiguous = [
            row
            for row in ambiguous_rows
            if subsystem in row["namespace_subsystems"]
            or subsystem in row["slice_memberships"]
        ]
        subsystem_rows[subsystem] = {
            "slice_address_count": len(slices[subsystem]),
            "promoted_method_name_candidate_count": len(promoted),
            "namespace_only_candidate_count": len(namespace_only),
            "ambiguous_function_count": len(ambiguous),
            "promoted_method_name_candidates": promoted,
            "namespace_only_candidates": namespace_only,
            "ambiguous_functions": ambiguous,
        }

    promoted_rows = [row for row in unique_rows if row["promoted"]]
    namespace_only_rows = [
        row
        for row in unique_rows
        if row["namespace_subsystem"] is not None and row["promoted"] is False
    ]
    slice_only_rows = [
        row
        for row in unique_rows
        if row["namespace_subsystem"] is None and row["slice_memberships"]
    ]

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": subsystem_report.get("source"),
        "method_anchor_format": anchor_report.get("format"),
        "subsystem_manifest_format": subsystem_report.get("format"),
        "unique_method_name_candidate_count": len(unique_rows),
        "promoted_method_name_candidate_count": len(promoted_rows),
        "namespace_only_candidate_count": len(namespace_only_rows),
        "slice_only_unclassified_candidate_count": len(slice_only_rows),
        "ambiguous_method_anchor_function_count": len(ambiguous_rows),
        "subsystems": subsystem_rows,
        "unique_candidates": unique_rows,
        "ambiguous_functions": ambiguous_rows,
        "scope": {
            "exact_method_string_required": True,
            "unique_method_anchor_required": True,
            "namespace_rule_required": True,
            "existing_subsystem_slice_required_for_promotion": True,
            "ambiguous_functions_promoted": False,
            "automatic_function_renaming_performed": False,
            "method_behavior_proven": False,
            "abi_proven": False,
            "note": (
                "Promotion means a unique exact method-name string agrees with a narrow "
                "namespace/class rule and the containing function already belongs to an "
                "independently established one-hop subsystem evidence slice. This is a "
                "semantic-name candidate only; it does not rename the binary or prove "
                "complete method behavior/ABI."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = join_method_anchors_to_subsystems(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"unique method-name candidates: {report['unique_method_name_candidate_count']}")
    print(f"subsystem-crosschecked candidates: {report['promoted_method_name_candidate_count']}")
    print(f"namespace-only candidates: {report['namespace_only_candidate_count']}")
    print(f"ambiguous functions: {report['ambiguous_method_anchor_function_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
