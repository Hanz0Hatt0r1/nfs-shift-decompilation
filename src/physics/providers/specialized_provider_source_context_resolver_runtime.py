"""Resolve specialized-provider workspace cells using explicit source context.

Phase 449 turns the Phase 448 alias map into a practical resolver. An absolute
workspace address may have multiple hypothetical logical owners, so direct
addresses return all candidates. A loop/array source form with an explicit
current row-pointer base and local_10 index resolves to one coordinate.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_workspace_alias_runtime import (
    enumerate_candidate_addresses,
)

FORMAT = "SHIFT.SpecializedProviderSourceContextResolverRuntime/1"


def _candidate_map(provider_id: int) -> dict[int, tuple[tuple[int, int], ...]]:
    layout = get_storage_layout(provider_id)
    return enumerate_candidate_addresses(
        get_row_pointers(provider_id),
        layout.scalar_count,
        layout.factor_workspace_base,
        layout.output_vector_base,
    )


def row_for_pointer(provider_id: int, row_pointer: int) -> int:
    pointers = get_row_pointers(provider_id)
    try:
        return pointers.index(int(row_pointer))
    except ValueError as exc:
        raise ValueError(
            f"row pointer {hex(int(row_pointer))} is not registered"
        ) from exc


def resolve_loop_cell(
    provider_id: int,
    *,
    row_pointer: int,
    local_index: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    row = row_for_pointer(provider_id, row_pointer)
    column = int(local_index)
    if column < 0 or column >= layout.scalar_count:
        raise ValueError(
            f"local index {column} outside scalar domain {layout.scalar_count}"
        )

    address = int(row_pointer) + column * 8
    if not (
        layout.factor_workspace_base
        <= address
        < layout.output_vector_base
    ):
        raise ValueError(
            f"resolved address {hex(address)} outside factor workspace"
        )

    return {
        "domain": "workspace",
        "form": "source-context-loop",
        "address": hex(address),
        "row": row,
        "column": column,
        "row_pointer": hex(int(row_pointer)),
        "local_index": column,
        "unique": True,
    }


def resolve_direct_address(
    provider_id: int,
    *,
    address: int,
) -> dict[str, Any]:
    value = int(address)
    layout = get_storage_layout(provider_id)
    candidates = _candidate_map(provider_id).get(value, ())

    if not candidates:
        if (
            layout.output_vector_base
            <= value
            < layout.output_vector_base + layout.output_vector_bytes
            and (value - layout.output_vector_base) % 8 == 0
        ):
            return {
                "domain": "output_vector",
                "form": "direct-address",
                "address": hex(value),
                "index": (value - layout.output_vector_base) // 8,
                "candidates": [],
                "unique": True,
            }
        return {
            "domain": "global",
            "form": "direct-address",
            "address": hex(value),
            "candidates": [],
            "unique": True,
        }

    return {
        "domain": "workspace",
        "form": "direct-address",
        "address": hex(value),
        "candidates": [
            {
                "row": row,
                "column": column,
            }
            for row, column in candidates
        ],
        "candidate_count": len(candidates),
        "unique": len(candidates) == 1,
    }


def resolve_contextual_cell(
    provider_id: int,
    *,
    row_pointer: int,
    local_index: int,
) -> dict[str, Any]:
    result = resolve_loop_cell(
        provider_id,
        row_pointer=row_pointer,
        local_index=local_index,
    )
    result["resolution_basis"] = "explicit-row-pointer-plus-local-index"
    return result


def build_source_context_contract() -> dict[str, Any]:
    providers: list[dict[str, Any]] = []

    for provider_id in (0, 1):
        layout = get_storage_layout(provider_id)
        pointers = get_row_pointers(provider_id)

        diagonal_examples = [
            resolve_contextual_cell(
                provider_id,
                row_pointer=pointers[i],
                local_index=i,
            )
            for i in range(layout.scalar_count)
        ]

        providers.append(
            {
                "provider_id": provider_id,
                "scalar_count": layout.scalar_count,
                "row_pointer_count": len(pointers),
                "diagonal_resolution_unique": all(
                    example["unique"] for example in diagonal_examples
                ),
                "diagonal_examples": diagonal_examples,
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "providers": providers,
        "resolution_policy": {
            "loop_or_array_source_form": "unique when row_pointer base and local_10 are explicit",
            "direct_absolute_address": "return all workspace alias candidates",
            "output_vector": "resolve by output-vector index",
            "global": "preserve direct absolute address",
        },
        "limitations": [
            "This resolver chooses a logical cell only when the source form provides explicit row-pointer context.",
            "It does not infer semantic matrix meaning or provider-specific C++ types.",
            "Direct workspace addresses remain ambiguous when the packed storage alias map contains multiple candidates.",
        ],
        "status": "source-context-cell-resolution",
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int, choices=(0, 1), default=None)
    parser.add_argument("--address", type=lambda value: int(value, 0))
    args = parser.parse_args()

    if args.address is not None:
        if args.provider is None:
            raise SystemExit("--provider is required with --address")
        report = resolve_direct_address(args.provider, address=args.address)
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(0)

    contract = build_source_context_contract()
    print(json.dumps(contract, indent=2, sort_keys=True))
    raise SystemExit(
        0
        if all(
            provider["diagonal_resolution_unique"]
            for provider in contract["providers"]
        )
        else 2
    )
