"""Evidence bridge for MEB COLOR0/COLOR1 to the recovered D3D9 declaration model.

This module constrains the unresolved MEB 460/461 mapping without selecting a
D3D9 Type. It deliberately distinguishes:
  * project-level MEB storage facts,
  * source-backed SHIFT.exe observations, and
  * optional runtime declaration observations.

A result is only "match" for an individual constraint when its inputs are
actually present and consistent. The property-to-D3D9-Type mapping remains
"not-proven" until an explicit cross-layer bridge is supplied.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


FORMAT = "SHIFT.MEBD3D9ColorBridgeEvidence/1"
SOURCE_FORMAT = "SHIFT.D3D9SourceVertexEvidence/1"
MEB_FORMAT = "SHIFT.MEB"

SUPPORTED_PROPERTIES = {
    "460": {"semantic": "COLOR0", "stream_name": "colors"},
    "461": {"semantic": "COLOR1", "stream_name": "colors2"},
}

D3D9_COLOR_TYPE_CANDIDATES = (
    {
        "code": 4,
        "name": "D3DCOLOR",
        "normalized": True,
        "element_size": 4,
        "shader_order": "RGBA",
        "memory_order": "BGRA",
    },
    {
        "code": 8,
        "name": "UBYTE4N",
        "normalized": True,
        "element_size": 4,
        "shader_order": "RGBA",
        "memory_order": "RGBA",
    },
)


def _load_json(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _status_from_checks(checks: Iterable[str]) -> str:
    states = list(checks)
    if not states:
        return "not-proven"
    if any(state == "mismatch" for state in states):
        return "mismatch"
    if all(state == "observed" for state in states):
        return "observed"
    return "partial"


def _find_layout(meb: Mapping[str, Any], property_id: str) -> dict[str, Any] | None:
    layouts = meb.get("property_layouts") or []
    for row in layouts:
        if str(row.get("id")) == property_id:
            return dict(row)
    return None


def _meb_constraint(meb: Mapping[str, Any], property_id: str) -> dict[str, Any]:
    meta = SUPPORTED_PROPERTIES[property_id]
    layout = _find_layout(meb, property_id)
    if meb.get("format") not in (None, MEB_FORMAT):
        return {
            "status": "mismatch",
            "property_id": property_id,
            "reason": "input is not a SHIFT.MEB report",
            "layout": layout,
        }
    if layout is None:
        return {
            "status": "partial",
            "property_id": property_id,
            "reason": "property layout is absent",
            "layout": None,
        }

    checks = {
        "stride_4": int(layout.get("stride", -1)) == 4,
        "storage_u8x4": str(layout.get("storage")) == "u8x4",
        "components_4": int(layout.get("components", -1)) == 4,
        "normalized_true": bool(layout.get("normalized")) is True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return {
        "status": "observed" if not failed else "mismatch",
        "property_id": property_id,
        "semantic": meta["semantic"],
        "stream_name": meta["stream_name"],
        "layout": layout,
        "checks": checks,
        "failed_checks": failed,
        "reason": (
            "project MEB parser describes a 4-byte normalized u8x4 color payload"
            if not failed
            else "MEB color storage does not satisfy the expected 4-byte normalized u8x4 contract"
        ),
        "basis": "project-level MEB parser metadata; not executable-source proof",
    }


def _source_constraint(source: Mapping[str, Any], observation_id: str) -> dict[str, Any]:
    observations = source.get("observations") or []
    row = next((x for x in observations if x.get("id") == observation_id), None)
    if row is None:
        return {
            "status": "not-proven",
            "observation_id": observation_id,
            "reason": "source observation is absent",
        }
    return {
        "status": str(row.get("status")),
        "observation_id": observation_id,
        "function": row.get("function"),
        "address": row.get("address"),
        "source_line": row.get("source_line"),
        "detail": row.get("detail"),
    }


def _source_linkage(source: Mapping[str, Any], linkage_id: str) -> dict[str, Any]:
    row = (source.get("linkage") or {}).get(linkage_id)
    if not isinstance(row, Mapping):
        return {
            "status": "not-proven",
            "linkage_id": linkage_id,
            "reason": "source linkage is absent",
        }
    return {
        "status": str(row.get("status")),
        "linkage_id": linkage_id,
        "reason": row.get("reason"),
    }


def _runtime_color_types(runtime: Mapping[str, Any] | None) -> dict[str, Any]:
    if not runtime:
        return {
            "status": "not-supplied",
            "records": [],
            "observed_type_codes": [],
            "reason": "no runtime declaration evidence supplied",
        }

    records = runtime.get("records") or []
    color_records = [
        dict(row)
        for row in records
        if int(row.get("usage", -1)) == 10
    ]
    type_codes = sorted(
        {
            int(row.get("type"))
            for row in color_records
            if row.get("type") is not None
        }
    )
    return {
        "status": "observed" if color_records else "not-found",
        "records": color_records,
        "observed_type_codes": type_codes,
        "reason": (
            "runtime declaration contains COLOR usage records"
            if color_records
            else "runtime declaration contains no D3D9 COLOR usage records"
        ),
        "property_linkage": "not-proven",
    }


def analyze_meb_d3d9_color_bridge(
    meb_report: str | Path | Mapping[str, Any],
    source_report: str | Path | Mapping[str, Any],
    *,
    runtime_report: str | Path | Mapping[str, Any] | None = None,
    source_text: str | bytes | None = None,
) -> dict[str, Any]:
    """Build the conservative 460/461 -> D3D9 color candidate report."""
    meb = _load_json(meb_report)
    source = _load_json(source_report)
    runtime = _load_json(runtime_report) if runtime_report is not None else None

    if source.get("format") != SOURCE_FORMAT:
        source_format_status = "mismatch"
    else:
        source_format_status = "observed"

    source_hash = None
    source_hash_verified = None
    literal_id_counts: dict[str, int] | None = None
    if source_text is not None:
        raw = source_text if isinstance(source_text, bytes) else str(source_text).encode("utf-8")
        source_hash = hashlib.sha256(raw).hexdigest()
        expected = (source.get("source") or {}).get("sha256")
        source_hash_verified = expected == source_hash if expected else False
        text_value = raw.decode("utf-8", errors="replace")
        literal_id_counts = {
            pid: text_value.count(f'"{pid}"')
            for pid in SUPPORTED_PROPERTIES
        }

    meb_rows = {
        pid: _meb_constraint(meb, pid)
        for pid in SUPPORTED_PROPERTIES
    }
    source_rows = {
        "xml_colour_stream": _source_constraint(source, "xml-colour-stream-field"),
        "type_4_packed_color": _source_constraint(source, "declaration-type-4-packed-color"),
        "xml_type_table_chain": _source_constraint(source, "xml-type-table-chain"),
        "type_table_accessor": _source_constraint(source, "type-table-accessor"),
    }
    link_rows = {
        "xml_colour_to_type_4": _source_linkage(source, "xml_colour_to_type_4"),
        "meb_460_461_to_type_4": _source_linkage(source, "meb_460_461_to_type_4"),
    }

    runtime_rows = _runtime_color_types(runtime)

    candidates = [
        {
            **row,
            "constraint": "4-byte normalized 4-component color storage is compatible with this D3D9 type",
        }
        for row in D3D9_COLOR_TYPE_CANDIDATES
    ]

    properties: dict[str, Any] = {}
    for pid, meb_row in meb_rows.items():
        required_checks = [source_format_status, meb_row["status"]]
        if source_hash is not None:
            required_checks.append("observed" if source_hash_verified else "mismatch")
        properties[pid] = {
            "semantic": SUPPORTED_PROPERTIES[pid]["semantic"],
            "stream_name": SUPPORTED_PROPERTIES[pid]["stream_name"],
            "meb_storage": meb_row,
            "candidate_types": candidates,
            "runtime_color_type_observation": runtime_rows,
            "property_to_type": {
                "status": "not-proven",
                "reason": (
                    "MEB 460/461 storage constrains the type to 4-byte normalized candidates "
                    "(D3DCOLOR=4 or UBYTE4N=8), while the recovered source proves a separate "
                    "Type-4 packed-color path but does not expose the MEB-property-to-Type bridge"
                ),
            },
            "status": _status_from_checks(required_checks),
        }

    return {
        "format": FORMAT,
        "properties": properties,
        "source_evidence": source_rows,
        "source_linkage": link_rows,
        "runtime_color_type_observation": runtime_rows,
        "source_integrity": {
            "source_report_format": source.get("format"),
            "source_text_sha256": source_hash,
            "source_hash_matches_report": source_hash_verified,
            "literal_property_id_counts": literal_id_counts,
            "literal_property_ids_are_not_mapping_evidence": True,
        },
        "d3d9_candidates": {
            "status": "ambiguous",
            "types": candidates,
            "basis": "D3D9 type semantics + current 4-byte normalized MEB storage",
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": (
                "No source-backed or runtime-correlated evidence ties MEB property 460/461 "
                "to a specific D3D9 declaration record Type byte."
            ),
        },
        "selection": "not-selected",
        "verified_abi": False,
    }


def write_bridge_report(
    meb_report: str | Path | Mapping[str, Any],
    source_report: str | Path | Mapping[str, Any],
    output: str | Path,
    *,
    runtime_report: str | Path | Mapping[str, Any] | None = None,
    source_text: str | bytes | None = None,
) -> dict[str, Any]:
    report = analyze_meb_d3d9_color_bridge(
        meb_report,
        source_report,
        runtime_report=runtime_report,
        source_text=source_text,
    )
    Path(output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Constrain MEB 460/461 against recovered D3D9 color declaration evidence"
    )
    parser.add_argument("meb_report", help="SHIFT.MEB JSON report")
    parser.add_argument("source_report", help="SHIFT.D3D9SourceVertexEvidence/1 JSON report")
    parser.add_argument("output", help="SHIFT.MEBD3D9ColorBridgeEvidence/1 JSON output")
    parser.add_argument(
        "--runtime-report",
        help="optional SHIFT.D3D9DeclarationInstanceEvidence/1 JSON report",
    )
    parser.add_argument(
        "--source-text",
        help="optional SHIFT.exe.c text used to verify source-report SHA-256",
    )
    args = parser.parse_args(argv)
    source_text = (
        Path(args.source_text).read_bytes()
        if args.source_text
        else None
    )
    write_bridge_report(
        args.meb_report,
        args.source_report,
        args.output,
        runtime_report=args.runtime_report,
        source_text=source_text,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
