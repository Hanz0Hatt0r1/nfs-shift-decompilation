#!/usr/bin/env python3
"""Extract reflected SHIFT class fields from recovered FUN_0063a280 calls."""
from __future__ import annotations

import argparse
import ast
import csv
from bisect import bisect_right
import hashlib
import json
import re
from pathlib import Path

from extract_shift_rtti_registry import (
    _pe_sections,
    _pe_string,
    _symbol_address,
    extract_registry,
)

FORMAT = "SHIFT-REFLECTION-FIELDS/1"

_FIELD_CALL = re.compile(
    r"FUN_0063a280\(&(?P<meta>DAT_[0-9a-fA-F]{8})\s*,\s*"
    r"(?P<type>[^,\n]+)\s*,\s*"
    r"(?P<namearg>[^,\n]+)\s*,\s*"
    r"(?P<offset>[^,\n]+)\s*,\s*"
    r"(?P<flags>[^,\n]+)\s*,"
)
_ADDRESS_OF = re.compile(r"&([A-Za-z_][A-Za-z0-9_]*)")
_FUNCTION_HEADER = re.compile(
    r"(?m)^[A-Za-z_][^\n;{}]*\b((?:thunk_)?FUN_[0-9a-fA-F]+)"
    r"\([^;\n]*\)\s*$"
)


def _parse_int(expression: str) -> int | None:
    value = expression.strip()
    if not re.fullmatch(r"-?(?:0x[0-9a-fA-F]+|\d+)", value):
        return None
    return int(value, 0)


def _name_variable(argument: str) -> str | None:
    matches = _ADDRESS_OF.findall(argument)
    return matches[-1] if matches else None


def _field_name_token(text: str, position: int, variable: str | None) -> str | None:
    if not variable:
        return None
    prefix = text[max(0, position - 500):position]
    pattern = re.compile(
        r"FUN_00631740\(&"
        + re.escape(variable)
        + r"\s*,\s*(?P<token>[^;\n]+)\);"
    )
    matches = list(pattern.finditer(prefix))
    return matches[-1].group("token").strip() if matches else None


def _function_index(text: str) -> tuple[list[int], list[str]]:
    positions: list[int] = []
    names: list[str] = []
    for match in _FUNCTION_HEADER.finditer(text):
        positions.append(match.start())
        names.append(match.group(1))
    return positions, names


def _reflection_function(
    positions: list[int],
    names: list[str],
    position: int,
) -> str | None:
    index = bisect_right(positions, position) - 1
    return names[index] if index >= 0 else None

def _resolve_name_token(
    token: str | None,
    exe_data: bytes | None,
    pe: tuple[int, dict[str, dict[str, int]]] | None,
) -> str | None:
    if not token:
        return None
    token = token.strip()
    if token.startswith('"') and token.endswith('"'):
        try:
            value = ast.literal_eval(token)
        except (SyntaxError, ValueError):
            return None
        return value if isinstance(value, str) and value else None

    if exe_data is None or pe is None:
        return None
    address = _symbol_address(token.lstrip("&"))
    if address is None:
        return None
    return _pe_string(exe_data, pe[0], pe[1], address)


def extract_reflection_fields(
    source: Path,
    exe: Path | None = None,
    registry: dict | None = None,
) -> dict:
    source_data = source.read_bytes()
    text = source_data.decode("utf-8", errors="replace")
    exe_data = exe.read_bytes() if exe is not None else None
    pe = _pe_sections(exe_data) if exe_data is not None else None

    if registry is None:
        registry = extract_registry(source, exe)
    function_positions, function_names = _function_index(text)
    by_metadata = {
        row["reflection_metadata_symbol"]: row
        for row in registry["classes"]
        if row["reflection_metadata_symbol"] is not None
    }

    fields: list[dict] = []
    for match in _FIELD_CALL.finditer(text):
        metadata = match.group("meta")
        owner = by_metadata.get(metadata)
        name_argument = match.group("namearg").strip()
        variable = _name_variable(name_argument)
        name_token = _field_name_token(text, match.start(), variable)
        field_name = _resolve_name_token(name_token, exe_data, pe)

        type_expression = match.group("type").strip()
        offset_expression = match.group("offset").strip()
        flags_expression = match.group("flags").strip()
        fields.append({
            "class_name": owner["name"] if owner is not None else None,
            "class_descriptor": owner["descriptor"] if owner is not None else None,
            "reflection_metadata_symbol": metadata,
            "reflection_function": _reflection_function(
                function_positions,
                function_names,
                match.start(),
            ),
            "field_name": field_name,
            "field_name_token": name_token,
            "name_argument": name_argument,
            "type_code": _parse_int(type_expression),
            "type_expression": type_expression,
            "offset": _parse_int(offset_expression),
            "offset_expression": offset_expression,
            "flags": _parse_int(flags_expression),
            "flags_expression": flags_expression,
        })

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": hashlib.sha256(source_data).hexdigest(),
        "exe": str(exe) if exe is not None else None,
        "exe_sha256": (
            hashlib.sha256(exe_data).hexdigest() if exe_data is not None else None
        ),
        "field_call_count": len(fields),
        "mapped_class_count": sum(row["class_name"] is not None for row in fields),
        "resolved_field_name_count": sum(
            row["field_name"] is not None for row in fields
        ),
        "static_type_count": sum(row["type_code"] is not None for row in fields),
        "static_offset_count": sum(row["offset"] is not None for row in fields),
        "static_flags_count": sum(row["flags"] is not None for row in fields),
        "fields": fields,
    }


def _selected_fields(report: dict, prefixes: list[str], names: list[str]) -> list[dict]:
    selected = report["fields"]
    if prefixes:
        selected = [
            row for row in selected
            if any((row["class_name"] or "").startswith(prefix) for prefix in prefixes)
        ]
    if names:
        wanted = set(names)
        selected = [row for row in selected if row["class_name"] in wanted]
    return selected


def _write_csv(path: Path, fields: list[dict]) -> None:
    columns = [
        "class_name",
        "class_descriptor",
        "reflection_metadata_symbol",
        "reflection_function",
        "field_name",
        "field_name_token",
        "name_argument",
        "type_code",
        "type_expression",
        "offset",
        "offset_expression",
        "flags",
        "flags_expression",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="keep class names beginning with this prefix",
    )
    parser.add_argument(
        "--class-name",
        action="append",
        default=[],
        help="keep this exact class name",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args()

    report = extract_reflection_fields(args.source, args.exe)
    selected = _selected_fields(report, args.prefix, args.class_name)
    rendered = dict(report)
    rendered["selected_field_count"] = len(selected)
    rendered["fields"] = selected

    payload = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.csv_out:
        _write_csv(args.csv_out, selected)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
