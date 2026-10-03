#!/usr/bin/env python3
"""Run the exact Ghidra instruction export required by the returned-pointer boundary.

This is orchestration only.  It reads
`SHIFT.VehicleReturnedAllocationPointerBoundary/1`, validates that the semantic
role is still unresolved, and passes its exact finite instruction worklist to the
existing read-only `run_shift_function_instructions.sh` exporter.

No address ranking, fallback discovery, original-game execution or runtime
capture is performed here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleReturnedAllocationPointerInstructionExportRun/1"
BOUNDARY_FORMAT = "SHIFT.VehicleReturnedAllocationPointerBoundary/1"
RUNNER = Path(__file__).with_name("run_shift_function_instructions.sh")
EXPECTED_BLOCKER = "returned_allocation_pointer_semantic_role_not_proven"


def _norm(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _load_boundary(path: Path) -> tuple[dict[str, Any], list[str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != BOUNDARY_FORMAT:
        raise ValueError(f"{path}: expected {BOUNDARY_FORMAT}")

    if value.get("returned_allocation_pointer_role_proven") is not False:
        raise ValueError(
            "returned allocation-pointer semantic boundary must remain unresolved"
        )
    if value.get("returned_allocation_pointer_role_state") != "unknown":
        raise ValueError("returned allocation-pointer role state must be unknown")

    blockers = value.get("blockers")
    if not isinstance(blockers, list) or EXPECTED_BLOCKER not in blockers:
        raise ValueError(
            "semantic boundary is missing the returned allocation-pointer blocker"
        )

    raw = value.get("required_instruction_targets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("semantic boundary has no required instruction targets")
    targets: list[str] = []
    for item in raw:
        address = _norm(item)
        if address is None:
            raise ValueError(f"invalid required instruction target: {item!r}")
        targets.append(address)
    if len(set(targets)) != len(targets):
        raise ValueError("semantic boundary contains duplicate instruction targets")
    if targets != sorted(targets):
        raise ValueError("semantic boundary instruction targets must be sorted")

    origins = value.get("return_origin_targets")
    if not isinstance(origins, list):
        raise ValueError("semantic boundary return_origin_targets must be a list")
    origin_set = {_norm(item) for item in origins}
    if None in origin_set:
        raise ValueError("semantic boundary contains invalid return-origin target")
    missing = [target for target in targets if target not in origin_set]
    if missing:
        raise ValueError(
            "required instruction target is not in the return-origin frontier: "
            + ", ".join(missing)
        )
    return value, targets


def build_command(
    project_dir: Path,
    project_name: str,
    program_name: str,
    output_jsonl: Path,
    targets: list[str],
) -> list[str]:
    if not project_name:
        raise ValueError("project_name must not be empty")
    if not program_name:
        raise ValueError("program_name must not be empty")
    if not targets:
        raise ValueError("targets must not be empty")
    return [
        "bash",
        str(RUNNER),
        str(project_dir),
        project_name,
        program_name,
        str(output_jsonl),
        *targets,
    ]


def run_vehicle_returned_allocation_pointer_instruction_export(
    boundary_path: Path,
    project_dir: Path,
    project_name: str,
    program_name: str,
    output_jsonl: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    boundary, targets = _load_boundary(boundary_path)
    command = build_command(
        project_dir,
        project_name,
        program_name,
        output_jsonl,
        targets,
    )

    if not RUNNER.is_file():
        raise FileNotFoundError(f"missing Ghidra instruction exporter runner: {RUNNER}")

    return_code: int | None = None
    status = "dry-run"
    if not dry_run:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, check=False)
        return_code = int(completed.returncode)
        if return_code != 0:
            raise RuntimeError(
                f"targeted Ghidra instruction export failed with status {return_code}"
            )
        if not output_jsonl.is_file():
            raise RuntimeError("targeted Ghidra instruction export did not create output JSONL")
        status = "completed"

    contexts = boundary.get("vehicle_create_bridges")
    if not isinstance(contexts, list):
        raise ValueError("semantic boundary vehicle_create_bridges must be a list")

    return {
        "format": FORMAT,
        "input_boundary": str(boundary_path),
        "project_dir": str(project_dir),
        "project_name": project_name,
        "program_name": program_name,
        "output_jsonl": str(output_jsonl),
        "target_count": len(targets),
        "targets": targets,
        "command": command,
        "status": status,
        "return_code": return_code,
        "vehicle_create_bridges": contexts,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "ghidra_project_opened_read_only_by_underlying_runner": True,
            "target_selection_ranked": False,
            "target_list_from_semantic_boundary_exact": True,
            "instruction_export_is_semantic_proof": False,
            "returned_allocation_pointer_role_proven": False,
            "note": (
                "This stage only materializes the exact instruction slice needed for the next "
                "static proof. Exporting instructions cannot by itself assign allocated-pointer "
                "semantics to a return value."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundary", type=Path)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("program_name")
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_vehicle_returned_allocation_pointer_instruction_export(
        args.boundary,
        args.project_dir,
        args.project_name,
        args.program_name,
        args.output_jsonl,
        dry_run=args.dry_run,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"targets: {report['target_count']}")
    print(f"instruction output: {report['output_jsonl']}")
    if args.manifest_out:
        print(f"manifest: {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
