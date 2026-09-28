"""Exact upgrade/modifier evaluation boundary from FUN_007a6be0.

The function resolves a base scalar against a linked list of upgrade nodes.
Each node covers an inclusive level interval, linearly interpolates its value,
then either multiplies a product accumulator or adds to an additive accumulator.
The final result is base * product + sum.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

FORMAT = "SHIFT.UpgradeModifierRuntime/1"
UNASSIGNED_UPGRADE_INDEX = 0x00000008


@dataclass(frozen=True)
class ModifierNode:
    value_start: float
    value_end: float
    level_start: int
    level_end: int
    additive: bool = False
    next_index: int | None = None


def _interpolate(node: ModifierNode, level: int) -> float:
    span = int(node.level_end) - int(node.level_start)
    if span == 0:
        return float(node.value_start)
    delta = int(level) - int(node.level_start)
    return (
        float(delta)
        * (float(node.value_end) - float(node.value_start))
        / float(span)
        + float(node.value_start)
    )


def evaluate_modifier_chain(
    base_value: float,
    upgrade_level: int,
    nodes: Sequence[ModifierNode],
) -> dict[str, Any]:
    """Reproduce FUN_007a6be0's complete accumulator semantics."""
    product = 1.0
    additive = 0.0
    matched: list[dict[str, Any]] = []

    current = 0 if nodes else None
    visited: set[int] = set()
    while current is not None:
        if current in visited:
            raise ValueError("modifier node cycle detected")
        if current < 0 or current >= len(nodes):
            raise ValueError("modifier node index out of range")
        visited.add(current)
        node = nodes[current]
        in_range = int(node.level_start) <= int(upgrade_level) <= int(node.level_end)
        if in_range:
            value = _interpolate(node, int(upgrade_level))
            matched.append({
                "node_index": current,
                "level_start": int(node.level_start),
                "level_end": int(node.level_end),
                "interpolated_value": value,
                "additive": bool(node.additive),
            })
            if node.additive:
                additive += value
            else:
                product *= value
        current = node.next_index

    result = float(base_value) * product + additive
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "evaluate-modifier-chain",
        "base_value": float(base_value),
        "upgrade_level": int(upgrade_level),
        "product": product,
        "additive": additive,
        "result": result,
        "matched_nodes": matched,
        "evidence": {
            "function": "FUN_007a6be0",
            "node_fields": {
                "value_start": "+0x00",
                "value_end": "+0x04",
                "level_start": "+0x08",
                "level_end": "+0x0c",
                "additive_flag": "+0x10",
                "next": "+0x14",
            },
            "final_expression": "base_value * product + additive",
            "upgrade_level_source": "DAT_00c10b2c + 0xcc + index*4",
        },
    }


def describe_modifier_chain(
    nodes: Sequence[ModifierNode],
) -> dict[str, Any]:
    """Return a serializable source-layout view of a modifier chain."""
    return {
        "format": FORMAT,
        "version": 1,
        "node_count": len(nodes),
        "record_stride": 0x18,
        "nodes": [
            {
                "index": index,
                "value_start": node.value_start,
                "value_end": node.value_end,
                "level_start": node.level_start,
                "level_end": node.level_end,
                "additive": node.additive,
                "next_index": node.next_index,
            }
            for index, node in enumerate(nodes)
        ],
        "evidence": {
            "function": "FUN_007a6be0",
            "unassigned_upgrade_index": UNASSIGNED_UPGRADE_INDEX,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a SHIFT upgrade modifier chain")
    parser.add_argument("input", type=Path, help="JSON array of modifier nodes")
    parser.add_argument("base", type=float)
    parser.add_argument("upgrade_level", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        parser.error("input must be a JSON array")
    nodes = [
        ModifierNode(
            float(row["value_start"]),
            float(row["value_end"]),
            int(row["level_start"]),
            int(row["level_end"]),
            bool(row.get("additive", False)),
            None if row.get("next_index") is None else int(row["next_index"]),
        )
        for row in raw
    ]
    report = evaluate_modifier_chain(args.base, args.upgrade_level, nodes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "result": report["result"],
        "matched_nodes": len(report["matched_nodes"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
