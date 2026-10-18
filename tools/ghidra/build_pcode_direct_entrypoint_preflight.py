#!/usr/bin/env python3
"""Preflight direct CALL/JMP targets against the frozen P-code function corpus.

The report is intentionally structural. It identifies direct control-flow targets
that are not normal Ghidra function starts so they can be reviewed/exported in a
batch before retail execution reaches them one at a time.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, Iterable, TextIO

COMPACT_FORMATS = {
    "REVENGINSTR.GhidraCompactInstructionStream/1",
    "SHIFT.GhidraCompactInstructionStream/1",
}
FUNCTION_FORMATS = {
    "REVENGINSTR.GhidraFunctionInstructions/1",
    "SHIFT.GhidraFunctionInstructions/2",
}
FORMAT = "NFSShift.PcodeDirectEntrypointPreflight/1"


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _rows(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with _open_text(path) as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield line_no, row


def _address(value: Any, *, field: str) -> int:
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        result = int(value, 0)
    else:
        raise ValueError(f"{field}: expected address")
    if result < 0 or result > 0xFFFFFFFF:
        raise ValueError(f"{field}: address outside x86-32 range")
    return result


def _compact_transfers(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], set[int]]:
    header: dict[str, Any] | None = None
    transfers: list[dict[str, Any]] = []
    direct_targets: set[int] = set()

    for line_no, row in _rows(path):
        if row.get("format") not in COMPACT_FORMATS:
            raise ValueError(f"{path}:{line_no}: unexpected compact stream format")
        kind = row.get("kind")
        if kind == "header":
            if header is not None:
                raise ValueError(f"{path}:{line_no}: duplicate compact header")
            header = row
            continue
        if kind != "instruction":
            raise ValueError(f"{path}:{line_no}: unexpected compact row kind")

        mnemonic = str(row.get("mnemonic") or "").upper()
        if mnemonic not in {"CALL", "JMP"}:
            continue
        flows = row.get("flows")
        if not isinstance(flows, list) or len(flows) != 1:
            continue
        try:
            source = _address(row.get("address"), field="instruction.address")
            target = _address(flows[0], field="instruction.flows[0]")
        except (TypeError, ValueError):
            continue
        transfers.append(
            {
                "source": source,
                "target": target,
                "mnemonic": mnemonic,
            }
        )
        direct_targets.add(target)

    if header is None:
        raise ValueError(f"{path}: compact stream has no header")
    return header, transfers, direct_targets


def _target_presence(path: Path, targets: set[int]) -> set[int]:
    present: set[int] = set()
    if not targets:
        return present
    for line_no, row in _rows(path):
        if row.get("format") not in COMPACT_FORMATS:
            raise ValueError(f"{path}:{line_no}: unexpected compact stream format")
        if row.get("kind") != "instruction":
            continue
        try:
            address = _address(row.get("address"), field="instruction.address")
        except (TypeError, ValueError):
            continue
        if address in targets:
            present.add(address)
            if len(present) == len(targets):
                break
    return present


def _function_owners(
    path: Path, interesting: set[int]
) -> tuple[dict[int, int], set[int], int]:
    owners: dict[int, int] = {}
    starts: set[int] = set()
    function_count = 0

    for line_no, row in _rows(path):
        if row.get("format") not in FUNCTION_FORMATS:
            raise ValueError(f"{path}:{line_no}: unexpected function corpus format")
        if row.get("found") is not True:
            continue
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, dict) or not isinstance(instructions, list):
            raise ValueError(f"{path}:{line_no}: malformed function row")
        start = _address(function.get("address"), field="function.address")
        starts.add(start)
        function_count += 1
        for instruction in instructions:
            if not isinstance(instruction, dict):
                raise ValueError(f"{path}:{line_no}: malformed instruction row")
            address = _address(instruction.get("address"), field="instruction.address")
            if address in interesting:
                previous = owners.setdefault(address, start)
                if previous != start:
                    raise ValueError(
                        f"0x{address:08x}: instruction belongs to multiple functions"
                    )
    return owners, starts, function_count


def build(compact: Path, corpus: Path) -> dict[str, Any]:
    header, transfers, targets = _compact_transfers(compact)
    present_targets = _target_presence(compact, targets)
    interesting = {row["source"] for row in transfers} | targets
    owners, starts, function_count = _function_owners(corpus, interesting)

    candidates: list[dict[str, Any]] = []
    counts = {
        "covered_function_entry": 0,
        "internal_jump": 0,
        "call_into_function_interior": 0,
        "jump_into_other_function_interior": 0,
        "orphan_direct_target": 0,
        "outside_instruction_stream": 0,
    }

    for transfer in transfers:
        source = transfer["source"]
        target = transfer["target"]
        mnemonic = transfer["mnemonic"]
        source_owner = owners.get(source)
        target_owner = owners.get(target)

        if target in starts:
            counts["covered_function_entry"] += 1
            continue
        if (
            mnemonic == "JMP"
            and source_owner is not None
            and target_owner == source_owner
        ):
            counts["internal_jump"] += 1
            continue

        if target_owner is not None:
            if mnemonic == "CALL":
                classification = "call_into_function_interior"
            else:
                classification = "jump_into_other_function_interior"
        elif target in present_targets:
            classification = "orphan_direct_target"
        else:
            classification = "outside_instruction_stream"

        counts[classification] += 1
        if classification == "outside_instruction_stream":
            continue
        candidates.append(
            {
                "source": f"0x{source:08x}",
                "source_function": (
                    f"0x{source_owner:08x}" if source_owner is not None else None
                ),
                "mnemonic": mnemonic,
                "target": f"0x{target:08x}",
                "target_function": (
                    f"0x{target_owner:08x}" if target_owner is not None else None
                ),
                "classification": classification,
                "target_is_instruction": target in present_targets,
            }
        )

    candidates.sort(
        key=lambda row: (
            int(row["target"], 16),
            int(row["source"], 16),
            row["mnemonic"],
        )
    )
    unique_targets = sorted({row["target"] for row in candidates})

    return {
        "format": FORMAT,
        "program": header.get("program"),
        "language_id": header.get("language_id"),
        "function_corpus_count": function_count,
        "direct_transfer_count": len(transfers),
        "classification_counts": counts,
        "supplemental_entrypoint_candidate_count": len(candidates),
        "supplemental_entrypoint_unique_target_count": len(unique_targets),
        "supplemental_entrypoint_unique_targets": unique_targets,
        "candidates": candidates,
        "scope": {
            "direct_call_and_jmp_only": True,
            "indirect_transfers_included": False,
            "same_function_direct_jumps_ignored": True,
            "outside_instruction_stream_targets_are_not_candidates": True,
            "candidate_is_not_semantic_proof": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compact_stream", type=Path)
    parser.add_argument("function_corpus", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build(args.compact_stream, args.function_corpus)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
