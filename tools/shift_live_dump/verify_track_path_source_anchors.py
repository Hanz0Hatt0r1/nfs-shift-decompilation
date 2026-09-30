#!/usr/bin/env python3
"""Verify track/path vtable constants against recovered SHIFT.exe.c and PE anchors."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

from extract_shift_rtti_registry import build_pe_rtti_index, extract_registry

FORMAT = "SHIFT-TRACK-PATH-SOURCE-ANCHORS/1"

ANCHORS = {
    "AIPathInfo": ("FUN_006bc3a0", "PTR_FUN_00afb150"),
    "AIArea": ("FUN_006c3a20", "PTR_FUN_00afc048"),
    "AINavigationDatabase": ("FUN_006bc7c0", "PTR_FUN_00afb198"),
    "AICarRecovery": ("FUN_006c8280", "PTR_FUN_00afc2c8"),
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

SOURCE_ONLY_VTABLE_ANCHORS = (
    ("AIPathObj", "FUN_006d0ef0", "PTR_FUN_00afc630", 0x00AFC630),
)

HIERARCHY_LINKS = (
    ("AIPathObj", "BPersistent"),
    ("AIPath", "AIPathObj"),
    ("AINavigationDatabase", "BPersistent"),
    ("AICarRecovery", "BPersistent"),
    ("AIPolylinePath", "AIPath"),
    ("AISegmentPath", "AIPath"),
)

DESTRUCTOR_CHAIN_LINKS = (
    ("AIPolylinePath", "FUN_006cc390", "PTR_FUN_00afc678", "FUN_006d0ef0"),
    ("AISegmentPath", "FUN_006ce660", "PTR_FUN_00afc930", "FUN_006d0ef0"),
)

RTTI_DESCRIPTORS = {
    "AIPathObj": 0x00C0DC64,
    "AIPath": 0x00C0D698,
    "AIPathInfo": 0x00C0D5A4,
    "AIArea": 0x00C0D588,
    "AINavigationDatabase": 0x00C0D434,
    "AICarRecovery": 0x00C0D5C8,
    "AIPolylinePath": 0x00C0D608,
    "Knot": 0x00C0D638,
    "AISpline": 0x00C0D648,
    "AISplineInfo": 0x00C0D658,
    "AISegmentPath": 0x00C0D668,
    "AIPolyPathNode": 0x00C0D678,
    "AIPathNode": 0x00C0D688,
}

# In the retail PE, AIPathInfo and the concrete polymorphic track/path classes
# above expose a tiny virtual RTTI getter of the form "mov eax, <descriptor>; ret". AISpline
# and AISplineInfo are reflected, but no dedicated getter/vtable is present via
# that same mechanism. Keep this absence explicit instead of inventing a
# concrete AISpline vtable from address proximity.
RTTI_GETTER_EXPECTED_ABSENT = {"AIPath", "AISpline", "AISplineInfo"}
PE_ONLY_VTABLES = {"AIPathObj": 0x00AFC630}


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


def scan_pe_rtti_vtables(data: bytes, known: dict[str, int]) -> dict:
    """Recover dedicated vtables through the shared PE RTTI index."""
    pe = build_pe_rtti_index(data)
    rows = []
    for class_name, descriptor in RTTI_DESCRIPTORS.items():
        getters = list(pe["getter_addresses"].get(descriptor, ()))
        candidates = list(pe["vtable_candidates"].get(descriptor, ()))
        analyzer_vtable = known.get(class_name)
        pe_only_vtable = PE_ONLY_VTABLES.get(class_name)
        expected_vtable = (
            analyzer_vtable if analyzer_vtable is not None else pe_only_vtable
        )
        expected_absent = class_name in RTTI_GETTER_EXPECTED_ABSENT
        if expected_absent:
            match = not getters and not candidates and expected_vtable is None
        else:
            match = (
                expected_vtable is not None
                and len(getters) == 1
                and candidates == [expected_vtable]
            )
        rows.append({
            "class": class_name,
            "descriptor": descriptor,
            "getter_addresses": getters,
            "candidate_vtables": candidates,
            "analyzer_vtable": analyzer_vtable,
            "pe_only_vtable": pe_only_vtable,
            "expected_vtable": expected_vtable,
            "expected_dedicated_vtable_absent": expected_absent,
            "match": match,
        })

    return {
        "image_base": pe["image_base"],
        "rows": rows,
        "ready": all(row["match"] for row in rows),
    }


def verify(
    source: Path,
    analyzer: Path,
    expected_sha256: str | None = None,
    exe: Path | None = None,
    expected_exe_sha256: str | None = None,
) -> dict:
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

    source_only_rows = []
    for class_name, function, symbol, expected in SOURCE_ONLY_VTABLE_ANCHORS:
        body = extract_function(text, function)
        source_only_rows.append({
            "class": class_name,
            "function": function,
            "vtable_symbol": symbol,
            "expected_vtable": expected,
            "function_found": body is not None,
            "source_symbol_found": body is not None and symbol in body,
            "symbol_address_match": symbol_address(symbol) == expected,
        })

    registry = extract_registry(source, exe)
    registry_by_name = {
        row["name"]: row
        for row in registry["classes"]
        if row.get("name") is not None
    }
    hierarchy_rows = []
    for class_name, expected_parent in HIERARCHY_LINKS:
        row = registry_by_name.get(class_name)
        hierarchy_rows.append({
            "class": class_name,
            "expected_parent": expected_parent,
            "class_found": row is not None,
            "actual_parent": row.get("parent_class") if row is not None else None,
            "match": row is not None and row.get("parent_class") == expected_parent,
        })

    destructor_rows = []
    for class_name, function, own_vtable, base_destructor in DESTRUCTOR_CHAIN_LINKS:
        body = extract_function(text, function)
        destructor_rows.append({
            "class": class_name,
            "function": function,
            "own_vtable_symbol": own_vtable,
            "base_destructor": base_destructor,
            "function_found": body is not None,
            "own_vtable_found": body is not None and own_vtable in body,
            "base_destructor_found": body is not None and base_destructor in body,
        })

    sha_match = expected_sha256 is None or actual_sha256.lower() == expected_sha256.lower()
    pe_report = None
    exe_sha256 = None
    exe_sha_match = None
    if exe is not None:
        exe_data = exe.read_bytes()
        exe_sha256 = hashlib.sha256(exe_data).hexdigest()
        exe_sha_match = (
            expected_exe_sha256 is None
            or exe_sha256.lower() == expected_exe_sha256.lower()
        )
        pe_report = scan_pe_rtti_vtables(exe_data, known)

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
        and all(
            row["function_found"]
            and row["source_symbol_found"]
            and row["symbol_address_match"]
            for row in source_only_rows
        )
        and all(row["match"] for row in hierarchy_rows)
        and all(
            row["function_found"]
            and row["own_vtable_found"]
            and row["base_destructor_found"]
            for row in destructor_rows
        )
        and (pe_report is None or (bool(exe_sha_match) and pe_report["ready"]))
    )
    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": actual_sha256,
        "expected_source_sha256": expected_sha256,
        "source_sha256_match": sha_match,
        "analyzer": str(analyzer),
        "exe": str(exe) if exe is not None else None,
        "exe_sha256": exe_sha256,
        "expected_exe_sha256": expected_exe_sha256,
        "exe_sha256_match": exe_sha_match,
        "ready": ready,
        "anchors": anchor_rows,
        "source_only_vtable_anchors": source_only_rows,
        "factory_links": factory_rows,
        "hierarchy_links": hierarchy_rows,
        "destructor_chain_links": destructor_rows,
        "pe_rtti_vtables": pe_report,
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
    parser.add_argument("--exe", type=Path, help="retail SHIFT.exe for PE RTTI/vtable validation")
    parser.add_argument("--expect-exe-sha256")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = verify(
        args.source,
        args.analyzer,
        args.expect_source_sha256,
        args.exe,
        args.expect_exe_sha256,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
