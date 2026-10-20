#!/usr/bin/env python3
"""Audit Ghidra P-code instruction exports without loading the whole corpus.

Structural warnings are *candidates*, not proof of corruption. Only verified
instruction requirements (addresses and original PE bytes) are hard failures.
No generated code, retail executable, or local resource is committed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct

FORMAT = "SHIFT.PcodeCorpusAudit/1"
REQUIREMENTS_FORMAT = "SHIFT.PcodeVerifiedInstructionRequirements/1"
ROW_FORMATS = {
    "SHIFT.GhidraFunctionInstructions/2",
    "REVENGINSTR.GhidraFunctionInstructions/1",
}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def address(value: str) -> int:
    if not isinstance(value, str) or not value.startswith(("0x", "0X")):
        raise ValueError(f"expected hexadecimal address: {value!r}")
    return int(value, 16)


def load_requirements(path: Path) -> dict[int, dict[int, str]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("format") != REQUIREMENTS_FORMAT or not isinstance(obj.get("functions"), dict):
        raise ValueError(f"{path}: invalid verified instruction requirements")
    result = {}
    for key, entries in obj["functions"].items():
        function = address(key)
        if function in result or not isinstance(entries, list) or not entries:
            raise ValueError(f"invalid or duplicate function requirements: {key}")
        required = {}
        for entry in entries:
            offset = address(entry["address"])
            raw = entry["bytes"]
            if (not isinstance(raw, str) or not raw or len(raw) % 2
                    or bytes.fromhex(raw).hex() != raw.lower() or offset in required):
                raise ValueError(f"{key}: invalid or duplicate instruction requirement")
            required[offset] = raw.lower()
        result[function] = required
    return result


def pe_bytes(path: Path, addresses: list[tuple[int, bytes]]) -> dict[int, bytes]:
    """Read original PE *file-backed* code at verified virtual addresses only."""
    blob = path.read_bytes()
    if len(blob) < 0x40 or blob[:2] != b"MZ":
        raise ValueError("expected a PE32 image")
    pe_offset = struct.unpack_from("<I", blob, 0x3c)[0]
    if pe_offset + 24 > len(blob) or blob[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    number = struct.unpack_from("<H", blob, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", blob, pe_offset + 20)[0]
    optional = pe_offset + 24
    if optional + optional_size > len(blob) or optional_size < 32:
        raise ValueError("invalid PE optional header")
    if struct.unpack_from("<H", blob, optional)[0] != 0x10b:
        raise ValueError("requires original PE32 image, not PE32+")
    image_base = struct.unpack_from("<I", blob, optional + 28)[0]
    sections = []
    section_offset = optional + optional_size
    if section_offset + 40 * number > len(blob):
        raise ValueError("truncated PE sections")
    for index in range(number):
        off = section_offset + index * 40
        raw_size, rva, raw_pointer = struct.unpack_from("<III", blob, off + 16)
        virtual_size = struct.unpack_from("<I", blob, off + 8)[0]
        sections.append((rva, max(raw_size, virtual_size), raw_size, raw_pointer))
    observed = {}
    for va, expected in addresses:
        rva = va - image_base
        locations = [
            pointer + rva - start
            for start, extent, raw_size, pointer in sections
            if start <= rva and rva + len(expected) <= start + extent
            and rva + len(expected) <= start + raw_size
        ]
        if len(locations) != 1 or locations[0] + len(expected) > len(blob):
            raise ValueError(f"verified instruction 0x{va:08x} is not uniquely file-backed")
        begin = locations[0]
        observed[va] = blob[begin:begin + len(expected)]
    return observed


def audit(corpus: Path, requirements: dict[int, dict[int, str]],
          sample_limit: int = 30) -> dict:
    if sample_limit < 0:
        raise ValueError("sample limit must be nonnegative")
    counters = Counter()
    problems = []
    warnings = []
    missing_requirements = set(requirements)
    opener = gzip.open if corpus.suffix == ".gz" else open
    with opener(corpus, "rt", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict) or row.get("format") not in ROW_FORMATS:
                raise ValueError(f"{corpus}:{line_no}: unsupported corpus row")
            counters["rows"] += 1
            if row.get("found") is not True:
                counters["missing_function_rows"] += 1
                continue
            function = row.get("function")
            instructions = row.get("instructions")
            if not isinstance(function, dict) or not isinstance(instructions, list):
                raise ValueError(f"{corpus}:{line_no}: malformed function record")
            entry = address(function["address"])
            counters["functions"] += 1
            if row.get("instruction_count") != len(instructions):
                problems.append({"function": f"0x{entry:08x}", "kind": "count_mismatch",
                                 "line": line_no})
                counters["count_mismatch"] += 1
            if entry in missing_requirements:
                missing_requirements.remove(entry)
            seen = {}
            previous_end = -1
            terminal = False
            for instruction in instructions:
                start = address(instruction["address"])
                data = bytes.fromhex(instruction["bytes"])
                if not data:
                    raise ValueError(f"{corpus}:{line_no}: empty instruction bytes")
                if start <= previous_end:
                    counters["overlapping_instructions"] += 1
                    if len(problems) < sample_limit:
                        problems.append({"function": f"0x{entry:08x}", "kind": "overlap",
                                         "address": f"0x{start:08x}"})
                previous_end = max(previous_end, start + len(data) - 1)
                seen[start] = data.hex()
                flow = str(instruction.get("flow_type", "")).upper()
                if "TERMINATOR" in flow or instruction.get("mnemonic", "").upper().startswith(
                    ("RET", "IRET")
                ):
                    terminal = True
            counters["instructions"] += len(instructions)
            if not terminal:
                counters["no_observed_return"] += 1
                if len(warnings) < sample_limit:
                    warnings.append({"function": f"0x{entry:08x}",
                                     "kind": "no_observed_return",
                                     "note": "may be a tail call or non-returning function"})
            if entry in requirements:
                for location, expected in requirements[entry].items():
                    counters["required_instructions"] += 1
                    actual = seen.get(location)
                    if actual != expected:
                        counters["required_failures"] += 1
                        if len(problems) < sample_limit:
                            problems.append({
                                "function": f"0x{entry:08x}", "kind": "verified_instruction_mismatch",
                                "address": f"0x{location:08x}",
                                "expected": expected, "actual": actual,
                            })
    for function in sorted(missing_requirements):
        counters["missing_required_functions"] += 1
        if len(problems) < sample_limit:
            problems.append({"function": f"0x{function:08x}",
                             "kind": "missing_required_function"})
    failures = (counters["count_mismatch"] + counters["overlapping_instructions"]
                + counters["required_failures"] + counters["missing_required_functions"])
    return {
        "format": FORMAT,
        "status": "blocked" if failures else "passed",
        "counters": dict(counters),
        "problem_samples": problems,
        "warning_samples": warnings,
        "behavioral_parity_proven": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path, help=".jsonl or .jsonl.gz")
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--pe", type=Path, help="optional original PE byte verification")
    parser.add_argument("--expected-pe-sha256", help="optional pinned SHA-256 for --pe")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-limit", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        requirements = load_requirements(args.requirements)
        if args.expected_pe_sha256 and not args.pe:
            raise ValueError("--expected-pe-sha256 requires --pe")
        if args.pe:
            pe_hash = sha256(args.pe)
            if args.expected_pe_sha256 and pe_hash != args.expected_pe_sha256.lower():
                raise ValueError("PE SHA-256 does not match the requested retail image")
            pairs = [(a, bytes.fromhex(b)) for entries in requirements.values()
                     for a, b in entries.items()]
            actual = pe_bytes(args.pe, pairs)
            for offset, expected in pairs:
                if actual[offset] != expected:
                    raise ValueError(f"required bytes at 0x{offset:08x} differ from original PE")
        report = audit(args.corpus, requirements, args.sample_limit)
        report["input"] = {
            "corpus_sha256": sha256(args.corpus),
            "requirements_sha256": sha256(args.requirements),
            "pe_sha256": sha256(args.pe) if args.pe else None,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
