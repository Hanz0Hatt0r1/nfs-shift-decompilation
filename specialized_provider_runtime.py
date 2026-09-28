"""Exact specialized-provider identity and sparsity matcher from retail SHIFT.

Provider 0 and provider 1 expose fixed scalar domains and strict-upper-triangle
sparsity signatures. The signatures are stored as source-observed run lengths:
each run is followed by one transition cell except the final run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.SpecializedProviderRuntime/1"

PROVIDER0_RLE = (
    2,2,1,11,4,14,0,2,1,11,4,17,1,11,4,14,1,1,1,14,4,9,0,1,1,14,
    4,11,1,14,4,9,0,11,4,26,4,14,0,14,4,24,4,9,1,2,1,11,4,4,0,2,1,
    11,4,7,1,11,4,4,1,1,1,14,5,1,1,14,4,1,1,14,5,11,4,16,4,4,0,14,
    4,14,194,
)

PROVIDER1_RLE = (
    9,4,2,2,0,11,7,4,2,2,0,11,6,4,2,2,0,11,5,4,2,2,0,11,4,4,2,2,0,11,
    3,4,2,2,0,11,2,4,2,2,0,11,1,4,2,2,0,11,0,4,2,2,0,16,2,2,0,11,3,8,
    4,4,2,8,4,4,1,8,4,4,0,8,4,13,4,4,1,2,0,1,10,2,0,1,9,2,0,1,11,0,1,
    4,5,0,1,4,4,0,1,4,4,1,10,4,4,4,49,
)


@dataclass(frozen=True)
class SpecializedProvider:
    provider_id: int
    selector_global: str
    vtable_address: int
    scalar_count: int
    init_function: int
    shutdown_function: int
    solve_function: int
    acceptance_function: int
    scalar_count_function: int
    vtable_04_accessor: int
    vtable_08_accessor: int
    vtable_0c_accessor: int
    vtable_2c_accessor: int
    constant_24: int
    constant_28: int
    accessor_results: dict[int, str]
    rle: tuple[int, ...]


PROVIDER0 = SpecializedProvider(
    provider_id=0,
    selector_global="DAT_00c23da8",
    vtable_address=0x00B0FC5C,
    scalar_count=40,
    init_function=0x007D2F70,
    shutdown_function=0x007C6E10,
    solve_function=0x007C7200,
    acceptance_function=0x007C6E50,
    scalar_count_function=0x007C6E30,
    vtable_04_accessor=0x007D2EB0,
    vtable_08_accessor=0x007D2EC0,
    vtable_0c_accessor=0x007D2ED0,
    vtable_2c_accessor=0x007D2F00,
    constant_24=0x4A6,
    constant_28=0x28,
    accessor_results={0x04:"0x00c23c68",0x08:"0x00c21738",0x0c:"0x00c21698",0x2c:"DAT_00b8d8ec"},
    rle=PROVIDER0_RLE,
)

PROVIDER1 = SpecializedProvider(
    provider_id=1,
    selector_global="DAT_00c23dac",
    vtable_address=0x00B0FC8C,
    scalar_count=34,
    init_function=0x007CD980,
    shutdown_function=0x007CDB00,
    solve_function=0x007CDFC0,
    acceptance_function=0x007CDB40,
    scalar_count_function=0x007CDB20,
    vtable_04_accessor=0x007D2F10,
    vtable_08_accessor=0x007D2F20,
    vtable_0c_accessor=0x007D2F30,
    vtable_2c_accessor=0x007D2F60,
    constant_24=0x2EA,
    constant_28=0x22,
    accessor_results={0x04:"0x00c21588",0x08:"0x00c1fe38",0x0c:"0x00c1fdb0",0x2c:"DAT_00b8d8f0"},
    rle=PROVIDER1_RLE,
)


def get_provider(provider_id: int) -> SpecializedProvider:
    if provider_id == 0:
        return PROVIDER0
    if provider_id == 1:
        return PROVIDER1
    raise ValueError(f"unsupported provider id: {provider_id}")


def decode_transition_rle(runs: Sequence[int], scalar_count: int) -> list[bool]:
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    if not runs:
        if n * (n - 1) // 2 == 0:
            return []
        raise ValueError("RLE must not be empty for a non-empty upper triangle")
    if any(int(run) < 0 for run in runs):
        raise ValueError("RLE run lengths must be non-negative")

    state = False
    bits: list[bool] = []
    for index, run in enumerate(runs):
        bits.extend([state] * int(run))
        if index != len(runs) - 1:
            bits.append(not state)
            state = not state

    expected = n * (n - 1) // 2
    if len(bits) != expected:
        raise ValueError(
            f"decoded RLE length {len(bits)} does not match strict-upper size {expected}"
        )
    return bits


def strict_upper_cells(matrix: Sequence[Sequence[float | int]]) -> list[bool]:
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return [
        float(matrix[row][column]) != 0.0
        for row in range(n)
        for column in range(row + 1, n)
    ]


def provider_signature(provider_id: int) -> list[bool]:
    provider = get_provider(provider_id)
    return decode_transition_rle(provider.rle, provider.scalar_count)


def match_provider_sparsity(
    provider_id: int,
    matrix: Sequence[Sequence[float | int]],
) -> dict[str, Any]:
    provider = get_provider(provider_id)
    n = len(matrix)
    if n != provider.scalar_count:
        return {
            "provider_id": provider_id,
            "ready": False,
            "matched": False,
            "reason": "dimension-mismatch",
            "expected_scalar_count": provider.scalar_count,
            "actual_scalar_count": n,
        }

    actual = strict_upper_cells(matrix)
    expected = provider_signature(provider_id)
    mismatches = [
        index
        for index, (lhs, rhs) in enumerate(zip(actual, expected))
        if lhs != rhs
    ]
    return {
        "provider_id": provider_id,
        "ready": True,
        "matched": not mismatches,
        "dimension": n,
        "upper_triangle_cells": len(expected),
        "expected_nonzero_cells": sum(expected),
        "actual_nonzero_cells": sum(actual),
        "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:16],
    }


def build_provider_contract() -> dict[str, Any]:
    def entry(provider: SpecializedProvider) -> dict[str, Any]:
        signature = provider_signature(provider.provider_id)
        return {
            "provider_id": provider.provider_id,
            "selector_global": provider.selector_global,
            "vtable_address": hex(provider.vtable_address),
            "scalar_count": provider.scalar_count,
            "functions": {
                "init": hex(provider.init_function),
                "shutdown": hex(provider.shutdown_function),
                "solve": hex(provider.solve_function),
                "acceptance": hex(provider.acceptance_function),
                "scalar_count": hex(provider.scalar_count_function),
                "vtable_04_accessor": hex(provider.vtable_04_accessor),
                "vtable_08_accessor": hex(provider.vtable_08_accessor),
                "vtable_0c_accessor": hex(provider.vtable_0c_accessor),
                "vtable_2c_accessor": hex(provider.vtable_2c_accessor),
                "accessor_results": dict(provider.accessor_results),
            },
            "constants": {
                "+0x24": hex(provider.constant_24),
                "+0x28": hex(provider.constant_28),
            },
            "sparsity": {
                "run_count": len(provider.rle),
                "upper_triangle_cells": len(signature),
                "nonzero_cells": sum(signature),
                "zero_cells": len(signature) - sum(signature),
                "rle": list(provider.rle),
                "transition_count": max(0, len(provider.rle) - 1),
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "providers": [entry(PROVIDER0), entry(PROVIDER1)],
        "vtable_offsets": {
            "probe": "0x14",
            "reset": "0x0c",
            "primary": "0x04",
            "aux": "0x08",
            "finalize": "0x2c",
        },
        "acceptance": {
            "provider0_dimension": 0x28,
            "provider1_dimension": 0x22,
            "criterion": "strict upper-triangle cell is non-zero iff decoded RLE bit is true",
        },
        "status": "source-backed-specialized-provider-identity",
        "limitations": [
            "The acceptance helper signature is not redefined here; its observed dimension constants are recorded independently.",
            "Provider solve functions are identified by address only; their numerical algorithms remain separate implementation layers.",
            "The RLE pattern authenticates sparsity only and does not prove BMW identity until compared against reconstructed/captured state.",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_provider_contract(), indent=2, sort_keys=True))
