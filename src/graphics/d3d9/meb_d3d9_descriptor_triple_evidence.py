"""Exact MEB 460/461 -> D3D9 Type triple evidence.

The current MEB parser represents a vertex property descriptor as three
little-endian DWORD values and constructs the property id from those words.
Recovered SHIFT binary-mesh loading consumes the same 12-byte semantic shape:
[Type ordinal, Usage ordinal, Channel].

This module proves only the descriptor/triple relation when all required
source and descriptor evidence is present. It does not infer values from the
decimal property id alone.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


FORMAT = "SHIFT.MEBD3D9DescriptorTripleEvidence/1"
SOURCE_FORMAT = "SHIFT.D3D9SourceVertexEvidence/1"

EXPECTED = {
    "460": {
        "semantic": "COLOR0",
        "words": [4, 6, 0],
        "d3d9_type_code": 4,
        "usage_ordinal": 6,
        "channel": 0,
    },
    "461": {
        "semantic": "COLOR1",
        "words": [4, 6, 1],
        "d3d9_type_code": 4,
        "usage_ordinal": 6,
        "channel": 1,
    },
}


def _load_json(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _find_descriptor(
    meb: Mapping[str, Any],
    property_id: str,
) -> dict[str, Any] | None:
    for row in meb.get("property_descriptors") or []:
        if isinstance(row, Mapping) and str(row.get("id")) == property_id:
            return dict(row)
    return None


def _source_observation(
    source: Mapping[str, Any],
    observation_id: str,
) -> dict[str, Any]:
    row = next(
        (
            item for item in source.get("observations") or []
            if item.get("id") == observation_id
        ),
        None,
    )
    if not isinstance(row, Mapping):
        return {
            "status": "not-proven",
            "id": observation_id,
            "reason": "required source observation is absent",
        }
    return {
        "status": str(row.get("status")),
        "id": observation_id,
        "function": row.get("function"),
        "address": row.get("address"),
        "source_line": row.get("source_line"),
        "detail": row.get("detail"),
    }


def _descriptor_check(
    meb: Mapping[str, Any],
    property_id: str,
) -> dict[str, Any]:
    expected = EXPECTED[property_id]
    descriptor = _find_descriptor(meb, property_id)
    if descriptor is None:
        return {
            "status": "partial",
            "property_id": property_id,
            "expected_words": expected["words"],
            "descriptor": None,
            "reason": "exact MEB property descriptor is absent",
        }
    words = descriptor.get("words")
    if not isinstance(words, list) or len(words) != 3:
        return {
            "status": "mismatch",
            "property_id": property_id,
            "expected_words": expected["words"],
            "descriptor": descriptor,
            "reason": "descriptor words are absent or not a 3-word list",
        }
    normalized = [int(x) for x in words]
    status = "match" if normalized == expected["words"] else "mismatch"
    return {
        "status": status,
        "property_id": property_id,
        "expected_words": expected["words"],
        "observed_words": normalized,
        "descriptor": descriptor,
        "d3d9_type_code": normalized[0],
        "usage_ordinal": normalized[1],
        "channel": normalized[2],
        "reason": (
            "MEB descriptor triple exactly matches binary loader semantic triple"
            if status == "match"
            else "MEB descriptor triple differs from expected COLOR descriptor"
        ),
    }


def analyze_meb_d3d9_descriptor_triple(
    meb_report: str | Path | Mapping[str, Any],
    source_report: str | Path | Mapping[str, Any],
    *,
    resource_reports: Iterable[str | Path | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    meb = _load_json(meb_report)
    source = _load_json(source_report)
    resource_rows = [
        _load_json(item) for item in (resource_reports or [])
    ]

    source_format = "observed" if source.get("format") == SOURCE_FORMAT else "mismatch"
    binary_triple = _source_observation(
        source, "binary-descriptor-triple-semantics"
    )
    loader_identity = _source_observation(
        source, "binary-mesh-loader-identity"
    )
    meb_extension = _source_observation(
        source, "meb-extension-registration"
    )

    properties: dict[str, Any] = {}
    for property_id, expected in EXPECTED.items():
        descriptor = _descriptor_check(meb, property_id)
        resources = []
        for report in resource_rows:
            if str(report.get("property_id")) != property_id:
                continue
            source_info = report.get("source")
            resources.append({
                "resource": (
                    source_info.get("resource")
                    if isinstance(source_info, Mapping)
                    else None
                ),
                "status": "observed" if (
                    isinstance(source_info, Mapping)
                    and source_info.get("kind") == "bff-meb"
                    and source_info.get("property_descriptor", {}).get("id") == property_id
                    and source_info.get("descriptor_range_status") == "observed"
                    and source_info.get("payload_range_status") == "observed"
                    and source_info.get("decoded_stream_matches_payload_status") == "observed"
                ) else "mismatch",
            })

        mapping_checks = [
            source_format == "observed",
            binary_triple["status"] == "observed",
            loader_identity["status"] == "observed",
            meb_extension["status"] == "observed",
            descriptor["status"] == "match",
        ]
        mapping_status = (
            "match" if all(mapping_checks)
            else "mismatch" if descriptor["status"] == "mismatch"
            else "partial"
        )
        properties[property_id] = {
            "semantic": expected["semantic"],
            "expected_descriptor_words": expected["words"],
            "descriptor_check": descriptor,
            "resource_provenance": {
                "reports": resources,
                "status": (
                    "observed" if resources and all(
                        row["status"] == "observed" for row in resources
                    ) else "not-supplied" if not resources else "mismatch"
                ),
            },
            "d3d9_type_mapping": {
                "status": mapping_status,
                "d3d9_type_code": expected["d3d9_type_code"]
                if mapping_status == "match" else None,
                "usage_ordinal": expected["usage_ordinal"]
                if mapping_status == "match" else None,
                "channel": expected["channel"]
                if mapping_status == "match" else None,
            },
        }

    statuses = [row["d3d9_type_mapping"]["status"] for row in properties.values()]
    if "mismatch" in statuses:
        overall = "mismatch"
    elif all(status == "match" for status in statuses):
        overall = "match"
    elif any(status == "partial" for status in statuses):
        overall = "partial"
    else:
        overall = "not-proven"

    return {
        "format": FORMAT,
        "source": {
            "format_status": source_format,
            "binary_triple": binary_triple,
            "binary_loader_identity": loader_identity,
            "meb_extension_registration": meb_extension,
        },
        "properties": properties,
        "d3d9_type_mapping": {
            "status": overall,
            "property_ids": ["460", "461"],
            "type_codes": [4, 4] if overall == "match" else [],
            "usage_ordinals": [6, 6] if overall == "match" else [],
            "channels": [0, 1] if overall == "match" else [],
        },
        "meb_property_mapping": {
            "status": overall,
            "reason": (
                "Both MEB color descriptors exactly match the source-backed "
                "12-byte binary loader triple semantics [Type, UsageOrdinal, Channel]"
                if overall == "match"
                else "Exact MEB descriptor-to-binary-loader triple mapping is incomplete"
            ),
        },
        "selection": "resolved" if overall == "match" else "not-selected",
        "verified_abi": overall == "match",
    }


def write_descriptor_triple_report(
    meb_report: str | Path | Mapping[str, Any],
    source_report: str | Path | Mapping[str, Any],
    output: str | Path,
    *,
    resource_reports: Iterable[str | Path | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    report = analyze_meb_d3d9_descriptor_triple(
        meb_report,
        source_report,
        resource_reports=resource_reports,
    )
    Path(output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report
