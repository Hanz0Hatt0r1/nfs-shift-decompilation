"""Exact executable model of the specialized-provider acceptance predicate.

Phase 481 mirrors the source-backed behavior of FUN_007c6e50/FUN_007cdb40:
compare the strict-upper matrix zero/non-zero state against the provider's
alternating RLE signature and reject on the first mismatching cell/run.
"""
from __future__ import annotations

from typing import Any, Sequence

from specialized_provider_runtime import (
    decode_transition_rle,
    get_provider,
)

FORMAT = "SHIFT.SpecializedProviderAcceptancePredicateRuntime/1"


def _index_to_cell(
    index: int,
    scalar_count: int,
) -> tuple[int, int]:
    offset = int(index)
    n = int(scalar_count)
    if offset < 0 or offset >= n * (n - 1) // 2:
        raise ValueError("upper-triangle index outside domain")

    remaining = offset
    for row in range(n):
        row_width = n - row - 1
        if remaining < row_width:
            return row, row + 1 + remaining
        remaining -= row_width
    raise AssertionError("unreachable")


def _cell_to_index(
    row: int,
    column: int,
    scalar_count: int,
) -> int:
    n = int(scalar_count)
    if not (0 <= row < column < n):
        raise ValueError("cell outside strict-upper domain")
    return (
        row * (2 * n - row - 1) // 2
        + (column - row - 1)
    )


def _rle_position(
    index: int,
    runs: Sequence[int],
) -> dict[str, Any]:
    cursor = 0
    state = False
    for run_index, run_value in enumerate(runs):
        run = int(run_value)
        if index < cursor + run:
            return {
                "run_index": run_index,
                "run_offset": index - cursor,
                "run_length": run,
                "state": state,
            }

        cursor += run
        if run_index != len(runs) - 1:
            if index == cursor:
                return {
                    "run_index": run_index,
                    "run_offset": run,
                    "run_length": run,
                    "state": not state,
                    "transition": True,
                }
            cursor += 1
            state = not state

    raise ValueError("RLE index outside decoded domain")


def strict_upper_bits(
    matrix: Sequence[Sequence[float | int]],
) -> list[bool]:
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return [
        float(matrix[row][column]) != 0.0
        for row in range(n)
        for column in range(row + 1, n)
    ]


def evaluate_acceptance_predicate(
    provider_id: int,
    matrix: Sequence[Sequence[float | int]],
) -> dict[str, Any]:
    provider = get_provider(provider_id)
    n = len(matrix)

    if n != provider.scalar_count:
        return {
            "format": FORMAT,
            "version": 1,
            "provider_id": provider_id,
            "status": "dimension-mismatch",
            "ready": False,
            "matched": False,
            "expected_scalar_count": provider.scalar_count,
            "actual_scalar_count": n,
            "upper_triangle_cells": n * (n - 1) // 2,
        }

    actual = strict_upper_bits(matrix)
    expected = decode_transition_rle(
        provider.rle,
        provider.scalar_count,
    )

    for index, (observed, expected_state) in enumerate(zip(actual, expected)):
        if observed != expected_state:
            row, column = _index_to_cell(
                index,
                provider.scalar_count,
            )
            rle = _rle_position(index, provider.rle)
            return {
                "format": FORMAT,
                "version": 1,
                "provider_id": provider_id,
                "status": "pattern-divergence",
                "ready": True,
                "matched": False,
                "dimension": n,
                "upper_triangle_cells": len(expected),
                "expected_nonzero_cells": sum(expected),
                "actual_nonzero_cells": sum(actual),
                "mismatch": {
                    "linear_index": index,
                    "row": row,
                    "column": column,
                    "expected_nonzero": expected_state,
                    "observed_nonzero": observed,
                    **rle,
                },
            }

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "status": "matched",
        "ready": True,
        "matched": True,
        "dimension": n,
        "upper_triangle_cells": len(expected),
        "expected_nonzero_cells": sum(expected),
        "actual_nonzero_cells": sum(actual),
        "mismatch": None,
    }


def build_signature_matrix(provider_id: int) -> list[list[float]]:
    provider = get_provider(provider_id)
    bits = decode_transition_rle(
        provider.rle,
        provider.scalar_count,
    )
    matrix = [
        [0.0] * provider.scalar_count
        for _ in range(provider.scalar_count)
    ]
    index = 0
    for row in range(provider.scalar_count):
        for column in range(row + 1, provider.scalar_count):
            value = 1.0 if bits[index] else 0.0
            matrix[row][column] = value
            matrix[column][row] = value
            index += 1
    return matrix


def describe_acceptance_predicate() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "providers": [
            {
                "provider_id": provider_id,
                "function": hex(get_provider(provider_id).acceptance_function),
                "scalar_count": get_provider(provider_id).scalar_count,
                "upper_triangle_cells": (
                    get_provider(provider_id).scalar_count
                    * (get_provider(provider_id).scalar_count - 1)
                    // 2
                ),
                "rle_entries": len(get_provider(provider_id).rle),
                "criterion": (
                    "accept iff every strict-upper cell has the exact "
                    "decoded RLE zero/non-zero state"
                ),
            }
            for provider_id in (0, 1)
        ],
        "algorithm": [
            "validate scalar dimension",
            "scan strict-upper cells in row-major upper-triangle order",
            "compare exact (cell != 0.0) state against alternating RLE",
            "stop at first divergence",
        ],
        "source_behavior": {
            "provider0": {
                "dimension_constant": "0x28",
                "final_transition_count": 0x52,
                "final_run_length": 0xc2,
            },
            "provider1": {
                "dimension_constant": "0x22",
                "final_transition_count": 0x6a,
                "final_run_length": 0x31,
            },
        },
        "limitations": [
            "This reproduces the sparsity predicate only; it does not model other provider selection side effects.",
            "A successful predicate match does not identify the physical or semantic meaning of any matrix cell.",
            "Provider identity for the BMW runtime remains capture-gated.",
        ],
        "status": "source-backed-executable-acceptance-predicate",
    }


def validate_acceptance_predicate_contract() -> dict[str, Any]:
    errors: list[str] = []

    for provider_id in (0, 1):
        provider = get_provider(provider_id)
        signature = decode_transition_rle(
            provider.rle,
            provider.scalar_count,
        )
        if len(signature) != provider.scalar_count * (
            provider.scalar_count - 1
        ) // 2:
            errors.append(
                f"provider-{provider_id}-decoded-length-mismatch"
            )

        matrix = build_signature_matrix(provider_id)
        result = evaluate_acceptance_predicate(
            provider_id,
            matrix,
        )
        if result["matched"] is not True:
            errors.append(
                f"provider-{provider_id}-signature-matrix-rejected"
            )

    return {
        "format": "SHIFT.SpecializedProviderAcceptancePredicateValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "_index_to_cell",
    "_cell_to_index",
    "_rle_position",
    "strict_upper_bits",
    "evaluate_acceptance_predicate",
    "build_signature_matrix",
    "describe_acceptance_predicate",
    "validate_acceptance_predicate_contract",
]
