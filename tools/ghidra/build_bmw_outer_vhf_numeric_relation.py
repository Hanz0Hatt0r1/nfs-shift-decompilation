#!/usr/bin/env python3
"""Materialize the exact selected BMW S2 outer->VHF numeric relation from retail BFF.

This is intentionally a thin composition wrapper.  It reuses the already-positive
BMW VHF root-frame builder for exact resource provenance, then passes that exact
packet to the fail-closed S2 evaluator.  It does not re-adjudicate the semantic
identity-vs-fixed-affine proof and it does not infer identity from MatrixNumber 0.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


def _load_sibling(filename: str, module_name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT_BUILDER = _load_sibling(
    "build_bmw_vhf_hierarchy_root_frame.py",
    "bmw_vhf_root_builder_for_s2",
)
EVALUATOR = _load_sibling(
    "evaluate_bmw_outer_vhf_numeric_relation.py",
    "bmw_outer_vhf_numeric_evaluator",
)

FORMAT = EVALUATOR.FORMAT
ROOT_FORMAT = ROOT_BUILDER.FORMAT
RESOURCE_JOIN_FORMAT = ROOT_BUILDER.RESOURCE_JOIN_FORMAT


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return value


def analyze_archive(
    semantic_relation: Mapping[str, Any],
    delta_proof: Mapping[str, Any],
    resource_join: Mapping[str, Any],
    primary_vehicle_archive: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root_frame = ROOT_BUILDER.analyze_archive(resource_join, primary_vehicle_archive)
    report = EVALUATOR.evaluate(semantic_relation, delta_proof, root_frame)
    source = root_frame["source"]
    report["materialization"] = {
        "root_frame_format": ROOT_FORMAT,
        "resource_join_format": RESOURCE_JOIN_FORMAT,
        "archive": source.get("archive"),
        "archive_sha256": source.get("archive_sha256"),
        "entry_index": source.get("entry_index"),
        "decoded_sha256": source.get("decoded_sha256"),
        "decoded_size": source.get("decoded_size"),
        "exact_root_packet_generated": True,
        "runtime_capture_used": False,
        "original_game_executed": False,
    }
    return report, root_frame


def _write(path: Path | None, value: Mapping[str, Any]) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semantic_relation", type=Path)
    parser.add_argument("delta_proof", type=Path)
    parser.add_argument("resource_join", type=Path)
    parser.add_argument("primary_vehicle_archive", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--root-json-out", type=Path)
    args = parser.parse_args(argv)

    report, root_frame = analyze_archive(
        _load(args.semantic_relation),
        _load(args.delta_proof),
        _load(args.resource_join),
        args.primary_vehicle_archive,
    )
    if args.root_json_out is not None:
        _write(args.root_json_out, root_frame)
    _write(args.json_out, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
