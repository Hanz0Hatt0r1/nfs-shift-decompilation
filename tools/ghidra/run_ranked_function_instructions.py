#!/usr/bin/env python3
"""Run the targeted Ghidra instruction exporter for one ranked Process 1 worklist.

The rank artifact is authoritative for scope: this wrapper extracts exactly
`selected_instruction_export_functions` from
SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1 and forwards exactly those
functions to run_shift_function_instructions.sh.  It refuses duplicate, empty,
wrong-retail, or oversized worklists instead of silently broadening the static
search.
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


def _load_rank(path: Path, *, max_functions: int) -> tuple[dict[str, Any], list[str]]:
    if max_functions <= 0:
        raise ValueError("max_functions must be positive")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != RANK_FORMAT or payload.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {RANK_FORMAT}")

    retail = payload.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("rank retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("rank retail identity drift")

    ranking = payload.get("ranking")
    if not isinstance(ranking, Mapping):
        raise ValueError("rank ranking section missing")
    raw = ranking.get("selected_instruction_export_functions")
    if not isinstance(raw, list) or not raw:
        raise ValueError("rank selected instruction-export worklist is empty")
    selected = [_normalize_address(value) for value in raw]
    if len(set(selected)) != len(selected):
        raise ValueError("rank selected instruction-export worklist contains duplicates")
    if len(selected) > max_functions:
        raise ValueError(
            f"rank selected worklist has {len(selected)} functions, exceeding safety cap {max_functions}"
        )

    declared_limit = ranking.get("selected_instruction_export_limit")
    if isinstance(declared_limit, int) and declared_limit > 0 and len(selected) > declared_limit:
        raise ValueError("rank selected worklist exceeds its declared export limit")
    return payload, selected


def build_command(
    rank_artifact: Path,
    project_dir: Path,
    project_name: str,
    output_jsonl: Path,
    *,
    max_functions: int = DEFAULT_MAX_FUNCTIONS,
    runner: Path = RUNNER,
) -> tuple[list[str], list[str]]:
    _payload, selected = _load_rank(rank_artifact, max_functions=max_functions)
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
    rank_artifact: Path,
    project_dir: Path,
    project_name: str,
    output_jsonl: Path,
    *,
    max_functions: int = DEFAULT_MAX_FUNCTIONS,
    dry_run: bool = False,
) -> int:
    command, selected = build_command(
        rank_artifact,
        project_dir,
        project_name,
        output_jsonl,
        max_functions=max_functions,
    )
    print(f"rank-selected function count: {len(selected)}")
    print("rank-selected functions: " + " ".join(selected))
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
    parser.add_argument("rank_artifact", type=Path)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--max-functions", type=int, default=DEFAULT_MAX_FUNCTIONS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(
            args.rank_artifact,
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
