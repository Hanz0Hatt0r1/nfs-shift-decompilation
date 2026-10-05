#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FORMAT = "SHIFT.GhidraGlobalReferences/1"
ADDRESS_RE = re.compile(r"^(?:0x|DAT_)?([0-9a-fA-F]+)$", re.IGNORECASE)


def normalize_address(token: str) -> str:
    match = ADDRESS_RE.fullmatch(token.strip())
    if match is None:
        raise ValueError(f"invalid global address: {token!r}")
    return f"0x{int(match.group(1), 16):08x}"


def validate(path: Path, requested: list[str]) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != len(requested):
        raise ValueError(f"expected {len(requested)} rows, got {len(rows)}")

    expected = [normalize_address(token) for token in requested]
    seen: list[str] = []
    for index, row in enumerate(rows):
        if row.get("format") != FORMAT:
            raise ValueError(f"row {index}: unexpected format {row.get('format')!r}")
        if row.get("found") is not True:
            raise ValueError(f"row {index}: requested global was not found")
        resolved = normalize_address(str(row.get("resolved_address", "")))
        if resolved != expected[index]:
            raise ValueError(f"row {index}: expected {expected[index]}, got {resolved}")
        if resolved in seen:
            raise ValueError(f"row {index}: duplicate resolved address {resolved}")
        seen.append(resolved)

        md5 = row.get("executable_md5")
        if not isinstance(md5, str) or len(md5) != 32:
            raise ValueError(f"row {index}: missing/invalid executable_md5")
        refs = row.get("references")
        if not isinstance(refs, list):
            raise ValueError(f"row {index}: references must be a list")
        if row.get("reference_count") != len(refs):
            raise ValueError(f"row {index}: reference_count disagrees with references")

        derived_functions: list[str] = []
        for ref_index, ref in enumerate(refs):
            if not isinstance(ref, dict):
                raise ValueError(f"row {index} ref {ref_index}: expected object")
            from_address = ref.get("from")
            if not isinstance(from_address, str):
                raise ValueError(f"row {index} ref {ref_index}: missing from address")
            normalize_address(from_address)
            if not isinstance(ref.get("type"), str) or not ref["type"]:
                raise ValueError(f"row {index} ref {ref_index}: missing reference type")
            if not isinstance(ref.get("operand_index"), int):
                raise ValueError(f"row {index} ref {ref_index}: operand_index must be int")
            if not isinstance(ref.get("primary"), bool):
                raise ValueError(f"row {index} ref {ref_index}: primary must be bool")
            function_address = ref.get("function_address")
            function_name = ref.get("function_name")
            if function_address is None:
                if function_name is not None:
                    raise ValueError(f"row {index} ref {ref_index}: function name without address")
            else:
                function_address = normalize_address(str(function_address))
                if not isinstance(function_name, str) or not function_name:
                    raise ValueError(f"row {index} ref {ref_index}: function address without name")
                if function_address not in derived_functions:
                    derived_functions.append(function_address)
            instruction = ref.get("instruction")
            if instruction is not None and not isinstance(instruction, str):
                raise ValueError(f"row {index} ref {ref_index}: instruction must be string or null")

        exported_functions = row.get("function_addresses")
        if not isinstance(exported_functions, list):
            raise ValueError(f"row {index}: function_addresses must be a list")
        exported_functions = [normalize_address(str(value)) for value in exported_functions]
        if exported_functions != derived_functions:
            raise ValueError(
                f"row {index}: function_addresses disagree with references: "
                f"{exported_functions!r} != {derived_functions!r}"
            )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(f"usage: {argv[0]} <export-jsonl> <global-address> [...]", file=sys.stderr)
        return 2
    try:
        validate(Path(argv[1]), argv[2:])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"global-reference export valid: {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
