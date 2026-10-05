#!/usr/bin/env python3
"""Run the targeted Ghidra instruction exporter for a bounded Process 1 worklist.

Supported worklist artifacts are authoritative for scope. The wrapper forwards
exactly their selected function list to run_shift_function_instructions.sh and
refuses empty, duplicate, wrong-retail, or oversized worklists.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

RANK_FORMAT = "SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1"
ROOT_POSE_FORMAT = "SHIFT.VehicleRenderRootPoseTransportFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
DEFAULT_MAX_FUNCTIONS = 64
RUNNER = Path(__file__).with_name("run_shift_function_instructions.sh")


def _normalize_address(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid function address: {value!r}")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid function address: {value!r}") from exc


def _validate_retail(program: Any, md5: Any, label: str) -> None:
    if program != PROGRAM or str(md5 or "").lower() != PE_MD5:
        raise ValueError(f"{label} retail identity drift")


def _extract_worklist(payload: Mapping[str, Any]) -> tuple[list[Any], int | None, str]:
    fmt = payload.get("format")
    if fmt == RANK_FORMAT:
        retail = payload.get("retail")
        ranking = payload.get("ranking")
        if not isinstance(retail, Mapping) or not isinstance(ranking, Mapping):
            raise ValueError("rank artifact sections missing")
        _validate_retail(retail.get("program"), retail.get("md5"), "rank")
        raw = ranking.get("selected_instruction_export_functions")
        limit = ranking.get("selected_instruction_export_limit")
        declared_limit = limit if isinstance(limit, int) and limit > 0 else None
        return raw if isinstance(raw, list) else [], declared_limit, "rank"

    if fmt == ROOT_POSE_FORMAT:
        retail = payload.get("retail")
        worklist = payload.get("targeted_instruction_worklist")
        if not isinstance(retail, Mapping) or not isinstance(worklist, Mapping):
            raise ValueError("root-pose frontier sections missing")
        _validate_retail(retail.get("program_name"), retail.get("executable_md5"), "root-pose frontier")
        if worklist.get("format") != INSTRUCTION_FORMAT:
            raise ValueError("root-pose worklist instruction format drift")
        raw = worklist.get("functions")
        return raw if isinstance(raw, list) else [], None, "root-pose frontier"

    raise ValueError(
        f"unsupported worklist artifact format {fmt!r}; expected {RANK_FORMAT} or {ROOT_POSE_FORMAT}"
    )


def _load_worklist(path: Path, *, max_functions: int) -> tuple[dict[str, Any], list[str], str]:
    if max_functions <= 0:
        raise ValueError("max_functions must be positive")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("ready") is not True:
        raise ValueError(f"{path}: worklist artifact is not ready")

    raw, declared_limit, source_kind = _extract_worklist(payload)
    if not raw:
        raise ValueError(f"{source_kind} instruction-export worklist is empty")
    selected = [_normalize_address(value) for value in raw]
    if len(set(selected)) != len(selected):
        raise ValueError(f"{source_kind} instruction-export worklist contains duplicates")
    if len(selected) > max_functions:
        raise ValueError(
            f"{source_kind} worklist has {len(selected)} functions, exceeding safety cap {max_functions}"
        )
    if declared_limit is not None and len(selected) > declared_limit:
        raise ValueError(f"{source_kind} selected worklist exceeds its declared export limit")
    return payload, selected, source_kind


def build_command(
    worklist_artifact: Path,
    project_dir: Path,
    project_name: str,
    output_jsonl: Path,
    *,
    max_functions: int = DEFAULT_MAX_FUNCTIONS,
    runner: Path = RUNNER,
) -> tuple[list[str], list[str]]:
    _payload, selected, _source_kind = _load_worklist(
        worklist_artifact, max_functions=max_functions
    )
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if not str(output_jsonl).strip():
        raise ValueError("output_jsonl must not be empty")
    command = [
        str(runner),
        str(project_dir),
        project_name,
        PROGRAM,
        str(output_jsonl),
        *selected,
    ]
    return command, selected


def _format_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(value)) for value in command)


def run(
    worklist_artifact: Path,
    project_dir: Path,
    project_name: str,
    output_jsonl: Path,
    *,
    max_functions: int = DEFAULT_MAX_FUNCTIONS,
    dry_run: bool = False,
) -> int:
    _payload, selected, source_kind = _load_worklist(
        worklist_artifact, max_functions=max_functions
    )
    command, selected_again = build_command(
        worklist_artifact,
        project_dir,
        project_name,
        output_jsonl,
        max_functions=max_functions,
    )
    if selected_again != selected:
        raise ValueError("worklist changed while building export command")
    print(f"worklist source: {source_kind}")
    print(f"selected function count: {len(selected)}")
    print("selected functions: " + " ".join(selected))
    print("command: " + _format_command(command))
    if dry_run:
        return 0
    if not RUNNER.is_file():
        raise ValueError(f"instruction runner missing: {RUNNER}")
    if "GHIDRA_HOME" not in os.environ or not os.environ["GHIDRA_HOME"].strip():
        raise ValueError("GHIDRA_HOME is not set")
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("worklist_artifact", type=Path)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--max-functions", type=int, default=DEFAULT_MAX_FUNCTIONS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(
            args.worklist_artifact,
            args.project_dir,
            args.project_name,
            args.output_jsonl,
            max_functions=args.max_functions,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
