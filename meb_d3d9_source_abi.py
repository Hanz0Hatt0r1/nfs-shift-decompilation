"""Source-correlated MEB -> D3D9 vertex ABI evidence.

This module bridges two independently recovered facts:

1. the MEB reader encodes a three-DWORD property identifier (Type, Usage, Channel);
2. the original Win binary mesh loader consumes the same 12-byte descriptor as
   Type, Usage and Channel, then resolves Type/Usage through the D3D9 lookup
   tables before building a vertex declaration.

For 460/461 this yields (4, 6, 0/1): D3DDECLTYPE_D3DCOLOR, Usage=Colour,
Channel 0/1. The packed helper establishes BGRA source memory order on the
original little-endian target.

The report is deliberately source-correlated rather than dependent on opaque
global initializer bytes. It never changes unrelated property semantics.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable


FORMAT = "SHIFT.MEBD3D9SourceABIEvidence/1"
BINARY_LOADER = "FUN_00859800"
DECLARATION_BUILDER = "FUN_00854e70"
PACKED_COLOR_HELPER = "FUN_008310c0"
XML_STREAM_LOADER = "FUN_008587e0"


VERIFIED_COLOR_ABI = {
    "460": {
        "property_id": "460",
        "descriptor_triplet": (4, 6, 0),
        "type_code": 4,
        "d3d9_type": "D3DCOLOR",
        "usage_code": 6,
        "usage": "Colour",
        "channel": 0,
        "semantic": "COLOR0",
        "source_memory_order": "BGRA",
        "shader_order": "RGBA",
        "normalized": True,
        "abi_status": "verified",
    },
    "461": {
        "property_id": "461",
        "descriptor_triplet": (4, 6, 1),
        "type_code": 4,
        "d3d9_type": "D3DCOLOR",
        "usage_code": 6,
        "usage": "Colour",
        "channel": 1,
        "semantic": "COLOR1",
        "source_memory_order": "BGRA",
        "shader_order": "RGBA",
        "normalized": True,
        "abi_status": "verified",
    },
}


def property_triplet(property_id: str | int) -> tuple[int, int, int]:
    """Convert a three-digit MEB property id to its source descriptor tuple."""
    text = str(property_id)
    if len(text) != 3 or not text.isdigit():
        raise ValueError(f"MEB property id must be exactly three decimal digits: {property_id!r}")
    return int(text[0]), int(text[1]), int(text[2])


def _contains_all(source: str, markers: Iterable[str]) -> bool:
    return all(marker in source for marker in markers)


def _line_number(source: str, marker: str, start: int = 0) -> int | None:
    offset = source.find(marker, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _function_span(source: str, signature_marker: str, next_signature: str | None = None) -> tuple[str, int, int] | None:
    start = source.find(signature_marker)
    if start < 0:
        return None
    end = len(source)
    if next_signature:
        candidate = source.find(next_signature, start + len(signature_marker))
        if candidate >= 0:
            end = candidate
    return source[start:end], start, end


def analyze_meb_d3d9_source_abi(
    source: str | bytes,
    properties: Iterable[str] = ("200", "220", "240", "250", "310", "580", "460", "461"),
) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    meb_descriptor = _contains_all(
        text,
        (
            "a = r.u32(); b = r.u32(); c = r.u32();",
            'prop = f"{a}{b}{c}"',
        ),
    )

    binary_loader_span = _function_span(
        text,
        f"uint __fastcall {BINARY_LOADER}",
    )
    binary_loader = binary_loader_span[0] if binary_loader_span else ""
    binary_descriptor = _contains_all(
        binary_loader,
        (
            "FUN_00853c20(*(uint *)pAVar24)",
            "FUN_00853c40(*(uint *)(pAVar24 + 4))",
            "SUB41(*(uint *)(pAVar24 + 8),0)",
            "pAVar24 = pAVar24 + 0xc;",
        ),
    )

    declaration_span = _function_span(
        text,
        f"undefined4 __fastcall {DECLARATION_BUILDER}",
    )
    declaration = declaration_span[0] if declaration_span else ""
    usage_colour_branch = _contains_all(
        declaration,
        (
            "else if (local_6c == (ushort *)0x6)",
            "local_14._3_1_",
            "local_14 = CONCAT13(local_14._3_1_ + '\\x01',(undefined3)local_14);",
        ),
    )

    packed_helper = _contains_all(
        text,
        (
            f"uint __fastcall {PACKED_COLOR_HELPER}(float *param_1)",
            "ROUND(param_1[3] * 255.0)",
            "ROUND(*param_1 * 255.0)",
            "ROUND(param_1[1] * 255.0)",
            "ROUND(param_1[2] * 255.0)",
            "return uVar1 << 8 | local_10;",
        ),
    )

    xml_usage = _contains_all(
        text,
        (
            f"uint __fastcall {XML_STREAM_LOADER}",
            "case 6:",
            'pcVar23 = "Colour";',
        ),
    )

    binary_decl_line = _line_number(text, "FUN_00853c20(*(uint *)pAVar24)")
    binary_usage_line = _line_number(text, "FUN_00853c40(*(uint *)(pAVar24 + 4))")
    binary_channel_line = _line_number(text, "SUB41(*(uint *)(pAVar24 + 8),0)")
    binary_stride_line = _line_number(text, "pAVar24 = pAVar24 + 0xc;")

    packed_helper_line = _line_number(text, f"uint __fastcall {PACKED_COLOR_HELPER}(float *param_1)")
    usage_colour_line = _line_number(text, "else if (local_6c == (ushort *)0x6)")
    xml_colour_line = _line_number(text, 'pcVar23 = "Colour";')

    results: list[dict[str, Any]] = []
    for property_id in properties:
        pid = str(property_id)
        triplet = property_triplet(pid)
        type_code, usage_code, channel = triplet

        semantic = None
        if usage_code == 6:
            semantic = f"COLOR{channel}"

        evidence_ok = (
            meb_descriptor
            and binary_descriptor
            and packed_helper
            and usage_colour_branch
            and xml_usage
        )
        is_verified_color = pid in VERIFIED_COLOR_ABI and triplet in {
            tuple(item["descriptor_triplet"]) for item in VERIFIED_COLOR_ABI.values()
        }

        row = {
            "property_id": pid,
            "descriptor_triplet": list(triplet),
            "type_code": type_code,
            "usage_code": usage_code,
            "channel": channel,
            "semantic": semantic,
            "status": "verified" if evidence_ok and is_verified_color else "not-proven",
            "verification_scope": (
                "source-correlated-under-MEB-three-u32-property-id-convention"
                if evidence_ok and is_verified_color
                else None
            ),
            "d3d9_type": "D3DCOLOR" if evidence_ok and is_verified_color else None,
            "source_memory_order": "BGRA" if evidence_ok and is_verified_color else None,
            "shader_order": "RGBA" if evidence_ok and is_verified_color else None,
            "normalized": True if evidence_ok and is_verified_color else None,
            "evidence": {
                "meb_three_u32_descriptor": {
                    "status": "observed" if meb_descriptor else "not-found",
                    "source_line": _line_number(text, 'prop = f"{a}{b}{c}"'),
                },
                "binary_descriptor_mapping": {
                    "status": "observed" if binary_descriptor else "not-found",
                    "type_source_line": binary_decl_line,
                    "usage_source_line": binary_usage_line,
                    "channel_source_line": binary_channel_line,
                    "descriptor_stride_source_line": binary_stride_line,
                    "descriptor_stride": 12 if binary_descriptor else None,
                },
                "type_4_packed_color": {
                    "status": "observed" if packed_helper and type_code == 4 else "not-proven",
                    "source_line": packed_helper_line,
                    "d3d9_type": "D3DCOLOR" if packed_helper and type_code == 4 else None,
                    "memory_order": "BGRA" if packed_helper and type_code == 4 else None,
                },
                "usage_6_colour": {
                    "status": "observed" if usage_colour_branch and usage_code == 6 else "not-proven",
                    "declaration_source_line": usage_colour_line,
                    "xml_source_line": xml_colour_line,
                    "usage_name": "Colour" if usage_code == 6 and xml_usage else None,
                },
            },
        }
        if pid in VERIFIED_COLOR_ABI:
            row["expected_source_abi"] = dict(VERIFIED_COLOR_ABI[pid])
        results.append(row)

    cross_checks = {
        "known_triplets": {
            "200": {
                "triplet": list(property_triplet("200")),
                "expected": {"type_code": 2, "usage_code": 0, "channel": 0, "semantic": "POSITION0"},
            },
            "220": {
                "triplet": list(property_triplet("220")),
                "expected": {"type_code": 2, "usage_code": 2, "channel": 0, "semantic": "NORMAL0"},
            },
            "240": {
                "triplet": list(property_triplet("240")),
                "expected": {"type_code": 2, "usage_code": 4, "channel": 0, "semantic": "TANGENT0"},
            },
            "250": {
                "triplet": list(property_triplet("250")),
                "expected": {"type_code": 2, "usage_code": 5, "channel": 0, "semantic": "BINORMAL0"},
            },
            "310": {
                "triplet": list(property_triplet("310")),
                "expected": {"type_code": 3, "usage_code": 1, "channel": 0, "semantic": "BLENDWEIGHT0"},
            },
            "580": {
                "triplet": list(property_triplet("580")),
                "expected": {"type_code": 5, "usage_code": 8, "channel": 0, "semantic": "BLENDINDICES0"},
            },
        },
        "consistency_basis": "all IDs use the same decimal three-digit Type/Usage/Channel encoding as the source loader's 12-byte descriptor",
    }

    verified = [
        row["property_id"]
        for row in results
        if row["status"] == "verified"
    ]
    return {
        "format": FORMAT,
        "source": {
            "kind": "shift-exe-c",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "source_functions": {
            "binary_loader": BINARY_LOADER,
            "declaration_builder": DECLARATION_BUILDER,
            "packed_color_helper": PACKED_COLOR_HELPER,
            "xml_stream_loader": XML_STREAM_LOADER,
        },
        "global_evidence": {
            "meb_three_u32_descriptor": meb_descriptor,
            "binary_descriptor_type_usage_channel": binary_descriptor,
            "declaration_usage_6_colour_channel": usage_colour_branch,
            "packed_color_type_4": packed_helper,
            "xml_usage_6_colour": xml_usage,
        },
        "properties": results,
        "verified_properties": verified,
        "verification_count": len(verified),
        "meb_mapping": {
            "status": "verified" if {"460", "461"}.issubset(verified) else "not-proven",
            "properties": {
                pid: dict(VERIFIED_COLOR_ABI[pid])
                for pid in ("460", "461")
                if pid in verified
            },
        },
        "cross_checks": cross_checks,
    }


def analyze_meb_d3d9_source_abi_file(path: str) -> dict[str, Any]:
    source_path = Path(path)
    report = analyze_meb_d3d9_source_abi(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
