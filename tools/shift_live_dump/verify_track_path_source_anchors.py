#!/usr/bin/env python3
"""Verify track/path vtable constants against recovered SHIFT.exe.c anchors."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT-TRACK-PATH-SOURCE-ANCHORS/1"

ANCHORS = {
    "AISegmentPath": ("FUN_006cfe70", "PTR_FUN_00afc930"),
    "AIPathNode": ("FUN_006cfc10", "PTR_FUN_00afbf60"),
    "AIPolylinePath": ("FUN_006cc900", "PTR_FUN_00afc678"),
    "AIPolyPathNode": ("FUN_006cc730", "PTR_FUN_00afbfa8"),
    "Knot": ("FUN_006cdf70", "PTR_FUN_00afbe28"),
}

FACTORY_LINKS = (
    ("AISegmentPath", "FUN_006d8490", "DAT_00c0d668", "FUN_006cfe70"),
    ("AIPolylinePath", "FUN_006d8490", "DAT_00c0d608", "FUN_006cc900"),
)


def extract_function(text: str, name: str) -> str | None:
    """Return the first definition body for a Ghidra-style named function."""
    needle = name + "("
    start = 0
    while True:
        pos = text.find(needle, start)
        if pos < 0:
            return None
        brace = text.find("{", pos + len(needle))
        semi = text.find(";", pos + len(needle))
        if brace < 0:
            return None
        if semi >= 0 and semi < brace:
            start = semi + 1
            continue
        depth = 0
        for index in range(brace, len(text)):
            ch = text[index]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[pos:index + 1]
        return None


def read_known_vtables(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "KNOWN_VTABLES"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                break
            return {str(key): int(item) for key, item in value.items()}
    raise ValueError(f"{path}: KNOWN_VTABLES dictionary not found")


def symbol_address(symbol: str) -> int:
    return int(symbol.rsplit("_", 1)[-1], 16)


def verify(source: Path, analyzer: Path, expected_sha256: str | None = None) -> dict:
    data = source.read_bytes()
    text = data.decode("utf-8", errors="replace")
    actual_sha256 = hashlib.sha256(data).hexdigest()
    known = read_known_vtables(analyzer)

    anchor_rows = []
    for class_name, (function, symbol) in ANCHORS.items():
        body = extract_function(text, function)
        expected = symbol_address(symbol)
        analyzer_value = known.get(class_name)
        anchor_rows.append({
            "class": class_name,
            "function": function,
            "vtable_symbol": symbol,
            "expected_vtable": expected,
            "function_found": body is not None,
            "source_symbol_found": body is not None and symbol in body,
            "analyzer_vtable": analyzer_value,
            "analyzer_match": analyzer_value == expected,
        })

    factory_rows = []
    for class_name, function, rtti, constructor in FACTORY_LINKS:
        body = extract_function(text, function)
        factory_rows.append({
            "class": class_name,
            "function": function,
            "rtti_symbol": rtti,
            "constructor": constructor,
            "function_found": body is not None,
            "rtti_found": body is not None and rtti in body,
            "constructor_found": body is not None and constructor in body,
        })

    sha_match = expected_sha256 is None or actual_sha256.lower() == expected_sha256.lower()
    ready = (
        sha_match
        and all(
            row["function_found"]
            and row["source_symbol_found"]
            and row["analyzer_match"]
            for row in anchor_rows
        )
        and all(
            row["function_found"] and row["rtti_found"] and row["constructor_found"]
            for row in factory_rows
        )
    )
    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": actual_sha256,
        "expected_source_sha256": expected_sha256,
        "source_sha256_match": sha_match,
        "analyzer": str(analyzer),
        "ready": ready,
        "anchors": anchor_rows,
        "factory_links": factory_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument(
        "--analyzer",
        type=Path,
        default=Path(__file__).with_name("analyze_track_paths.py"),
        help="analyze_track_paths.py to validate",
    )
    parser.add_argument("--expect-source-sha256")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = verify(args.source, args.analyzer, args.expect_source_sha256)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
