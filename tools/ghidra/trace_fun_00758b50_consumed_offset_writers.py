#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

FORMAT = "SHIFT.Fun00758b50ConsumedOffsetWriterCandidates/1"
TARGET = "FUN_00758b50"
INPUT_FORMAT = "SHIFT.Fun00758b50InputSurfaceInventory/1"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
RETAIL_EXECUTABLE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

_FUNCTION_DEF = re.compile(r"^(?P<prefix>.+?)\b(?P<name>FUN_[0-9a-fA-F]{8})\s*\(")
_HEX_OFFSET = re.compile(r"\+\s*0x([0-9a-fA-F]+)\b")
_ASSIGNMENT = re.compile(r"(?<![=!<>])(?:\+=|-=|\*=|/=|&=|\|=|\^=|=)(?!=)")


def _is_definition_candidate(lines: list[str], index: int) -> tuple[bool, str | None]:
    stripped = lines[index].strip()
    match = _FUNCTION_DEF.match(stripped)
    if not match:
        return False, None
    prefix = match.group("prefix").strip()
    if (
        not prefix
        or prefix.endswith(("=", ",", "(", "+", "-", "*", "/"))
        or "{" in prefix
        or "}" in prefix
        or ";" in prefix
    ):
        return False, None
    lookahead = "\n".join(lines[index : min(index + 8, len(lines))])
    before_brace = lookahead.split("{", 1)[0]
    if "{" not in lookahead or ";" in before_brace:
        return False, None
    return True, match.group("name")


def _extract_functions(lines: list[str]) -> list[dict]:
    functions: list[dict] = []
    index = 0
    while index < len(lines):
        valid, name = _is_definition_candidate(lines, index)
        if not valid or name is None:
            index += 1
            continue
        depth = 0
        opened = False
        end = None
        for cursor in range(index, len(lines)):
            for char in lines[cursor]:
                if char == "{":
                    depth += 1
                    opened = True
                elif char == "}" and opened:
                    depth -= 1
                    if depth == 0:
                        end = cursor
                        break
            if end is not None:
                break
        if end is None:
            raise ValueError(f"unterminated function {name} at line {index + 1}")
        functions.append(
            {
                "name": name,
                "start_line": index + 1,
                "end_line": end + 1,
                "body": lines[index : end + 1],
            }
        )
        index = end + 1
    return functions


def _assignment_lhs(line: str) -> str | None:
    match = _ASSIGNMENT.search(line)
    if not match:
        return None
    lhs = line[: match.start()].strip()
    if not lhs or lhs.startswith(("if ", "if(", "while ", "while(", "for ", "for(")):
        return None
    return lhs


def _candidate_offsets(inventory: dict) -> list[dict]:
    if inventory.get("format") != INPUT_FORMAT:
        raise ValueError(f"expected {INPUT_FORMAT}")
    refs = inventory.get("inventory", {}).get("offset_reference_sites")
    if not isinstance(refs, list):
        raise ValueError("inventory offset_reference_sites missing")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in refs:
        offset = str(row.get("offset", "")).lower()
        if not re.fullmatch(r"0x[0-9a-f]+", offset):
            raise ValueError(f"invalid inventory offset {offset!r}")
        grouped[offset].append(row)

    candidates: list[dict] = []
    for offset, rows in grouped.items():
        target_lhs_writes = sum(bool(row.get("appears_on_assignment_lhs")) for row in rows)
        target_non_lhs_refs = len(rows) - target_lhs_writes
        if target_non_lhs_refs == 0 or target_lhs_writes != 0:
            continue
        candidates.append(
            {
                "offset": offset,
                "target_reference_count": len(rows),
                "target_non_lhs_reference_count": target_non_lhs_refs,
                "target_assignment_lhs_count": target_lhs_writes,
                "target_lines": sorted({int(row["line"]) for row in rows if "line" in row}),
            }
        )
    return sorted(candidates, key=lambda row: int(row["offset"], 16))


