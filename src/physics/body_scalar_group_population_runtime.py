"""Trace runtime scalar blocks into the BODY group storage used by FUN_007ba2b0.

Phase 488 makes explicit the source call-site contract already observed in
FUN_007b3820: every runtime constraint contributes one scalar block to each
referenced endpoint BODY, using the section-specific helper and BODY group
storage area. This is a traceability layer, not a new semantic interpretation.
"""
from __future__ import annotations

from typing import Any, Mapping

from body_matrix_structure_runtime import group_descriptor

FORMAT = "SHIFT.BodyScalarGroupPopulationRuntime/1"

SECTION_POPULATION = {
    "JOINT": {
        "helper": "FUN_007ba8b0",
        "body_group_width": 3,
        "body_group_storage": "+0x160",
        "record_stride": 0x40,
        "scalar_index_offset": "+0x30",
        "auxiliary_offset": None,
    },
    "HINGE": {
        "helper": "FUN_007ba900",
        "body_group_width": 2,
        "body_group_storage": "+0x164",
        "record_stride": 0xA0,
        "scalar_index_offset": "+0x94",
        "auxiliary_offset": "+0x90",
    },
    "BAR": {
        "helper": "FUN_007ba990",
        "body_group_width": 1,
        "body_group_storage": "+0x168",
        "record_stride": 0x60,
        "scalar_index_offset": "+0x30",
        "auxiliary_offset": None,
    },
}


def _section_info(section: str) -> dict[str, Any]:
    key = str(section).upper()
    try:
        return dict(SECTION_POPULATION[key])
    except KeyError as exc:
        raise ValueError(f"unsupported solver section: {section}") from exc


