#!/usr/bin/env python3
"""Summarize repeated source-to-backend memory-wrapper provenance patterns.

This layer groups already-joined mechanical argument provenance by wrapper,
backend target and physical backend parameter storage. It reports recurrence and
stability only; it never assigns semantic roles such as allocation size, pool,
alignment or release flags.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

INPUT_FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
FORMAT = "SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != INPUT_FORMAT:
        raise ValueError(f"{path}: expected {INPUT_FORMAT}")
    return payload


def _argument_metadata(row: dict[str, Any], index: int | None) -> dict[str, Any] | None:
    if index is None:
        return None
    for argument in row.get("arguments") or []:
        if not isinstance(argument, dict):
            continue
        if argument.get("index") == index:
            return argument
    return None


def _histogram(counter: Counter[Any], key_name: str) -> list[dict[str, Any]]:
    def sort_key(item: tuple[Any, int]) -> tuple[str, str]:
        value = item[0]
        return (type(value).__name__, str(value))

    return [
        {key_name: value, "occurrence_count": count}
        for value, count in sorted(counter.items(), key=sort_key)
    ]


def summarize_memory_wrapper_argument_patterns(path: Path) -> dict[str, Any]:
    joined = _load(path)
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in joined.get("rows") or []:
        if not isinstance(row, dict):
            continue
        wrapper = str(row.get("wrapper") or "")
        caller = str(row.get("caller") or "")
        ghidra_crosschecked = row.get("ghidra_crosschecked_join") is True
        for backend in row.get("backend_calls") or []:
            if not isinstance(backend, dict):
                continue
            target = str(backend.get("target") or "")
            target_name = backend.get("target_name")
            instruction = backend.get("instruction")
            for argument in backend.get("arguments") or []:
                if not isinstance(argument, dict):
                    continue
                storage = str(argument.get("backend_storage") or "")
                key = (wrapper, target, storage)
                bucket = buckets.setdefault(
                    key,
                    {
                        "wrapper": wrapper,
                        "backend_target": target,
                        "backend_target_names": set(),
                        "backend_instructions": set(),
                        "backend_storage": storage,
                        "occurrence_count": 0,
                        "callers": set(),
                        "ghidra_crosschecked_occurrence_count": 0,
                        "source_mapped_occurrence_count": 0,
                        "wrapper_internal_occurrence_count": 0,
                        "unresolved_occurrence_count": 0,
                        "source_argument_indices": Counter(),
                        "source_argument_expressions": Counter(),
                        "exact_source_integer_literals": Counter(),
                        "wrapper_internal_sources": Counter(),
                        "forwarding_sources": Counter(),
                    },
                )
                bucket["occurrence_count"] += 1
                if caller:
                    bucket["callers"].add(caller)
                if isinstance(target_name, str) and target_name:
                    bucket["backend_target_names"].add(target_name)
                if isinstance(instruction, str) and instruction:
                    bucket["backend_instructions"].add(instruction)
                if ghidra_crosschecked:
                    bucket["ghidra_crosschecked_occurrence_count"] += 1

                forwarding_source = str(argument.get("forwarding_source") or "unresolved")
                bucket["forwarding_sources"][forwarding_source] += 1

                if argument.get("source_argument_mapped") is True:
                    bucket["source_mapped_occurrence_count"] += 1
                    source_index = argument.get("source_argument_index")
                    if isinstance(source_index, int):
                        bucket["source_argument_indices"][source_index] += 1
                        metadata = _argument_metadata(row, source_index)
                        if metadata is not None:
                            expression = metadata.get("expression")
                            if isinstance(expression, str):
                                bucket["source_argument_expressions"][expression] += 1
                            if metadata.get("is_exact_integer_literal") is True:
                                literal = metadata.get("exact_integer_value")
                                if isinstance(literal, int):
                                    bucket["exact_source_integer_literals"][literal] += 1
                elif argument.get("wrapper_internal_source") is True:
                    bucket["wrapper_internal_occurrence_count"] += 1
                    bucket["wrapper_internal_sources"][forwarding_source] += 1
                else:
                    bucket["unresolved_occurrence_count"] += 1

    patterns: list[dict[str, Any]] = []
    for key in sorted(buckets):
        bucket = buckets[key]
        occurrence_count = int(bucket["occurrence_count"])
        mapped_count = int(bucket["source_mapped_occurrence_count"])
        internal_count = int(bucket["wrapper_internal_occurrence_count"])
        unresolved_count = int(bucket["unresolved_occurrence_count"])
        index_counter: Counter[int] = bucket["source_argument_indices"]
        internal_counter: Counter[str] = bucket["wrapper_internal_sources"]

        stable_source_index = None
        if mapped_count == occurrence_count and unresolved_count == 0 and internal_count == 0 and len(index_counter) == 1:
            stable_source_index = next(iter(index_counter))

        stable_internal_source = None
        if internal_count == occurrence_count and unresolved_count == 0 and mapped_count == 0 and len(internal_counter) == 1:
            stable_internal_source = next(iter(internal_counter))

        if stable_source_index is not None:
            mapping_kind = "stable-source-argument"
        elif stable_internal_source is not None:
            mapping_kind = "stable-wrapper-internal"
        elif unresolved_count == occurrence_count:
            mapping_kind = "unresolved"
        else:
            mapping_kind = "mixed"

        ghidra_count = int(bucket["ghidra_crosschecked_occurrence_count"])
        patterns.append(
            {
                "wrapper": bucket["wrapper"],
                "backend_target": bucket["backend_target"],
                "backend_target_names": sorted(bucket["backend_target_names"]),
                "backend_instructions": sorted(bucket["backend_instructions"]),
                "backend_storage": bucket["backend_storage"],
                "occurrence_count": occurrence_count,
                "caller_count": len(bucket["callers"]),
                "callers": sorted(bucket["callers"]),
                "ghidra_crosschecked_occurrence_count": ghidra_count,
                "fully_ghidra_crosschecked": bool(occurrence_count and ghidra_count == occurrence_count),
                "source_mapped_occurrence_count": mapped_count,
                "wrapper_internal_occurrence_count": internal_count,
                "unresolved_occurrence_count": unresolved_count,
                "mapping_kind": mapping_kind,
                "stable_source_argument_index": stable_source_index,
                "stable_wrapper_internal_source": stable_internal_source,
                "source_argument_index_histogram": _histogram(index_counter, "source_argument_index"),
                "source_argument_expression_histogram": _histogram(
                    bucket["source_argument_expressions"], "expression"
                ),
                "exact_source_integer_literal_histogram": _histogram(
                    bucket["exact_source_integer_literals"], "value"
                ),
                "wrapper_internal_source_histogram": _histogram(
                    internal_counter, "forwarding_source"
                ),
                "forwarding_source_histogram": _histogram(
                    bucket["forwarding_sources"], "forwarding_source"
                ),
                "recurrent_pattern": occurrence_count >= 2,
                "crosschecked_stable_pattern": bool(
                    occurrence_count >= 2
                    and ghidra_count == occurrence_count
                    and mapping_kind in {"stable-source-argument", "stable-wrapper-internal"}
                ),
            }
        )

    return {
        "format": FORMAT,
        "argument_join": str(path),
        "pattern_count": len(patterns),
        "recurrent_pattern_count": sum(row["recurrent_pattern"] is True for row in patterns),
        "crosschecked_stable_pattern_count": sum(
            row["crosschecked_stable_pattern"] is True for row in patterns
        ),
        "stable_source_argument_pattern_count": sum(
            row["mapping_kind"] == "stable-source-argument" for row in patterns
        ),
        "stable_wrapper_internal_pattern_count": sum(
            row["mapping_kind"] == "stable-wrapper-internal" for row in patterns
        ),
        "mixed_or_unresolved_pattern_count": sum(
            row["mapping_kind"] in {"mixed", "unresolved"} for row in patterns
        ),
        "patterns": patterns,
        "scope": {
            "repeated_provenance_patterns_observed": True,
            "ghidra_crosschecked_stability_observed": True,
            "argument_semantic_roles_proven": False,
            "allocation_size_role_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "allocator_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "Stable and recurrent mappings are repetition evidence only. A backend "
                "storage repeatedly receiving the same source argument index or wrapper-"
                "internal symbolic value is not automatically assigned a semantic role."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("argument_join", type=Path, help=f"{INPUT_FORMAT} JSON")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = summarize_memory_wrapper_argument_patterns(args.argument_join)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"patterns: {report['pattern_count']}")
    print(f"recurrent patterns: {report['recurrent_pattern_count']}")
    print(f"crosschecked stable patterns: {report['crosschecked_stable_pattern_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
