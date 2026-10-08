#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT.Fun00765c40WriteSurfaceInventory/1"
TARGET = "FUN_00765c40"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
RETAIL_EXECUTABLE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

_DEFINITION = re.compile(rf"^(?P<prefix>.+?)\b{re.escape(TARGET)}\s*\(")
_FUNCTION_TOKEN = re.compile(r"\b(FUN_[0-9a-fA-F]{8})\s*\(")
_GLOBAL_TOKEN = re.compile(r"\b(?:DAT|PTR|LAB|UNK)_[0-9a-fA-F]{8}\b")
_HEX_OFFSET = re.compile(r"\+\s*0x([0-9a-fA-F]+)\b")
_ASSIGNMENT = re.compile(r"(?<![=!<>])(?:\+=|-=|\*=|/=|&=|\|=|\^=|=)(?!=)")


def _find_definition(lines: list[str]) -> int:
    candidates: list[int] = []
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        match = _DEFINITION.match(stripped)
        if not match:
            continue
        prefix = match.group("prefix").strip()
        if not prefix or prefix.endswith(("=", ",", "(", "+", "-", "*", "/")):
            continue
        lookahead = "\n".join(lines[index : min(index + 8, len(lines))])
        before_brace = lookahead.split("{", 1)[0]
        if "{" not in lookahead or ";" in before_brace:
            continue
        candidates.append(index)
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one {TARGET} definition, found {[value + 1 for value in candidates]}"
        )
    return candidates[0]


def _extract_function(lines: list[str]) -> tuple[int, int, list[str]]:
    start = _find_definition(lines)
    depth = 0
    opened = False
    for index in range(start, len(lines)):
        for char in lines[index]:
            if char == "{":
                depth += 1
                opened = True
            elif char == "}" and opened:
                depth -= 1
                if depth == 0:
                    return start + 1, index + 1, lines[start : index + 1]
    raise ValueError(f"unterminated {TARGET} body starting at line {start + 1}")


def _assignment_site(line_no: int, line: str) -> dict | None:
    match = _ASSIGNMENT.search(line)
    if not match:
        return None
    lhs = line[: match.start()].strip()
    if not lhs or lhs.startswith(("if ", "if(", "while ", "while(", "for ", "for(")):
        return None
    return {
        "line": line_no,
        "operator": match.group(0),
        "lhs": lhs,
        "text": line.strip(),
        "mentions_param_1": "param_1" in line,
        "mentions_this": "this" in line,
    }


def _inventory(start_line: int, body: list[str]) -> dict:
    assignments: list[dict] = []
    calls: list[dict] = []
    globals_seen: list[dict] = []
    offsets: Counter[str] = Counter()

    for relative, line in enumerate(body):
        line_no = start_line + relative
        assignment = _assignment_site(line_no, line)
        if assignment is not None:
            assignments.append(assignment)

        for callee in _FUNCTION_TOKEN.findall(line):
            if callee != TARGET:
                calls.append({"line": line_no, "callee": callee})
        for token in _GLOBAL_TOKEN.findall(line):
            globals_seen.append({"line": line_no, "token": token})
        for raw in _HEX_OFFSET.findall(line):
            offsets[f"0x{int(raw, 16):x}"] += 1

    return {
        "assignment_sites": assignments,
        "assignment_count": len(assignments),
        "param_1_assignment_sites": [row for row in assignments if row["mentions_param_1"]],
        "this_assignment_sites": [row for row in assignments if row["mentions_this"]],
        "direct_call_sites": calls,
        "unique_direct_callees": sorted({row["callee"] for row in calls}),
        "global_reference_sites": globals_seen,
        "unique_global_references": sorted({row["token"] for row in globals_seen}),
        "hex_offset_frequency": dict(
            sorted(offsets.items(), key=lambda item: (int(item[0], 16), item[0]))
        ),
    }


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PINNED_SOURCE_SHA256:
        raise SystemExit(f"unexpected SHIFT.exe.c sha256: {sha}; expected {PINNED_SOURCE_SHA256}")

    lines = raw.decode("utf-8").splitlines()
    start_line, end_line, body = _extract_function(lines)
    inventory = _inventory(start_line, body)

    return {
        "format": FORMAT,
        "ready": True,
        "purpose": "raw FUN_00765c40 assignment/call inventory for P1.2b side-effect audit; not a semantic ownership contract",
        "source": {
            "authority": "PC retail 1.02",
            "file": path.name,
            "sha256": sha,
            "retail_executable_sha256": RETAIL_EXECUTABLE_SHA256,
            "target": TARGET,
            "start_line": start_line,
            "end_line": end_line,
        },
        "inventory": inventory,
        "known_closed_surface_hints": [
            "HDVehicle+0x38dc returned cache handle",
            "HDVehicle+0x38e0 hit/miss scalar",
            "four wheel +0x738 f64 load terms",
        ],
        "adjudication": {
            "residual_side_effects_classified": False,
            "absence_of_other_writes_proven": False,
            "safe_to_remove_FUN_00765c40_provider": False,
            "manual_pointer_and_alias_review_required": True,
        },
        "review_instructions": [
            "Classify every assignment site against already-closed query/cache/scalar/load-term contracts.",
            "Trace aliases before treating a local-pointer store as an HDVehicle or wheel-runtime write.",
            "Treat calls as possible side-effect carriers until their callee contracts prove otherwise.",
            "Do not infer absence of writes from param_1_assignment_sites alone; local aliases may hide object writes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory pinned PC-retail FUN_00765c40 assignments/calls for the residual side-effect audit."
    )
    parser.add_argument("source", type=Path, help="Path to authoritative SHIFT.exe.c")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.source)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
