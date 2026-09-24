"""Source-level evidence extractor for the recovered SHIFT.exe Ghidra C output.

This module never promotes an ABI guess. It records only observations that are
explicitly visible in the supplied decompilation and keeps unresolved linkage
machine-readable.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


FORMAT = "SHIFT.D3D9SourceVertexEvidence/1"

FUNCTIONS = {
    "packed_color_helper": "FUN_008310c0",
    "declaration_builder": "FUN_00854e70",
    "stream_builder": "FUN_00858180",
    "stream_data_parser": "FUN_00859800",
    "type_table_accessor": "FUN_00853c20",
    "xml_stream_parser": "FUN_008587e0",
}


def _contains_all(source: str, needles: tuple[str, ...]) -> bool:
    return all(needle in source for needle in needles)


def _line_number(source: str, needle: str) -> int | None:
    """Return the 1-based source line containing a matched evidence marker."""
    offset = source.find(needle)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1

def _line_numbers(source: str, needle: str) -> list[int]:
    """Return all 1-based source lines containing a marker."""
    lines: list[int] = []
    start = 0
    while True:
        offset = source.find(needle, start)
        if offset < 0:
            return lines
        lines.append(source.count("\n", 0, offset) + 1)
        start = offset + len(needle)


def _source_path_line_numbers(source: str, filename_fragment: str) -> list[int]:
    """Return all source lines containing an escaped path fragment."""
    normalized_path = re.escape(filename_fragment).replace(r"\\", r"\\+")
    pattern = re.compile(normalized_path)
    return [
        source.count("\n", 0, match.start()) + 1
        for match in pattern.finditer(source)
    ]


def _source_line_anchors(source: str, filename_fragment: str) -> list[dict[str, int | str]]:
    """Extract decompiler line -> original source line anchors from diagnostics."""
    normalized_path = re.escape(filename_fragment).replace(r"\\", r"\\+")
    pattern = re.compile(
        re.escape("FUN_0062de50(")
        + r'[^,]+,".*?'
        + normalized_path
        + r'",0x([0-9A-Fa-f]+),'
    )
    anchors: list[dict[str, int | str]] = []
    for match in pattern.finditer(source):
        decompiler_line = source.count("\n", 0, match.start()) + 1
        original_line_hex = match.group(1).lower()
        anchors.append(
            {
                "decompiler_line": decompiler_line,
                "original_line": int(original_line_hex, 16),
                "original_line_hex": "0x" + original_line_hex,
                "source_file": filename_fragment,
            }
        )
    return anchors


def analyze_shift_exe_c(source: str | bytes) -> dict[str, Any]:
    """Extract explicit D3D9 vertex/color observations from SHIFT.exe.c text."""
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    packed_helper = _contains_all(
        text,
        (
            "uint __fastcall FUN_008310c0(float *param_1)",
            "local_10 = (uint)(longlong)ROUND(param_1[3] * 255.0);",
            "return uVar1 << 8 | local_10;",
        ),
    )

    declaration_type_switch = _contains_all(
        text,
        (
            "switch(*pbVar18)",
            "case 4:",
            "fVar7 = (float)FUN_008310c0(&local_100);",
            "case 5:",
        ),
    )

    declaration_record_layout = _contains_all(
        text,
        (
            "*(undefined2 *)(*(int *)(local_48 + 0x1c) + local_68 * 8) = 0xff;",
            "*(char *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12) = (char)uVar5;",
            "*(char *)(*(int *)(iVar15 + 0x1c) + 6 + iVar12) = (char)uVar5;",
            "*(undefined1 *)(iVar10 + 7 + iVar12) = 0;",
        ),
    )

    stream_fields_marker = 'FUN_0063d410(local_40,"Channel",&local_1c);'
    stream_fields = _contains_all(
        text,
        (
            '"STREAM"',
            '"Usage"',
            '"Channel"',
        ),
    )

    binary_descriptor_triple = _contains_all(
        text,
        (
            "uint __fastcall FUN_00859800(int param_1,int param_2)",
            "uVar13 = FUN_00853c20(*(uint *)pAVar24);",
            "uVar13 = FUN_00853c40(*(uint *)(pAVar24 + 4));",
            "SUB41(*(uint *)(pAVar24 + 8),0)",
            "pAVar24 = pAVar24 + 0xc;",
        ),
    )

    binary_descriptor_name = "LoadBinaryMeshFromResource"
    binary_loader_name = binary_descriptor_name in text

    meb_extension_marker = 'FUN_00636310(&local_64,"meb");'
    meb_extension_registration = meb_extension_marker in text

    packed_color_marker = "uint __fastcall FUN_008310c0(float *param_1)"
    declaration_type_marker = "fVar7 = (float)FUN_008310c0(&local_100);"
    type_table_marker = "return *(undefined4 *)(&DAT_00b90088 + param_1 * 4);"
    type_table_accessor = _contains_all(
        text,
        (
            "undefined4 __fastcall FUN_00853c20(int param_1)",
            type_table_marker,
        ),
    )

    xml_type_link_marker = "pbVar17 = (&PTR_DAT_00b901d0)[(int)local_18];"
    xml_type_table_chain = _contains_all(
        text,
        (
            "uint __fastcall FUN_008587e0(int param_1,int param_2)",
            xml_type_link_marker,
            "uVar9 = FUN_00853c20((int)local_18);",
            "*(char *)(iVar7 + 4 + *(int *)(param_1 + 0x1c)) = (char)uVar9;",
        ),
    )

    xml_usage_channel = _contains_all(
        text,
        (
            'pcVar16 = (char *)FUN_0063d360(local_40,(byte *)"Usage");',
            "uVar9 = FUN_00853c40(local_5c);",
            stream_fields_marker,
        ),
    )

    colour_stream_marker = 'pcVar23 = "Colour";'
    colour_stream_field = _contains_all(
        text,
        (
            "switch(local_5c)",
            "case 6:",
            colour_stream_marker,
        ),
    )

    type_table_chain = type_table_accessor and xml_type_table_chain

    type_table_call_lines = [
        line
        for line in _line_numbers(text, "FUN_00853c20(")
        if line != _line_number(text, "undefined4 __fastcall FUN_00853c20(int param_1)")
    ]
    primitive_type_source_lines = _source_path_line_numbers(
        text,
        ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",
    )
    primitive_type_anchors = _source_line_anchors(
        text,
        ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",
    )

    packed_path = packed_helper and declaration_type_switch
    observations = [
        {
            "id": "packed-color-helper",
            "status": "observed" if packed_helper else "not-found",
            "function": FUNCTIONS["packed_color_helper"],
            "address": "0x008310C0",
            "source_line": _line_number(text, packed_color_marker),
            "detail": "float RGBA components are rounded to 8-bit and accumulated as 0xAARRGGBB",
            "little_endian_memory_order": "BGRA",
        },
        {
            "id": "declaration-type-4-packed-color",
            "status": "observed" if declaration_type_switch else "not-found",
            "function": FUNCTIONS["declaration_builder"],
            "address": "0x00854E70",
            "source_line": _line_number(text, declaration_type_marker),
            "detail": "vertex conversion switch handles type 4 by calling FUN_008310c0",
            "type_code": 4,
            "conversion": "packed-color",
        },
        {
            "id": "declaration-record-fields",
            "status": "observed" if declaration_record_layout else "not-found",
            "function": FUNCTIONS["declaration_builder"],
            "address": "0x00854E70",
            "source_line": _line_number(text, "*(char *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12) = (char)uVar5;"),
            "detail": "8-byte declaration records carry stream/offset/type/method/usage/usageIndex fields",
        },
        {
            "id": "stream-type-usage-channel",
            "status": "observed" if stream_fields else "not-found",
            "function": FUNCTIONS["stream_data_parser"],
            "address": "0x00859800",
            "source_line": _line_number(text, stream_fields_marker),
            "detail": "STREAM records are parsed through Type, Usage and Channel fields",
        },
        {
            "id": "binary-descriptor-triple-semantics",
            "status": "observed" if binary_descriptor_triple else "not-found",
            "function": FUNCTIONS["stream_data_parser"],
            "address": "0x00859800",
            "source_line": _line_number(text, "uVar13 = FUN_00853c20(*(uint *)pAVar24);"),
            "detail": "binary mesh element records consume a 12-byte triple [Type ordinal, Usage ordinal, Channel] at offsets 0, 4 and 8",
            "record_stride": 0x0C,
            "fields": [
                {"name": "type_ordinal", "offset": 0, "width": 4},
                {"name": "usage_ordinal", "offset": 4, "width": 4},
                {"name": "channel", "offset": 8, "width": 4},
            ],
        },
        {
            "id": "binary-mesh-loader-identity",
            "status": "observed" if binary_loader_name else "not-found",
            "function": FUNCTIONS["stream_data_parser"],
            "address": "0x00859800",
            "source_line": _line_number(text, binary_descriptor_name),
            "detail": "diagnostic identifies FUN_00859800 as LoadBinaryMeshFromResource",
        },
        {
            "id": "meb-extension-registration",
            "status": "observed" if meb_extension_registration else "not-found",
            "source_line": _line_number(text, meb_extension_marker),
            "detail": "source registers/recognizes the .meb mesh-resource extension",
            "extension": ".meb",
        },
        {
            "id": "type-table-accessor",
            "status": "observed" if type_table_accessor else "not-found",
            "function": FUNCTIONS["type_table_accessor"],
            "address": "0x00853C20",
            "source_line": _line_number(text, type_table_marker),
            "detail": "type ordinal indexes the opaque DAT_00b90088 table",
            "table": "DAT_00b90088",
        },
        {
            "id": "xml-type-table-chain",
            "status": "observed" if xml_type_table_chain else "not-found",
            "function": FUNCTIONS["xml_stream_parser"],
            "address": "0x008587E0",
            "source_line": _line_number(text, xml_type_link_marker),
            "detail": "XML STREAM Type text is matched against PTR_DAT_00b901d0 and the matching ordinal is resolved through FUN_00853c20",
            "table": "PTR_DAT_00b901d0",
        },
        {
            "id": "xml-usage-channel-chain",
            "status": "observed" if xml_usage_channel else "not-found",
            "function": FUNCTIONS["xml_stream_parser"],
            "address": "0x008587E0",
            "source_line": _line_number(text, stream_fields_marker),
            "detail": "XML STREAM Usage resolves through FUN_00853c40 and Channel is copied into the declaration record",
        },
        {
            "id": "xml-colour-stream-field",
            "status": "observed" if colour_stream_field else "not-found",
            "function": FUNCTIONS["xml_stream_parser"],
            "address": "0x008587E0",
            "source_line": _line_number(text, colour_stream_marker),
            "detail": "the XML stream-data loader names local stream family 6 as Colour",
            "stream_family_index": 6,
        },
        {
            "id": "type-table-callsite-census",
            "status": "observed" if type_table_call_lines else "not-found",
            "function": FUNCTIONS["type_table_accessor"],
            "address": "0x00853C20",
            "source_lines": type_table_call_lines,
            "call_count": len(type_table_call_lines),
            "detail": "FUN_00853c20 is called from declaration/type-resolution paths",
        },
        {
            "id": "cprimitive-type-source-reference",
            "status": "observed" if primitive_type_source_lines else "not-found",
            "source_lines": primitive_type_source_lines,
            "reference_count": len(primitive_type_source_lines),
            "detail": "recovered diagnostics embed the original Win CPrimitiveType.cpp source path",
        },
        {
            "id": "cprimitive-type-source-anchors",
            "status": "observed" if primitive_type_anchors else "not-found",
            "source_line_anchors": primitive_type_anchors,
            "anchor_count": len(primitive_type_anchors),
            "detail": "diagnostic calls preserve original CPrimitiveType.cpp line numbers for selected decompiled branches",
        },
    ]

    linkage = {
        "type_4_to_packed_color": {
            "status": "observed" if packed_path else "not-proven",
            "reason": "FUN_00854e70 case 4 calls FUN_008310c0" if packed_path else "required source patterns were not found",
        },
        "xml_type_name_to_d3d9_type_table": {
            "status": "observed" if type_table_chain else "not-proven",
            "reason": "XML Type ordinal is fed into FUN_00853c20 and the returned type code reaches the declaration record; the opaque table contents are not exposed" if type_table_chain else "required type-table and declaration patterns were not found",
        },
        "binary_triple_to_declaration_fields": {
            "status": "observed" if binary_descriptor_triple else "not-proven",
            "reason": "FUN_00859800 resolves triple[0] via FUN_00853c20 to declaration Type, triple[1] via FUN_00853c40 to declaration Usage, and copies triple[2] into UsageIndex" if binary_descriptor_triple else "required binary descriptor triple patterns were not found",
        },
        "meb_descriptor_triple_to_binary_record": {
            "status": "observed" if (binary_descriptor_triple and binary_loader_name and meb_extension_registration) else "not-proven",
            "reason": "the recovered source identifies the binary mesh loader, recognizes .meb resources, and consumes 12-byte Type/Usage/Channel triples; this is the source-side identity bridge used for exact MEB descriptor matching" if (binary_descriptor_triple and binary_loader_name and meb_extension_registration) else "required source-side .meb loader/triple evidence is incomplete",
        },
        "xml_colour_to_type_4": {
            "status": "not-proven",
            "reason": "the XML loader exposes a Colour stream family and a shared Type table, but the recovered C does not expose the table contents needed to prove that Colour resolves to D3D9 type 4",
        },
        "meb_460_461_to_type_4": {
            "status": "not-proven",
            "reason": "the source shows the D3D9 type conversion path but does not expose the MEB property-to-Type linkage for 460/461",
        },
    }

    return {
        "format": FORMAT,
        "source": {
            "kind": "shift-exe-c",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "functions": FUNCTIONS,
        "observations": observations,
        "linkage": linkage,
        "binary_descriptor_triple": {
            "status": "observed" if binary_descriptor_triple else "not-proven",
            "record_stride": 0x0C,
            "fields": [
                {"name": "type_ordinal", "offset": 0, "width": 4},
                {"name": "usage_ordinal", "offset": 4, "width": 4},
                {"name": "channel", "offset": 8, "width": 4},
            ],
        },
        "meb_source_identity": {
            "extension_registration_status": "observed" if meb_extension_registration else "not-found",
            "binary_loader_status": "observed" if binary_loader_name else "not-found",
        },
        "selection": "not-selected",
        "verified_abi": False,
    }


def analyze_shift_exe_c_file(path: str | Path) -> dict[str, Any]:
    """Read one decompilation C dump and return its source evidence report."""
    source_path = Path(path)
    data = source_path.read_bytes()
    report = analyze_shift_exe_c(data)
    report["source"]["path"] = str(source_path)
    return report