def _scan_direct_writers(functions: list[dict], candidates: list[dict]) -> list[dict]:
    candidate_offsets = {row["offset"] for row in candidates}
    writer_map: dict[str, list[dict]] = defaultdict(list)

    for function in functions:
        if function["name"] == TARGET:
            continue
        for relative, line in enumerate(function["body"]):
            lhs = _assignment_lhs(line)
            if lhs is None:
                continue
            lhs_offsets = {f"0x{int(raw, 16):x}" for raw in _HEX_OFFSET.findall(lhs)}
            for offset in sorted(candidate_offsets & lhs_offsets, key=lambda value: int(value, 16)):
                writer_map[offset].append(
                    {
                        "function": function["name"],
                        "function_start_line": function["start_line"],
                        "line": function["start_line"] + relative,
                        "lhs": lhs,
                        "text": line.strip(),
                    }
                )

    results: list[dict] = []
    by_offset = {row["offset"]: row for row in candidates}
    for offset in sorted(candidate_offsets, key=lambda value: int(value, 16)):
        writers = writer_map.get(offset, [])
        writer_functions = sorted({row["function"] for row in writers})
        results.append(
            {
                **by_offset[offset],
                "direct_assignment_writer_site_count": len(writers),
                "direct_assignment_writer_functions": writer_functions,
                "direct_assignment_writer_function_count": len(writer_functions),
                "direct_assignment_writer_sites": writers,
                "source_visible_direct_writer_found": bool(writers),
            }
        )

    results.sort(
        key=lambda row: (
            0 if row["source_visible_direct_writer_found"] else 1,
            row["direct_assignment_writer_function_count"] or 10**9,
            row["direct_assignment_writer_site_count"] or 10**9,
            -row["target_reference_count"],
            int(row["offset"], 16),
        )
    )
    return results


def analyze(source_path: Path, inventory_path: Path) -> dict:
    raw = source_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PINNED_SOURCE_SHA256:
        raise SystemExit(f"unexpected SHIFT.exe.c sha256: {sha}; expected {PINNED_SOURCE_SHA256}")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    candidates = _candidate_offsets(inventory)
    functions = _extract_functions(raw.decode("utf-8").splitlines())
    ranked = _scan_direct_writers(functions, candidates)

    return {
        "format": FORMAT,
        "ready": True,
        "purpose": "rank direct source-visible writer candidates for offsets consumed read-only inside FUN_00758b50; navigation evidence only",
        "source": {
            "authority": "PC retail 1.02",
            "file": source_path.name,
            "sha256": sha,
            "retail_executable_sha256": RETAIL_EXECUTABLE_SHA256,
            "target": TARGET,
        },
        "input_inventory_format": INPUT_FORMAT,
        "candidate_count": len(ranked),
        "ranked_consumed_offsets": ranked,
        "adjudication": {
            "direct_source_visible_writer_candidates_enumerated": True,
            "alias_complete_writer_ownership_proven": False,
            "callee_side_effect_writers_excluded": True,
            "matching_numeric_offset_proves_same_object": False,
            "retail_control_semantics_proven": False,
            "p1_3_control_producer_complete": False,
            "provider_count_changed": False,
        },
        "review_instructions": [
            "Start with offsets having the fewest direct writer functions and join receiver/base provenance before claiming object identity.",
            "A matching numeric offset in another function is only a writer candidate until the pointer/receiver is proven to alias the FUN_00758b50 vehicle/wheel object.",
            "Inspect callees and local aliases separately; this report intentionally does not claim alias-complete writer coverage.",
            "Do not assign throttle/brake/steering semantics until an exact PC-retail value transfer is proven from an input/control producer.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Join FUN_00758b50 read-only offset inventory to direct source-visible assignment writers."
    )
    parser.add_argument("source", type=Path, help="Path to authoritative SHIFT.exe.c")
    parser.add_argument("inventory", type=Path, help=f"Path to {INPUT_FORMAT} JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.source, args.inventory)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
