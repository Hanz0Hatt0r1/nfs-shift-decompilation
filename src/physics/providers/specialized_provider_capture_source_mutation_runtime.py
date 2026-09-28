"""Correlate observed provider workspace mutations with source-derived factor edges.

The correlation is deliberately address-first. It maps each source-derived
(row, column) factor edge through the captured row-pointer table to an absolute
workspace address, then compares those addresses with the observed pre/post
workspace mutations. Aliased addresses retain every candidate source edge;
nothing is promoted to unique logical ownership.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from specialized_provider_capture_diff_runtime import (
    build_capture_diff_contract,
)
from specialized_provider_capture_runtime import normalize_provider_capture
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderCaptureSourceMutationCorrelation/1"


def _address(value: Any) -> int:
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _normalize_edges(
    source_pattern: Mapping[str, Any],
) -> tuple[list[tuple[int, int]], list[str]]:
    errors: list[str] = []
    edges: set[tuple[int, int]] = set()

    for index, raw in enumerate(source_pattern.get("edges") or []):
        if not isinstance(raw, Mapping):
            errors.append(f"edge-{index}:not-object")
            continue
        try:
            pivot = int(raw["pivot_index"])
            column = int(raw["column"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"edge-{index}:invalid:{exc}")
            continue
        edges.add((pivot, column))

    return sorted(edges), errors


def _source_workspace_addresses(
    pre_capture: Mapping[str, Any],
    source_pattern: Mapping[str, Any],
) -> dict[str, Any]:
    capture = normalize_provider_capture(pre_capture)
    provider_id = int(capture["provider_id"])
    layout = get_storage_layout(provider_id)
    pointers = list(capture.get("row_pointers") or [])
    errors: list[str] = []

    if not pointers:
        errors.append("row-pointer-table-missing")
    elif len(pointers) != layout.scalar_count:
        errors.append(
            "row-pointer-count-mismatch:"
            f"{len(pointers)}:{layout.scalar_count}"
        )

    source_provider = source_pattern.get("provider_id")
    if source_provider is None:
        errors.append("source-pattern-provider-id-missing")
    elif int(source_provider) != provider_id:
        errors.append(
            "provider-id-mismatch:"
            f"{provider_id}:{int(source_provider)}"
        )

    if source_pattern.get("ready") is not True:
        errors.append("source-pattern-not-ready")
        errors.extend(
            f"source-pattern:{error}"
            for error in source_pattern.get("errors") or []
        )

    edges, edge_errors = _normalize_edges(source_pattern)
    errors.extend(edge_errors)

    address_edges: dict[int, list[dict[str, int]]] = defaultdict(list)
    invalid_edges: list[dict[str, int | str]] = []

    for pivot, column in edges:
        if not 0 <= pivot < layout.scalar_count:
            invalid_edges.append(
                {
                    "pivot_index": pivot,
                    "column": column,
                    "reason": "pivot-out-of-domain",
                }
            )
            continue
        if not 0 <= column < layout.scalar_count:
            invalid_edges.append(
                {
                    "pivot_index": pivot,
                    "column": column,
                    "reason": "column-out-of-domain",
                }
            )
            continue
        if not pointers or pivot >= len(pointers):
            continue

        address = int(pointers[pivot]) + 8 * column
        if not (
            layout.factor_workspace_base
            <= address
            < layout.output_vector_base
        ):
            invalid_edges.append(
                {
                    "pivot_index": pivot,
                    "column": column,
                    "address": hex(address),
                    "reason": "outside-factor-workspace",
                }
            )
            continue

        address_edges[address].append(
            {
                "pivot_index": pivot,
                "column": column,
            }
        )

    for entries in address_edges.values():
        entries.sort(
            key=lambda item: (
                int(item["pivot_index"]),
                int(item["column"]),
            )
        )

    return {
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "factor_workspace_base": hex(layout.factor_workspace_base),
        "factor_workspace_end": hex(layout.output_vector_base),
        "source_edge_count": len(edges),
        "source_address_count": len(address_edges),
        "source_edges": [
            {"pivot_index": pivot, "column": column}
            for pivot, column in edges
        ],
        "address_edges": {
            hex(address): entries
            for address, entries in sorted(address_edges.items())
        },
        "invalid_edges": invalid_edges,
        "alias_address_count": sum(
            len(entries) > 1
            for entries in address_edges.values()
        ),
        "errors": list(dict.fromkeys(errors)),
        "ready": not errors and not invalid_edges,
    }


def correlate_source_mutations(
    pre_capture: Mapping[str, Any],
    capture_diff: Mapping[str, Any],
    source_pattern: Mapping[str, Any],
) -> dict[str, Any]:
    address_map = _source_workspace_addresses(
        pre_capture,
        source_pattern,
    )
    pre = normalize_provider_capture(pre_capture)
    provider_id = int(pre["provider_id"])
    errors = list(address_map["errors"])

    if capture_diff.get("ready") is not True:
        errors.append("capture-diff-not-ready")
    if capture_diff.get("provider_id") is None:
        errors.append("capture-diff-provider-id-missing")
    elif int(capture_diff["provider_id"]) != provider_id:
        errors.append(
            "capture-diff-provider-id-mismatch:"
            f"{provider_id}:{int(capture_diff['provider_id'])}"
        )

    observed_addresses = sorted(
        {
            _address(row["address"])
            for row in capture_diff.get("workspace_changes") or []
        }
    )
    source_addresses = {
        _address(address)
        for address in address_map["address_edges"]
    }
    observed_set = set(observed_addresses)
    covered = sorted(observed_set & source_addresses)
    uncovered = sorted(observed_set - source_addresses)
    source_changed = sorted(source_addresses & observed_set)
    source_unchanged = sorted(source_addresses - observed_set)

    observed_details = []
    for address in observed_addresses:
        observed_details.append(
            {
                "address": hex(address),
                "source_edges": list(
                    address_map["address_edges"].get(
                        hex(address),
                        [],
                    )
                ),
                "source_edge_match_count": len(
                    address_map["address_edges"].get(
                        hex(address),
                        [],
                    )
                ),
                "coverage": (
                    "source-pattern-address"
                    if address in source_addresses
                    else "uncovered-observation"
                ),
            }
        )

    status = (
        "blocked"
        if errors
        else "correlated"
        if not uncovered
        else "partial"
    )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "status": status,
        "source_pattern": {
            "format": source_pattern.get("format"),
            "provider_id": source_pattern.get("provider_id"),
            "ready": source_pattern.get("ready"),
            "source_edge_count": address_map["source_edge_count"],
            "source_address_count": address_map["source_address_count"],
        },
        "capture_diff": {
            "format": capture_diff.get("format"),
            "ready": capture_diff.get("ready"),
            "workspace_change_count": len(
                capture_diff.get("workspace_changes") or []
            ),
            "observed_workspace_address_count": len(observed_addresses),
        },
        "mapping": {
            "source_edges": address_map["source_edges"],
            "address_edges": address_map["address_edges"],
            "invalid_edges": address_map["invalid_edges"],
            "alias_address_count": address_map["alias_address_count"],
        },
        "observations": observed_details,
        "coverage": {
            "observed_workspace_address_count": len(observed_addresses),
            "observed_addresses_covered": len(covered),
            "observed_addresses_uncovered": len(uncovered),
            "observed_addresses_covered_ratio": (
                len(covered) / len(observed_addresses)
                if observed_addresses
                else None
            ),
            "source_pattern_addresses": len(source_addresses),
            "source_pattern_addresses_changed": len(source_changed),
            "source_pattern_addresses_unchanged": len(source_unchanged),
            "covered_addresses": [hex(address) for address in covered],
            "uncovered_observed_addresses": [
                hex(address) for address in uncovered
            ],
            "changed_source_pattern_addresses": [
                hex(address) for address in source_changed
            ],
            "unchanged_source_pattern_addresses": [
                hex(address) for address in source_unchanged
            ],
        },
        "errors": list(dict.fromkeys(errors)),
        "interpretation": [
            "An observed address covered by the source pattern means at least one source-derived factor edge maps to that storage address.",
            "Multiple source edges on one address are preserved as an alias set; no unique logical owner is selected.",
            "An uncovered observed address is not evidence of a source mismatch because other solver writes may target the same packed workspace.",
            "This report does not establish numeric equality, factor semantics, or retail binary equivalence.",
        ],
    }


def build_source_mutation_correlation_contract(
    pre_capture: Mapping[str, Any],
    post_capture: Mapping[str, Any],
    source_pattern: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    diff = build_capture_diff_contract(
        pre_capture,
        post_capture,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    report = correlate_source_mutations(
        pre_capture,
        diff,
        source_pattern,
    )
    report["capture_diff"] = diff
    report["summary"] = {
        "provider_id": report["provider_id"],
        "status": report["status"],
        "ready": report["ready"],
        "source_edge_count": int(
            report["source_pattern"]["source_edge_count"]
        ),
        "source_address_count": len(
            report["mapping"]["address_edges"]
        ),
        "observed_workspace_address_count": report["coverage"][
            "observed_workspace_address_count"
        ],
        "observed_addresses_covered": report["coverage"][
            "observed_addresses_covered"
        ],
        "observed_addresses_uncovered": report["coverage"][
            "observed_addresses_uncovered"
        ],
        "alias_address_count": report["mapping"][
            "alias_address_count"
        ],
    }
    return report


__all__ = [
    "FORMAT",
    "correlate_source_mutations",
    "build_source_mutation_correlation_contract",
]
