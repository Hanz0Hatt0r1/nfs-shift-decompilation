#!/usr/bin/env python3
"""Attach targeted memory-wrapper forwarding evidence to class-pipeline output.

The base class-evidence pipeline intentionally does not require the targeted
instruction export. This postprocessor joins an already-produced
SHIFT-MEMORY-WRAPPER-FORWARDING/1 report to the pipeline's
memory_wrapper_callsites.json and updates pipeline_manifest.json in place while
preserving the existing evidence boundaries.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from join_memory_wrapper_argument_evidence import join_memory_wrapper_argument_evidence

PIPELINE_FORMAT = "SHIFT-CLASS-EVIDENCE-PIPELINE/1"
CALLSITE_FORMAT = "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
JOIN_FORMAT = "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return report


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def attach_memory_wrapper_forwarding(
    pipeline_dir: Path,
    forwarding_path: Path,
) -> dict[str, Any]:
    manifest_path = pipeline_dir / "pipeline_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing pipeline manifest: {manifest_path}")

    manifest = _load_json(manifest_path, PIPELINE_FORMAT)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError(f"{manifest_path}: artifacts object missing")

    callsite_name = artifacts.get("memory_wrapper_callsites")
    if not isinstance(callsite_name, str) or not callsite_name:
        raise ValueError(f"{manifest_path}: memory_wrapper_callsites artifact missing")
    callsite_path = pipeline_dir / callsite_name
    _load_json(callsite_path, CALLSITE_FORMAT)
    _load_json(forwarding_path, FORWARDING_FORMAT)

    join = join_memory_wrapper_argument_evidence(callsite_path, forwarding_path)
    if join.get("format") != JOIN_FORMAT:
        raise ValueError(f"unexpected join format: {join.get('format')!r}")

    join_path = pipeline_dir / "memory_wrapper_argument_join.json"
    _atomic_write_json(join_path, join)

    artifacts["memory_wrapper_argument_join"] = join_path.name
    counts = manifest.setdefault("counts", {})
    if not isinstance(counts, dict):
        raise ValueError(f"{manifest_path}: counts must be an object")
    counts.update(
        {
            "memory_wrapper_argument_join_callsites": join.get("callsite_count"),
            "memory_wrapper_forwarding_record_callsites": join.get(
                "forwarding_record_callsite_count"
            ),
            "memory_wrapper_forwarding_join_ready_callsites": join.get(
                "forwarding_join_ready_callsite_count"
            ),
            "memory_wrapper_forwarding_ghidra_crosschecked_joins": join.get(
                "ghidra_crosschecked_join_callsite_count"
            ),
            "memory_wrapper_backend_arguments": join.get("backend_argument_count"),
            "memory_wrapper_source_mapped_backend_arguments": join.get(
                "source_mapped_backend_argument_count"
            ),
            "memory_wrapper_internal_backend_arguments": join.get(
                "wrapper_internal_backend_argument_count"
            ),
            "memory_wrapper_unresolved_backend_arguments": join.get(
                "unresolved_backend_argument_count"
            ),
        }
    )

    scope = manifest.setdefault("scope", {})
    if not isinstance(scope, dict):
        raise ValueError(f"{manifest_path}: scope must be an object")
    scope.update(
        {
            "memory_wrapper_instruction_forwarding_used": True,
            "memory_wrapper_argument_provenance_joined": True,
            "argument_roles_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "ownership_semantics_proven": False,
        }
    )
    scope["note"] = (
        str(scope.get("note") or "").rstrip()
        + " Targeted memory-wrapper instruction forwarding was additionally joined "
        "to recovered source call expressions. This proves mechanical value provenance "
        "through wrapper entry storage to modeled backend argument storage; semantic "
        "argument roles, allocator/release ABI and ownership remain unproven."
    ).strip()

    manifest["memory_wrapper_forwarding"] = str(forwarding_path)
    _atomic_write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pipeline_dir",
        type=Path,
        help="directory produced by build_class_evidence_pipeline.py",
    )
    parser.add_argument(
        "--forwarding",
        type=Path,
        required=True,
        help="SHIFT-MEMORY-WRAPPER-FORWARDING/1 JSON",
    )
    args = parser.parse_args()

    manifest = attach_memory_wrapper_forwarding(args.pipeline_dir, args.forwarding)
    counts = manifest.get("counts", {})
    print(f"format: {manifest['format']}")
    print(
        "join-ready wrapper callsites: "
        f"{counts.get('memory_wrapper_forwarding_join_ready_callsites')}"
    )
    print(
        "source-mapped backend arguments: "
        f"{counts.get('memory_wrapper_source_mapped_backend_arguments')}"
    )
    print(
        "unresolved backend arguments: "
        f"{counts.get('memory_wrapper_unresolved_backend_arguments')}"
    )
    print(f"updated: {args.pipeline_dir / 'pipeline_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
