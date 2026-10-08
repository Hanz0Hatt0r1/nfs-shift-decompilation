#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT.Fun00758b50InputSurfaceInventory/1"
TARGET = "FUN_00758b50"
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
        if (
            not prefix
            or prefix.endswith(("=", ",", "(", "+", "-", "*", "/"))
            or "{" in prefix
            or "}" in prefix
            or ";" in prefix
        ):
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
    }


def _inventory(start_line: int, body: list[str]) -> dict:
    assignments: list[dict] = []
    calls: list[dict] = []
    globals_seen: list[dict] = []
    offset_sites: list[dict] = []
    offsets: Counter[str] = Counter()

    for relative, line in enumerate(body):
        line_no = start_line + relative
        assignment = _assignment_site(line_no, line)
        if assignment is not None:
            assignments.append(assignment)

        line_offsets = [f"0x{int(raw, 16):x}" for raw in _HEX_OFFSET.findall(line)]
        for offset in line_offsets:
            offsets[offset] += 1
            offset_sites.append(
                {
                    "line": line_no,
                    "offset": offset,
                    "text": line.strip(),
                    "line_has_assignment": assignment is not None,
                    "appears_on_assignment_lhs": bool(
                        assignment is not None and offset in assignment["lhs"].lower()
                    ),
                }
            )

        for callee in _FUNCTION_TOKEN.findall(line):
            if callee != TARGET:
                calls.append({"line": line_no, "callee": callee})
        for token in _GLOBAL_TOKEN.findall(line):
            globals_seen.append({"line": line_no, "token": token})

    return {
        "assignment_sites": assignments,
        "assignment_count": len(assignments),
        "offset_reference_sites": offset_sites,
        "hex_offset_frequency": dict(
            sorted(offsets.items(), key=lambda item: (int(item[0], 16), item[0]))
        ),
        "direct_call_sites": calls,
        "unique_direct_callees": sorted({row["callee"] for row in calls}),
        "global_reference_sites": globals_seen,
        "unique_global_references": sorted({row["token"] for row in globals_seen}),
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
        "purpose": "raw FUN_00758b50 offset/read-write/call inventory for P1.3 wheel/control producer tracing; navigation evidence only",
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
        "known_structural_anchors": {
            "wheel_state_base": "0x848",
            "wheel_runtime_base": "0x400",
            "wheel_stride": "0xa80",
            "wheel_count": 4,
        },
        "adjudication": {
            "retail_control_value_producer_identified": False,
            "offset_reference_equals_control_semantics": False,
            "complete_alias_aware_writer_surface_proven": False,
            "manual_pointer_and_alias_review_required": True,
            "provider_count_changed": False,
        },
        "review_instructions": [
            "Classify target-body offset references as reads, writes, local aliases, or unrelated arithmetic before assigning ownership.",
            "Trace source values of consumed wheel/vehicle fields upstream to exact writers; a matching numeric offset elsewhere is not sufficient.",
            "Treat every direct callee as a possible producer/side-effect carrier until an existing contract closes it.",
            "Do not map native VehicleControlIntent fields onto retail offsets without an exact PC-retail value-transfer proof.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory pinned PC-retail FUN_00758b50 offset references and calls for P1.3 producer tracing."
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
