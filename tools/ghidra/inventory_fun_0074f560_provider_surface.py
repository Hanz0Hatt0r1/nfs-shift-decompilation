#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT.Fun0074f560ProviderSurfaceInventory/1"
TARGET = "FUN_0074f560"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
RETAIL_EXECUTABLE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

_FUNCTION_TOKEN = re.compile(r"\b(FUN_[0-9a-fA-F]{8})\s*\(")
_GLOBAL_TOKEN = re.compile(r"\b(?:DAT|PTR|LAB|UNK)_[0-9a-fA-F]{8}\b")
_HEX_OFFSET = re.compile(r"\+\s*0x([0-9a-fA-F]+)\b")
_DEFINITION = re.compile(
    rf"^(?P<prefix>.+?)\b{re.escape(TARGET)}\s*\(",
)


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
        display = [value + 1 for value in candidates]
        raise ValueError(f"expected exactly one {TARGET} definition, found {display}")
    return candidates[0]


def _extract_function(lines: list[str]) -> tuple[int, int, list[str]]:
    start = _find_definition(lines)
    brace_depth = 0
    seen_open = False

    for index in range(start, len(lines)):
        line = lines[index]
        for char in line:
            if char == "{":
                brace_depth += 1
                seen_open = True
            elif char == "}" and seen_open:
                brace_depth -= 1
                if brace_depth == 0:
                    return start + 1, index + 1, lines[start : index + 1]

    raise ValueError(f"unterminated {TARGET} body starting at source line {start + 1}")


def _is_potential_indirect_call(line: str) -> bool:
    compact = line.replace(" ", "")
    if TARGET in line:
        return False
    markers = (
        "(**",
        "(*(code*)",
        "(*(undefined",
        "(*pcVar",
        "(*puVar",
        "(*piVar",
        "(*pFVar",
    )
    return any(marker in compact for marker in markers)


def _inventory_body(start_line: int, body: list[str]) -> dict:
    direct_calls: list[dict] = []
    globals_seen: list[dict] = []
    indirect_calls: list[dict] = []
    offset_counter: Counter[str] = Counter()

    for relative, line in enumerate(body):
        line_no = start_line + relative

        for callee in _FUNCTION_TOKEN.findall(line):
            if callee != TARGET:
                direct_calls.append({"line": line_no, "callee": callee})

        for token in _GLOBAL_TOKEN.findall(line):
            globals_seen.append({"line": line_no, "token": token})

        for raw_offset in _HEX_OFFSET.findall(line):
            offset_counter[f"0x{int(raw_offset, 16):x}"] += 1

        if _is_potential_indirect_call(line):
            indirect_calls.append({"line": line_no, "text": line.strip()})

    unique_direct = sorted({row["callee"] for row in direct_calls})
    unique_globals = sorted({row["token"] for row in globals_seen})

    return {
        "direct_call_sites": direct_calls,
        "unique_direct_callees": unique_direct,
        "global_reference_sites": globals_seen,
        "unique_global_references": unique_globals,
        "potential_indirect_call_sites": indirect_calls,
        "hex_offset_frequency": dict(
            sorted(offset_counter.items(), key=lambda item: (int(item[0], 16), item[0]))
        ),
    }


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    if sha256 != PINNED_SOURCE_SHA256:
        raise SystemExit(
            f"unexpected SHIFT.exe.c sha256: {sha256}; expected {PINNED_SOURCE_SHA256}"
        )

    lines = raw.decode("utf-8").splitlines()
    start_line, end_line, body = _extract_function(lines)
    inventory = _inventory_body(start_line, body)

    return {
        "format": FORMAT,
        "ready": True,
        "purpose": "raw static inventory only; no collision-provider semantic promotion",
        "source": {
            "authority": "PC retail 1.02",
            "file": path.name,
            "sha256": sha256,
            "retail_executable_sha256": RETAIL_EXECUTABLE_SHA256,
            "target": TARGET,
            "start_line": start_line,
            "end_line": end_line,
        },
        "inventory": inventory,
        "adjudication": {
            "provider_object_identified": False,
            "scene_query_call_identified": False,
            "physx_class_name_proven": False,
            "safe_to_replace_with_guessed_track_query": False,
            "requires_manual_pointer_provenance_review": True,
        },
        "review_instructions": [
            "Start from potential_indirect_call_sites and direct callees; preserve pointer provenance before naming an owner.",
            "Use global_reference_sites and offset frequency only as navigation evidence, not semantic identity.",
            "Bind any promoted lower call back to the already-recovered FUN_007b0710 0x58-byte returned surface-record contract.",
            "Do not infer PhysX class names from vtable-shaped code alone.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory the pinned PC-retail FUN_0074f560 provider surface without guessing semantics."
    )
    parser.add_argument("source", type=Path, help="Path to the authoritative SHIFT.exe.c export")
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
