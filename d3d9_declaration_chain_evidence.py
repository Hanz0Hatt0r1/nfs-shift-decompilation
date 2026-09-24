"""Cross-check the recovered D3D9 declaration evidence chain.

This module intentionally joins already-proven evidence reports instead of
reconstructing facts a second time. It checks that the recovered Type tables,
STREAM topology, 8-byte declaration record and canonicalizer all agree on the
same declaration ABI. Optional runtime-memory evidence is accepted only when
its address/range metadata, hashes and complete declaration array are coherent.
MEB 460/461 -> Type remains explicitly unresolved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.D3D9DeclarationChainEvidence/1"
EXPECTED_RECORD_STRIDE = 8
EXPECTED_GROUP_STRIDE = 0x14
EXPECTED_TYPE_MATCHES = 17

def _status(report: Mapping[str, Any], *path: str) -> Any:
    value: Any = report
    for key in path:
        if not isinstance(value, Mapping):
            return "not-found"
        value = value.get(key)
    return value if value is not None else "not-found"

def _count_observed_fields(report: Mapping[str, Any]) -> tuple[int, int]:
    fields = report.get("fields", [])
    if not isinstance(fields, list):
        return (0, 0)
    total = len(fields)
    observed = sum(
        isinstance(row, Mapping) and row.get("status") == "observed"
        for row in fields
    )
    return observed, total

def _source_signature(report: Mapping[str, Any]) -> dict[str, Any]:
    source = report.get("source", {})
    if not isinstance(source, Mapping):
        return {}
    return {
        key: source.get(key)
        for key in ("kind", "bytes", "line_count")
        if source.get(key) is not None
    }


def _runtime_memory_proven(report: Mapping[str, Any]) -> bool:
    if report.get("format") != "SHIFT.D3D9MemoryDeclarationEvidence/1":
        return False
    if report.get("status") != "match" or report.get("endianness") != "little":
        return False
    memory = report.get("memory")
    provenance = report.get("provenance")
    raw_bytes = report.get("bytes")
    extraction = report.get("extraction")
    boundary = report.get("evidence_boundary")
    instance = report.get("declaration_instance")
    if not all(isinstance(value, Mapping) for value in (
        memory, provenance, raw_bytes, extraction, boundary, instance
    )):
        return False
    if boundary.get("runtime_memory_dump") != "supplied":
        return False
    if boundary.get("runtime_declaration_array") != "observed":
        return False
    if not extraction.get("complete_array"):
        return False
    source_sha256 = provenance.get("source_sha256")
    slice_sha256 = provenance.get("slice_sha256")
    if not all(
        isinstance(value, str) and len(value) == 64
        for value in (source_sha256, slice_sha256)
    ):
        return False
    hex_value = raw_bytes.get("hex")
    length = raw_bytes.get("length")
    if not isinstance(hex_value, str) or not isinstance(length, int):
        return False
    try:
        decoded = bytes.fromhex(hex_value)
    except ValueError:
        return False
    if len(decoded) != length or memory.get("slice_length") != length:
        return False
    if hashlib.sha256(decoded).hexdigest() != slice_sha256:
        return False
    if instance.get("status") != "match":
        return False
    return (
        instance.get("record_stride") == EXPECTED_RECORD_STRIDE
        and _status(instance, "semantic_links", "d3dvertexelement9_shape", "status")
        == "observed"
    )

def analyze_d3d9_declaration_chain(
    *,
    type_profile: Mapping[str, Any] | None = None,
    stream_topology: Mapping[str, Any] | None = None,
    stream_record: Mapping[str, Any] | None = None,
    canonicalizer: Mapping[str, Any] | None = None,
    pe_evidence: Mapping[str, Any] | None = None,
    declaration_instance: Mapping[str, Any] | None = None,
    runtime_memory_evidence: Mapping[str, Any] | None = None,
    runtime_layout_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Join independent evidence reports into one conservative chain result."""

    type_profile = type_profile or {}
    stream_topology = stream_topology or {}
    stream_record = stream_record or {}
    canonicalizer = canonicalizer or {}
    pe_evidence = pe_evidence or {}
    declaration_instance = declaration_instance or {}
    runtime_memory_evidence = runtime_memory_evidence or {}
    runtime_layout_evidence = runtime_layout_evidence or {}

    type_validation = _status(type_profile, "validation", "status")
    type_match_count = _status(type_profile, "validation", "match_count")
    topology_status = _status(stream_topology, "status")
    topology_group_stride = stream_topology.get("grouping", {}).get("group_stride")
    record_status = _status(stream_record, "status")
    record_stride = stream_record.get("record", {}).get("stride")
    observed_fields, total_fields = _count_observed_fields(stream_record)
    canonicalizer_status = _status(canonicalizer, "status")
    canonicalizer_identity = _status(
        canonicalizer, "canonicalization", "full_record_identity"
    )

    memory_supplied = bool(runtime_memory_evidence)
    if memory_supplied and not declaration_instance:
        nested_instance = runtime_memory_evidence.get("declaration_instance")
        if isinstance(nested_instance, Mapping):
            declaration_instance = nested_instance

    instance_supplied = bool(declaration_instance)
    instance_status = _status(declaration_instance, "status")
    instance_stride = declaration_instance.get("record_stride")
    instance_shape = _status(
        declaration_instance,
        "semantic_links",
        "d3dvertexelement9_shape",
        "status",
    )

    checks = {
        "type_table_semantics": {
            "status": "observed"
            if type_validation == "match" and type_match_count == EXPECTED_TYPE_MATCHES
            else ("not-proven" if type_validation == "not-found" else type_validation),
            "detail": (
                "file-backed Type size/component tables match all recovered "
                "Type codes 0..16"
            ),
        },
        "stream_grouping": {
            "status": "observed"
            if topology_status == "observed"
            and topology_group_stride == EXPECTED_GROUP_STRIDE
            else "not-proven",
            "detail": "FUN_00854e70 groups declaration elements by Stream using a 0x14-byte group",
        },
        "declaration_record_shape": {
            "status": "observed"
            if record_status == "observed"
            and record_stride == EXPECTED_RECORD_STRIDE
            and observed_fields == total_fields == 6
            else "not-proven",
            "detail": "the XML STREAM builder emits the six 8-byte D3DVERTEXELEMENT9-shaped fields",
        },
        "full_record_identity": {
            "status": "observed"
            if canonicalizer_status == "observed"
            and canonicalizer_identity == "observed"
            else "not-proven",
            "detail": "FUN_00830f80 compares the complete 8-byte declaration record",
        },
        "xml_type_to_record_type": {
            "status": _status(
                stream_record, "semantic_links", "xml_type_to_record_type_code", "status"
            ),
        },
        "xml_usage_to_record_usage": {
            "status": _status(
                stream_record,
                "semantic_links",
                "xml_usage_to_record_usage_code",
                "status",
            ),
        },
        "xml_channel_to_usage_index": {
            "status": _status(
                stream_record,
                "semantic_links",
                "xml_channel_to_record_usage_index",
                "status",
            ),
        },
        "stream_group_to_record_pointer": {
            "status": _status(
                stream_topology,
                "semantic_links",
                "stream_group_to_record_pointer",
                "status",
            ),
        },
        "type_to_group_byte_size": {
            "status": _status(
                stream_topology,
                "semantic_links",
                "type_to_group_byte_size",
                "status",
            ),
        },
    }

    memory_layout_supplied = bool(runtime_layout_evidence)
    if memory_supplied:
        checks["runtime_memory_provenance"] = {
            "status": "observed" if _runtime_memory_proven(runtime_memory_evidence) else "not-proven",
            "detail": "the runtime memory slice has coherent address/range provenance, byte hashes and a complete declaration array",
        }

    if memory_layout_supplied:
        layout_status = runtime_layout_evidence.get("status")
        layout_link_status = _status(
            runtime_layout_evidence,
            "semantic_links",
            "offsets_follow_type_sizes",
            "status",
        )
        checks["runtime_declaration_layout"] = {
            "status": (
                "observed"
                if layout_status == "match" and layout_link_status == "observed"
                else ("mismatch" if layout_status == "mismatch" else "not-proven")
            ),
            "detail": "runtime declaration offsets follow the recovered packed Type sizes within each Stream",
        }

    if instance_supplied:
        instance_check_status = (
            "observed"
            if instance_status == "match"
            and instance_stride == EXPECTED_RECORD_STRIDE
            and instance_shape == "observed"
            else "not-proven"
            if instance_status == "match"
            else instance_status
        )
        checks["declaration_instance"] = {
            "status": instance_check_status,
            "detail": "supplied runtime declaration bytes decode as a complete 8-byte D3DVERTEXELEMENT9-shaped instance",
        }

    required_keys = [
        "type_table_semantics",
        "stream_grouping",
        "declaration_record_shape",
        "full_record_identity",
        "xml_type_to_record_type",
        "xml_usage_to_record_usage",
        "xml_channel_to_usage_index",
        "stream_group_to_record_pointer",
        "type_to_group_byte_size",
    ]
    if instance_supplied:
        required_keys.append("declaration_instance")
    if memory_supplied:
        required_keys.append("runtime_memory_provenance")
    if memory_layout_supplied:
        required_keys.append("runtime_declaration_layout")
    required_keys = tuple(required_keys)
    blocking = [
        key for key in required_keys if checks[key]["status"] != "observed"
    ]
    pe_validation = _status(pe_evidence, "type_profile_validation", "validation", "status")
    pe_available = bool(pe_evidence)
    meb_status = "not-proven"

    return {
        "format": FORMAT,
        "status": "observed" if not blocking else "not-proven",
        "chain": {
            "source": "SHIFT.exe.c",
            "type_tables": "D3D9 Type size/component tables",
            "stream_topology": "FUN_00854e70",
            "declaration_record": "FUN_008587e0",
            "canonicalizer": "FUN_00830f80",
        },
        "checks": checks,
        "summary": {
            "required_checks": len(required_keys),
            "observed_checks": len(required_keys) - len(blocking),
            "blocking_checks": blocking,
            "type_match_count": type_match_count,
            "record_stride": record_stride,
            "group_stride": topology_group_stride,
            "record_fields_observed": observed_fields,
            "record_fields_expected": total_fields,
            "pe_type_profile_status": pe_validation if pe_available else "not-supplied",
            "runtime_memory_status": (
                runtime_memory_evidence.get("status", "not-supplied")
                if memory_supplied else "not-supplied"
            ),
            "runtime_layout_status": (
                runtime_layout_evidence.get("status", "not-supplied")
                if memory_layout_supplied else "not-supplied"
            ),
        },
        "evidence_boundary": {
            "source_backed": all(
                value in {"observed", "match"}
                for value in (
                    topology_status,
                    record_status,
                    canonicalizer_status,
                    checks["xml_type_to_record_type"]["status"],
                    checks["xml_usage_to_record_usage"]["status"],
                    checks["xml_channel_to_usage_index"]["status"],
                )
            ),
            "pe_file_backed_validation": pe_validation if pe_available else "not-supplied",
            "runtime_memory_dump": (
                "observed"
                if memory_supplied and _runtime_memory_proven(runtime_memory_evidence)
                else ("not-proven" if memory_supplied else "not-supplied")
            ),
            "runtime_declaration_instance": (
                "observed" if instance_supplied and instance_status == "match" else (
                    instance_status if instance_supplied else "not-supplied"
                )
            ),
        },
        "meb_property_mapping": {
            "status": meb_status,
            "detail": "No joined evidence in this chain assigns MEB properties 460/461 to a D3D9 Type ordinal.",
        },
        "source_signatures": {
            "stream_topology": _source_signature(stream_topology),
            "stream_record": _source_signature(stream_record),
            "canonicalizer": _source_signature(canonicalizer),
        },
        "runtime_layout_evidence": (
            {
                "format": runtime_layout_evidence.get("format"),
                "status": runtime_layout_evidence.get("status"),
                "stream_summaries": runtime_layout_evidence.get("stream_summaries"),
                "issues": runtime_layout_evidence.get("issues"),
            }
            if memory_layout_supplied else None
        ),
        "runtime_memory_evidence": (
            {
                "format": runtime_memory_evidence.get("format"),
                "status": runtime_memory_evidence.get("status"),
                "memory": runtime_memory_evidence.get("memory"),
                "provenance": runtime_memory_evidence.get("provenance"),
                "extraction": runtime_memory_evidence.get("extraction"),
            }
            if memory_supplied else None
        ),
    }

def analyze_d3d9_declaration_chain_files(
    type_profile_path: str | Path,
    stream_topology_path: str | Path,
    stream_record_path: str | Path,
    canonicalizer_path: str | Path,
    *,
    pe_evidence_path: str | Path | None = None,
    declaration_instance_path: str | Path | None = None,
    runtime_memory_evidence_path: str | Path | None = None,
    runtime_layout_evidence_path: str | Path | None = None,
) -> dict[str, Any]:
    def load(path: str | Path) -> dict[str, Any]:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object: {path}")
        return value

    return analyze_d3d9_declaration_chain(
        type_profile=load(type_profile_path),
        stream_topology=load(stream_topology_path),
        stream_record=load(stream_record_path),
        canonicalizer=load(canonicalizer_path),
        pe_evidence=None if pe_evidence_path is None else load(pe_evidence_path),
        declaration_instance=(
            None if declaration_instance_path is None else load(declaration_instance_path)
        ),
        runtime_memory_evidence=(
            None
            if runtime_memory_evidence_path is None
            else load(runtime_memory_evidence_path)
        ),
        runtime_layout_evidence=(
            None
            if runtime_layout_evidence_path is None
            else load(runtime_layout_evidence_path)
        ),
    )
