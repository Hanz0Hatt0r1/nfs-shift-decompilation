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
        for key in ("name", "sha256", "kind", "bytes", "line_count")
        if source.get(key) is not None
    }


def _source_provenance_check(
    reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    signatures = {
        name: _source_signature(report)
        for name, report in reports.items()
    }
    candidates = {
        name: signature
        for name, signature in signatures.items()
        if signature.get("sha256") is not None
    }
    if not candidates:
        return {
            "status": "not-supplied",
            "reference": None,
            "conflicts": [],
        }

    required_fields = ("sha256", "bytes", "line_count")
    incomplete = [
        name for name, signature in signatures.items()
        if any(signature.get(field) is None for field in required_fields)
    ]
    if incomplete:
        return {
            "status": "not-proven",
            "reference": None,
            "conflicts": [{"source": name, "reason": "incomplete source provenance"} for name in incomplete],
        }

    first_name, first_signature = next(iter(signatures.items()))
    reference = {
        field: first_signature.get(field)
        for field in required_fields
    }
    reference["name"] = first_signature.get("name")
    conflicts = []
    for name, signature in signatures.items():
        for field in required_fields:
            if signature.get(field) != reference.get(field):
                conflicts.append({
                    "source": name,
                    "field": field,
                    "expected": reference.get(field),
                    "observed": signature.get(field),
                })
        if reference.get("name") is not None and signature.get("name") != reference["name"]:
            conflicts.append({
                "source": name,
                "field": "name",
                "expected": reference["name"],
                "observed": signature.get("name"),
            })

    return {
        "status": "observed" if not conflicts else "mismatch",
        "reference": reference,
        "conflicts": conflicts,
    }

def _runtime_source_sentinel_coherence(
    runtime_memory: Mapping[str, Any],
    source_sentinel: Mapping[str, Any],
) -> dict[str, Any]:
    nested = runtime_memory.get("declaration_instance")
    if not isinstance(nested, Mapping):
        return {"status": "not-proven", "conflicts": [{"reason": "missing nested declaration instance"}]}

    runtime_validation = nested.get("validation")
    records = nested.get("records")
    source_shape = source_sentinel.get("sentinel")
    source_status = source_sentinel.get("status")
    source_link = _status(
        source_sentinel,
        "semantic_links",
        "exact_d3ddecl_end_shape",
        "status",
    )
    follow_link = _status(
        source_sentinel,
        "semantic_links",
        "sentinel_follows_data_count",
        "status",
    )
    if not isinstance(runtime_validation, Mapping) or not isinstance(records, list):
        return {"status": "not-proven", "conflicts": [{"reason": "runtime sentinel metadata missing"}]}
    if source_status != "observed" or source_link != "observed" or follow_link != "observed":
        return {"status": "not-proven", "conflicts": [{"reason": "source sentinel evidence incomplete"}]}
    end_index = runtime_validation.get("end_sentinel_index")
    if not isinstance(end_index, int) or end_index < 0 or end_index >= len(records):
        return {"status": "not-proven", "conflicts": [{"reason": "runtime end sentinel index invalid", "observed": end_index}]}
    runtime_record = records[end_index]
    if not isinstance(runtime_record, Mapping):
        return {"status": "not-proven", "conflicts": [{"reason": "runtime sentinel record missing"}]}

    if not isinstance(source_shape, Mapping):
        return {"status": "not-proven", "conflicts": [{"reason": "source sentinel values missing"}]}

    fields = ("stream", "offset", "type", "method", "usage", "usage_index")
    conflicts = []
    for field in fields:
        observed = runtime_record.get(field)
        expected = source_shape.get(field)
        if observed != expected:
            conflicts.append({
                "field": field,
                "expected": expected,
                "observed": observed,
            })

    expected_array_records = end_index + 1
    extraction = runtime_memory.get("extraction")
    if isinstance(extraction, Mapping):
        observed_array_records = extraction.get("declaration_array_records")
        if observed_array_records is not None and observed_array_records != expected_array_records:
            conflicts.append({
                "field": "declaration_array_records",
                "expected": expected_array_records,
                "observed": observed_array_records,
            })

    return {
        "status": "observed" if not conflicts else "mismatch",
        "end_sentinel_index": end_index,
        "expected_sentinel": dict(source_shape),
        "observed_sentinel": {
            field: runtime_record.get(field)
            for field in fields
        },
        "conflicts": conflicts,
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
    api_bind_evidence: Mapping[str, Any] | None = None,
    render_api_evidence: Mapping[str, Any] | None = None,
    declaration_create_evidence: Mapping[str, Any] | None = None,
    declaration_count_evidence: Mapping[str, Any] | None = None,
    declaration_sentinel_evidence: Mapping[str, Any] | None = None,
    declaration_lifecycle_evidence: Mapping[str, Any] | None = None,
    binding_args_evidence: Mapping[str, Any] | None = None,
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
    api_bind_evidence = api_bind_evidence or {}
    render_api_evidence = render_api_evidence or {}
    declaration_create_evidence = declaration_create_evidence or {}
    declaration_count_evidence = declaration_count_evidence or {}
    declaration_sentinel_evidence = declaration_sentinel_evidence or {}
    declaration_lifecycle_evidence = declaration_lifecycle_evidence or {}
    binding_args_evidence = binding_args_evidence or {}

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

    provenance_reports = {
        "stream_topology": stream_topology,
        "stream_record": stream_record,
        "canonicalizer": canonicalizer,
    }
    if api_bind_evidence:
        provenance_reports["api_bind"] = api_bind_evidence
    if render_api_evidence:
        provenance_reports["render_api"] = render_api_evidence
    if declaration_create_evidence:
        provenance_reports["declaration_create"] = declaration_create_evidence
    if declaration_count_evidence:
        provenance_reports["declaration_count"] = declaration_count_evidence
    if declaration_sentinel_evidence:
        provenance_reports["declaration_sentinel"] = declaration_sentinel_evidence
    if declaration_lifecycle_evidence:
        provenance_reports["declaration_lifecycle"] = declaration_lifecycle_evidence
    if binding_args_evidence:
        provenance_reports["binding_args"] = binding_args_evidence
    source_provenance = _source_provenance_check(provenance_reports)

    memory_layout_supplied = bool(runtime_layout_evidence)
    api_bind_supplied = bool(api_bind_evidence)
    binding_args_supplied = bool(binding_args_evidence)
    if binding_args_supplied:
        binding_status = binding_args_evidence.get("status")
        stream_link = _status(
            binding_args_evidence,
            "semantic_links",
            "stream_arguments_to_device",
            "status",
        )
        index_link = _status(
            binding_args_evidence,
            "semantic_links",
            "index_argument_to_device",
            "status",
        )
        checks["d3d9_binding_arguments"] = {
            "status": (
                "observed"
                if binding_status == "observed"
                and stream_link == "observed"
                and index_link == "observed"
                else ("mismatch" if binding_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed SetStreamSource and SetIndices argument forwarding is internally complete",
        }

    declaration_lifecycle_supplied = bool(declaration_lifecycle_evidence)
    if declaration_lifecycle_supplied:
        lifecycle_status = declaration_lifecycle_evidence.get("status")
        static_chain_status = _status(
            declaration_lifecycle_evidence,
            "evidence_boundary",
            "static_source_call_chain",
        )
        checks["d3d9_declaration_lifecycle"] = {
            "status": (
                "observed"
                if lifecycle_status == "observed" and static_chain_status == "observed"
                else ("mismatch" if lifecycle_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed mesh construction, declaration creation and declaration binding form one recovered lifecycle",
        }

    declaration_sentinel_supplied = bool(declaration_sentinel_evidence)
    if declaration_sentinel_supplied:
        sentinel_status = declaration_sentinel_evidence.get("status")
        sentinel_link = _status(
            declaration_sentinel_evidence,
            "semantic_links",
            "exact_d3ddecl_end_shape",
            "status",
        )
        follow_link = _status(
            declaration_sentinel_evidence,
            "semantic_links",
            "sentinel_follows_data_count",
            "status",
        )
        checks["d3d9_declaration_sentinel"] = {
            "status": (
                "observed"
                if sentinel_status == "observed"
                and sentinel_link == "observed"
                and follow_link == "observed"
                else ("mismatch" if sentinel_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed loader writes the complete D3DDECL_END-shaped sentinel after the data declaration records",
        }

    declaration_count_supplied = bool(declaration_count_evidence)
    if declaration_count_supplied:
        count_status = declaration_count_evidence.get("status")
        count_link = _status(
            declaration_count_evidence,
            "semantic_links",
            "count_to_create_buffer",
            "status",
        )
        checks["d3d9_declaration_count_boundary"] = {
            "status": (
                "observed"
                if count_status == "observed" and count_link == "observed"
                else ("mismatch" if count_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed declaration count drives the 8-byte record buffer passed to creation",
        }

    declaration_create_supplied = bool(declaration_create_evidence)
    if declaration_create_supplied:
        create_status = declaration_create_evidence.get("status")
        create_link = _status(
            declaration_create_evidence,
            "semantic_links",
            "canonical_record_bytes_to_create_call",
            "status",
        )
        checks["d3d9_declaration_create"] = {
            "status": (
                "observed"
                if create_status == "observed" and create_link == "observed"
                else ("mismatch" if create_status == "mismatch" else "not-proven")
            ),
            "detail": "the canonicalized 8-byte declaration array reaches IDirect3DDevice9 CreateVertexDeclaration",
        }

    render_api_supplied = bool(render_api_evidence)
    if render_api_supplied:
        render_status = render_api_evidence.get("status")
        render_links = _status(
            render_api_evidence,
            "semantic_links",
            "declaration_to_stream_setup",
            "status",
        )
        draw_link = _status(
            render_api_evidence,
            "semantic_links",
            "render_setup_to_draw",
            "status",
        )
        checks["d3d9_render_api_boundary"] = {
            "status": (
                "observed"
                if render_status == "observed"
                and render_links == "observed"
                and draw_link == "observed"
                else ("mismatch" if render_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed declaration/stream/index setup reaches the indexed D3D9 draw API boundary",
        }

    if api_bind_supplied:
        api_status = api_bind_evidence.get("status")
        api_link = _status(
            api_bind_evidence,
            "semantic_links",
            "declaration_object_to_d3d9_bind",
            "status",
        )
        checks["d3d9_api_bind"] = {
            "status": (
                "observed"
                if api_status == "observed" and api_link == "observed"
                else ("mismatch" if api_status == "mismatch" else "not-proven")
            ),
            "detail": "source-backed declaration object reaches the IDirect3DDevice9 SetVertexDeclaration vtable slot",
        }

    runtime_memory_sentinel_coherence_supplied = bool(
        runtime_memory_evidence and declaration_sentinel_evidence
    )
    if runtime_memory_sentinel_coherence_supplied:
        sentinel_coherence = _runtime_source_sentinel_coherence(
            runtime_memory_evidence,
            declaration_sentinel_evidence,
        )
        checks["runtime_source_sentinel_coherence"] = {
            "status": sentinel_coherence["status"],
            "detail": "runtime D3DDECL_END bytes exactly match the source-proven sentinel producer",
            "coherence": sentinel_coherence,
        }

    if source_provenance["status"] != "not-supplied":
        checks["source_provenance_coherence"] = {
            "status": source_provenance["status"],
            "detail": "source-backed evidence reports refer to one coherent SHIFT.exe.c provenance tuple",
        }

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
    if source_provenance["status"] != "not-supplied":
        required_keys.append("source_provenance_coherence")
    if api_bind_supplied:
        required_keys.append("d3d9_api_bind")
    if render_api_supplied:
        required_keys.append("d3d9_render_api_boundary")
    if declaration_create_supplied:
        required_keys.append("d3d9_declaration_create")
    if declaration_count_supplied:
        required_keys.append("d3d9_declaration_count_boundary")
    if declaration_sentinel_supplied:
        required_keys.append("d3d9_declaration_sentinel")
    if declaration_lifecycle_supplied:
        required_keys.append("d3d9_declaration_lifecycle")
    if binding_args_supplied:
        required_keys.append("d3d9_binding_arguments")
    if instance_supplied:
        required_keys.append("declaration_instance")
    if memory_supplied:
        required_keys.append("runtime_memory_provenance")
    if runtime_memory_sentinel_coherence_supplied:
        required_keys.append("runtime_source_sentinel_coherence")
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
            "source_provenance_status": source_provenance["status"],
            "api_bind_status": (
                api_bind_evidence.get("status", "not-supplied")
                if api_bind_supplied else "not-supplied"
            ),
            "render_api_status": (
                render_api_evidence.get("status", "not-supplied")
                if render_api_supplied else "not-supplied"
            ),
            "declaration_create_status": (
                declaration_create_evidence.get("status", "not-supplied")
                if declaration_create_supplied else "not-supplied"
            ),
            "declaration_count_status": (
                declaration_count_evidence.get("status", "not-supplied")
                if declaration_count_supplied else "not-supplied"
            ),
            "declaration_sentinel_status": (
                declaration_sentinel_evidence.get("status", "not-supplied")
                if declaration_sentinel_supplied else "not-supplied"
            ),
            "declaration_lifecycle_status": (
                declaration_lifecycle_evidence.get("status", "not-supplied")
                if declaration_lifecycle_supplied else "not-supplied"
            ),
            "binding_args_status": (
                binding_args_evidence.get("status", "not-supplied")
                if binding_args_supplied else "not-supplied"
            ),
            "runtime_memory_status": (
                runtime_memory_evidence.get("status", "not-supplied")
                if memory_supplied else "not-supplied"
            ),
            "runtime_sentinel_coherence_status": (
                sentinel_coherence["status"]
                if runtime_memory_sentinel_coherence_supplied else "not-supplied"
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
        "source_provenance": source_provenance,
        "binding_args_evidence": (
            {
                "format": binding_args_evidence.get("format"),
                "status": binding_args_evidence.get("status"),
                "stream_source": binding_args_evidence.get("stream_source"),
                "index_source": binding_args_evidence.get("index_source"),
                "semantic_links": binding_args_evidence.get("semantic_links"),
            }
            if binding_args_supplied else None
        ),
        "declaration_lifecycle_evidence": (
            {
                "format": declaration_lifecycle_evidence.get("format"),
                "status": declaration_lifecycle_evidence.get("status"),
                "lifecycle": declaration_lifecycle_evidence.get("lifecycle"),
                "edges": declaration_lifecycle_evidence.get("edges"),
                "evidence_boundary": declaration_lifecycle_evidence.get("evidence_boundary"),
            }
            if declaration_lifecycle_supplied else None
        ),
        "declaration_sentinel_evidence": (
            {
                "format": declaration_sentinel_evidence.get("format"),
                "status": declaration_sentinel_evidence.get("status"),
                "function": declaration_sentinel_evidence.get("function"),
                "sentinel": declaration_sentinel_evidence.get("sentinel"),
                "semantic_links": declaration_sentinel_evidence.get("semantic_links"),
            }
            if declaration_sentinel_supplied else None
        ),
        "declaration_count_evidence": (
            {
                "format": declaration_count_evidence.get("format"),
                "status": declaration_count_evidence.get("status"),
                "count_boundary": declaration_count_evidence.get("count_boundary"),
                "create_boundary": declaration_count_evidence.get("create_boundary"),
                "semantic_links": declaration_count_evidence.get("semantic_links"),
            }
            if declaration_count_supplied else None
        ),
        "declaration_create_evidence": (
            {
                "format": declaration_create_evidence.get("format"),
                "status": declaration_create_evidence.get("status"),
                "api_identity": declaration_create_evidence.get("api_identity"),
                "record_layout": declaration_create_evidence.get("record_layout"),
                "semantic_links": declaration_create_evidence.get("semantic_links"),
            }
            if declaration_create_supplied else None
        ),
        "render_api_evidence": (
            {
                "format": render_api_evidence.get("format"),
                "status": render_api_evidence.get("status"),
                "api_methods": render_api_evidence.get("api_methods"),
                "observations": render_api_evidence.get("observations"),
                "semantic_links": render_api_evidence.get("semantic_links"),
            }
            if render_api_supplied else None
        ),
        "api_bind_evidence": (
            {
                "format": api_bind_evidence.get("format"),
                "status": api_bind_evidence.get("status"),
                "api_identity": api_bind_evidence.get("api_identity"),
                "semantic_links": api_bind_evidence.get("semantic_links"),
            }
            if api_bind_supplied else None
        ),
        "meb_property_mapping": {
            "status": meb_status,
            "detail": "No joined evidence in this chain assigns MEB properties 460/461 to a D3D9 Type ordinal.",
        },
        "source_signatures": {
            "stream_topology": _source_signature(stream_topology),
            "stream_record": _source_signature(stream_record),
            "canonicalizer": _source_signature(canonicalizer),
        },
        "runtime_sentinel_coherence": (
            sentinel_coherence
            if runtime_memory_sentinel_coherence_supplied else None
        ),
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
    api_bind_evidence_path: str | Path | None = None,
    render_api_evidence_path: str | Path | None = None,
    declaration_create_evidence_path: str | Path | None = None,
    declaration_count_evidence_path: str | Path | None = None,
    declaration_sentinel_evidence_path: str | Path | None = None,
    declaration_lifecycle_evidence_path: str | Path | None = None,
    binding_args_evidence_path: str | Path | None = None,
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
        api_bind_evidence=(
            None
            if api_bind_evidence_path is None
            else load(api_bind_evidence_path)
        ),
        render_api_evidence=(
            None
            if render_api_evidence_path is None
            else load(render_api_evidence_path)
        ),
        declaration_create_evidence=(
            None
            if declaration_create_evidence_path is None
            else load(declaration_create_evidence_path)
        ),
        declaration_count_evidence=(
            None
            if declaration_count_evidence_path is None
            else load(declaration_count_evidence_path)
        ),
        declaration_sentinel_evidence=(
            None
            if declaration_sentinel_evidence_path is None
            else load(declaration_sentinel_evidence_path)
        ),
        declaration_lifecycle_evidence=(
            None
            if declaration_lifecycle_evidence_path is None
            else load(declaration_lifecycle_evidence_path)
        ),
        binding_args_evidence=(
            None
            if binding_args_evidence_path is None
            else load(binding_args_evidence_path)
        ),
    )
