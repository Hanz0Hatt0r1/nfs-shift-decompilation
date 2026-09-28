"""Enumerate packed-workspace logical-address aliases for specialized providers.

The specialized provider row-pointer bases are storage anchors, but the packed
workspace does not provide a one-to-one mapping from (row, scalar-column) to
absolute address when every logical column is hypothetically enumerated. This
module makes those collisions explicit.

It is an evidence map only: an alias class does not assign ownership to any
particular logical matrix cell.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderWorkspaceAliasRuntime/1"


def enumerate_candidate_addresses(
    row_pointers: Iterable[int],
    scalar_count: int,
    workspace_start: int,
    workspace_end: int,
) -> dict[int, tuple[tuple[int, int], ...]]:
    """Map each in-range absolute workspace address to candidate (row,column)s."""
    pointers = tuple(int(value) for value in row_pointers)
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")

    addresses: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for row, base in enumerate(pointers):
        if row >= n:
            break
        for column in range(n):
            address = base + column * 8
            if workspace_start <= address < workspace_end:
                addresses[address].append((row, column))

    return {
        address: tuple(cells)
        for address, cells in sorted(addresses.items())
    }


def build_alias_map(provider_id: int) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    mapping = enumerate_candidate_addresses(
        pointers,
        layout.scalar_count,
        layout.factor_workspace_base,
        layout.output_vector_base,
    )

    collision_classes = {
        address: cells
        for address, cells in mapping.items()
        if len(cells) > 1
    }
    alias_entries = sum(len(cells) - 1 for cells in collision_classes.values())

    diagonal_entries = [
        {
            "pivot_index": index,
            "row_pointer": hex(base),
            "diagonal_address": hex(base + index * 8),
        }
        for index, base in enumerate(pointers[: layout.scalar_count])
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "workspace": {
            "start": hex(layout.factor_workspace_base),
            "end": hex(layout.output_vector_base),
            "bytes": layout.factor_workspace_bytes,
            "doubles": layout.factor_workspace_doubles,
        },
        "candidate_cell_count": layout.scalar_count * layout.scalar_count,
        "unique_storage_addresses": len(mapping),
        "collision_address_count": len(collision_classes),
        "alias_entry_count": alias_entries,
        "collision_classes": [
            {
                "address": hex(address),
                "cells": [
                    {"row": row, "column": column}
                    for row, column in cells
                ],
            }
            for address, cells in collision_classes.items()
        ],
        "diagonal_entries": diagonal_entries,
        "ready": True,
        "errors": [],
    }


def summarize_alias_map(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "candidate_cell_count": report.get("candidate_cell_count"),
        "unique_storage_addresses": report.get("unique_storage_addresses"),
        "collision_address_count": report.get("collision_address_count"),
        "alias_entry_count": report.get("alias_entry_count"),
        "diagonal_count": len(report.get("diagonal_entries") or []),
        "ready": bool(report.get("ready")),
    }


def validate_alias_map(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    diagonal_entries = report.get("diagonal_entries") or []

    if len(diagonal_entries) != scalar_count:
        errors.append(
            f"diagonal-count:expected={scalar_count}:actual={len(diagonal_entries)}"
        )

    start = int(str(report["workspace"]["start"]), 16)
    end = int(str(report["workspace"]["end"]), 16)

    for entry in diagonal_entries:
        address = int(str(entry["diagonal_address"]), 16)
        if not (start <= address < end):
            errors.append(
                f"pivot-{entry['pivot_index']}-diagonal-outside-workspace"
            )

    for collision in report.get("collision_classes") or []:
        cells = collision.get("cells") or []
        if len(cells) < 2:
            errors.append(
                f"collision-{collision.get('address')}-has-fewer-than-two-cells"
            )
        for cell in cells:
            row = int(cell["row"])
            column = int(cell["column"])
            if row < 0 or row >= scalar_count:
                errors.append(f"collision-{collision.get('address')}-row-out-of-range")
            if column < 0 or column >= scalar_count:
                errors.append(
                    f"collision-{collision.get('address')}-column-out-of-range"
                )

    return {
        "format": "SHIFT.SpecializedProviderWorkspaceAliasValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "collision_address_count": len(report.get("collision_classes") or []),
    }


def build_workspace_alias_contract() -> dict[str, Any]:
    providers = []
    for provider_id in (0, 1):
        report = build_alias_map(provider_id)
        report["summary"] = summarize_alias_map(report)
        report["validation"] = validate_alias_map(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "specialized_provider_row_storage_runtime.py / PE provider accessors",
        "providers": providers,
        "scope": {
            "representation": "absolute-address -> candidate logical (row,column) aliases",
            "candidate_domain": "all scalar_count × scalar_count row/column pairs whose computed address lies inside the factor workspace",
            "ownership": "unresolved",
        },
        "limitations": [
            "The candidate logical domain is intentionally hypothetical; it does not assert that every row/column pair is semantically populated.",
            "Collision classes describe address reuse in the packed layout and do not decide which logical interpretation is active at a source site.",
            "Diagonal addresses are validated as in-range storage locations but no semantic matrix meaning is inferred.",
        ],
        "status": "source-backed-packed-workspace-alias-map",
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int, choices=(0, 1), default=None)
    args = parser.parse_args()

    if args.provider is None:
        contract = build_workspace_alias_contract()
        ready = all(
            provider["validation"]["ready"]
            for provider in contract["providers"]
        )
        print(json.dumps(contract, indent=2, sort_keys=True))
    else:
        report = build_alias_map(args.provider)
        report["summary"] = summarize_alias_map(report)
        report["validation"] = validate_alias_map(report)
        print(json.dumps(report, indent=2, sort_keys=True))
        ready = report["validation"]["ready"]

    raise SystemExit(0 if ready else 2)