def build_scalar_group_witness(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one source-backed BODY group insertion witness per endpoint."""
    scalar_count = int(solver_domain.get("solver_scalar_count", 0))
    records = list(solver_domain.get("records") or [])
    groups_by_body: dict[str, list[dict[str, Any]]] = {}
    insertions: list[dict[str, Any]] = []
    errors: list[str] = []

    for ordered_position, record in enumerate(records):
        section = str(record.get("section", "")).upper()
        info = _section_info(section)
        width = int(record.get("solver_width", 0))
        scalar_base = int(record.get("scalar_base", -1))
        scalar_indices = [
            int(value)
            for value in record.get("scalar_indices") or []
        ]

        if width != int(info["body_group_width"]):
            errors.append(
                f"record-{ordered_position}-width-mismatch"
            )

        expected_indices = list(
            range(
                scalar_base,
                scalar_base + width,
            )
        )
        if scalar_indices != expected_indices:
            errors.append(
                f"record-{ordered_position}-scalar-block-mismatch"
            )

        if scalar_base < 0 or scalar_base + width > scalar_count:
            errors.append(
                f"record-{ordered_position}-scalar-block-out-of-domain"
            )

        for endpoint_field in ("posbody", "negbody"):
            raw_body = record.get(endpoint_field)
            if raw_body is None:
                errors.append(
                    f"record-{ordered_position}-missing-{endpoint_field}"
                )
                continue

            body = str(raw_body).upper()
            group = {
                "ordered_position": ordered_position,
                "runtime_record_index": int(
                    record.get("runtime_record_index", -1)
                ),
                "section": section,
                "endpoint_field": endpoint_field,
                "body": body,
                "width": width,
                "scalar_base": scalar_base,
                "scalar_indices": scalar_indices,
                "helper": info["helper"],
                "body_group_storage": info["body_group_storage"],
                "record_stride": info["record_stride"],
                "scalar_index_offset": info["scalar_index_offset"],
                "auxiliary_offset": info["auxiliary_offset"],
            }
            insertions.append(group)
            groups_by_body.setdefault(body, []).append(group)

    body_group_counts = {
        body: {
            "width_3": sum(
                entry["width"] == 3
                for entry in groups
            ),
            "width_2": sum(
                entry["width"] == 2
                for entry in groups
            ),
            "width_1": sum(
                entry["width"] == 1
                for entry in groups
            ),
            "total_groups": len(groups),
        }
        for body, groups in sorted(groups_by_body.items())
    }

    for body, groups in groups_by_body.items():
        seen = {
            (entry["section"], entry["scalar_base"], entry["endpoint_field"])
            for entry in groups
        }
        if len(seen) != len(groups):
            errors.append(
                f"body-{body}-duplicate-endpoint-group-witness"
            )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "scalar_count": scalar_count,
        "runtime_constraint_records": len(records),
        "endpoint_insertion_count": len(insertions),
        "body_count": len(groups_by_body),
        "insertions": insertions,
        "groups_by_body": groups_by_body,
        "body_group_counts": body_group_counts,
        "errors": errors,
        "source_contract": {
            section: {
                "helper": info["helper"],
                "body_group_width": info["body_group_width"],
                "body_group_storage": info["body_group_storage"],
                "record_stride": info["record_stride"],
                "scalar_index_offset": info["scalar_index_offset"],
                "auxiliary_offset": info["auxiliary_offset"],
            }
            for section, info in SECTION_POPULATION.items()
        },
    }


def validate_scalar_group_witness(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    records = int(report.get("runtime_constraint_records", 0))
    insertions = list(report.get("insertions") or [])

    if records < 0:
        errors.append("negative-runtime-record-count")

    expected_insertions = records * 2
    if len(insertions) != expected_insertions:
        errors.append(
            f"endpoint-insertion-count:expected={expected_insertions}:"
            f"actual={len(insertions)}"
        )

    for entry in insertions:
        section = str(entry.get("section", "")).upper()
        width = int(entry.get("width", 0))
        expected = _section_info(section)
        if width != expected["body_group_width"]:
            errors.append(
                f"section-width-mismatch:{section}:{width}"
            )

        descriptor = group_descriptor(width)
        expected_storage = f"+0x{descriptor['storage_offset']:x}"
        if entry.get("body_group_storage") != expected_storage:
            errors.append(
                f"body-group-storage-mismatch:{section}"
            )

        base = int(entry.get("scalar_base", -1))
        indices = [
            int(value)
            for value in entry.get("scalar_indices") or []
        ]
        if indices != list(range(base, base + width)):
            errors.append(
                f"scalar-index-range-mismatch:{section}:{base}"
            )

        if base < 0 or base + width > scalar_count:
            errors.append(
                f"scalar-index-out-of-domain:{section}:{base}"
            )

    return {
        "format": "SHIFT.BodyScalarGroupPopulationValidation/1",
        "version": 1,
        "ready": not errors,
        "scalar_count": scalar_count,
        "runtime_constraint_records": records,
        "endpoint_insertions": len(insertions),
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_scalar_group_witness(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    counts = report.get("body_group_counts") or {}
    width3 = sum(
        int(row.get("width_3", 0))
        for row in counts.values()
    )
    width2 = sum(
        int(row.get("width_2", 0))
        for row in counts.values()
    )
    width1 = sum(
        int(row.get("width_1", 0))
        for row in counts.values()
    )

    return {
        "scalar_count": report.get("scalar_count"),
        "runtime_constraint_records": report.get(
            "runtime_constraint_records"
        ),
        "endpoint_insertions": report.get(
            "endpoint_insertion_count"
        ),
        "body_count": report.get("body_count"),
        "width3_group_count": width3,
        "width2_group_count": width2,
        "width1_group_count": width1,
        "ready": bool(report.get("ready")),
    }


def build_scalar_group_population_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    witness = build_scalar_group_witness(solver_domain)
    validation = validate_scalar_group_witness(witness)
    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007b3820",
        "downstream": "FUN_007b2010 -> FUN_007ba2b0",
        "witness": witness,
        "summary": summarize_scalar_group_witness(witness),
        "validation": validation,
        "formula": {
            "source_scalar": "runtime constraint +0x70 copied into helper param_2",
            "endpoint_population": "helper invoked once for +0x78 endpoint and once for +0x80 endpoint",
            "joint": "FUN_007ba8b0 -> BODY width-3 group",
            "hinge": "FUN_007ba900 -> BODY width-2 group",
            "bar": "FUN_007ba990 -> BODY width-1 group",
        },
        "limitations": [
            "The helper return pointer is represented as a population event; allocator internals remain opaque.",
            "Endpoint group population is structural and does not assign physical semantic names.",
            "Same-body self-constraints are retained as two source endpoint calls rather than deduplicated.",
        ],
        "status": "source-backed-body-scalar-group-population",
    }


__all__ = [
    "FORMAT",
    "SECTION_POPULATION",
    "build_scalar_group_witness",
    "validate_scalar_group_witness",
    "summarize_scalar_group_witness",
    "build_scalar_group_population_contract",
]
