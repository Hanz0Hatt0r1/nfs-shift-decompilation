#!/usr/bin/env python3
"""Validate and split the one-shot S5 retail instruction export.

The combined export is execution infrastructure only. It is split back into the
exact target sets required by the fail-closed analyzers so no analyzer silently
accepts a broader machine surface. The BManager subset is the corrected
registration/list/timing/default-dispatch topology; the superseded lifecycle
wrapper assumptions are intentionally absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.GhidraFunctionInstructions/2"
MANIFEST_FORMAT = "SHIFT.S5RetailInstructionExecutionBundle/1"

SCHEDULER = (
    "FUN_007155e9",
    "FUN_00715380",
    "FUN_00713050",
)
RATE_ACCESSOR = (
    "FUN_00713050",
    "FUN_0070fe90",
    "FUN_0041903c",
    "FUN_0070fe99",
    "FUN_0070fae0",
)
BMANAGER = (
    "FUN_00647d80",
    "FUN_00647ef0",
    "FUN_0065b8b0",
    "FUN_006626a0",
    "FUN_00662880",
    "FUN_00d36000",
    "FUN_006485b0",
    "FUN_00662600",
    "FUN_0070fe90",
)

SUBSETS = {
    "scheduler": SCHEDULER,
    "rate_accessor": RATE_ACCESSOR,
    "bmanager": BMANAGER,
}

BUNDLE_TARGETS = tuple(dict.fromkeys((*SCHEDULER, *RATE_ACCESSOR, *BMANAGER)))
if len(BUNDLE_TARGETS) != 15:
    raise AssertionError(f"S5 bundle target drift: expected 15, got {len(BUNDLE_TARGETS)}")

OUTPUTS = {
    "scheduler": "s5_scheduler_accumulator_instructions.jsonl",
    "rate_accessor": "s5_physics_manager_rate_accessor_instructions.jsonl",
    "bmanager": "s5_bmanager_dispatch_instructions.jsonl",
}


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        if value.get("format") != FORMAT:
            raise ValueError(f"{path}:{line_no}: expected {FORMAT}")
        if value.get("found") is not True:
            raise ValueError(f"{path}:{line_no}: unresolved target {value.get('requested')!r}")
        function = value.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise ValueError(f"{path}:{line_no}: function name missing")
        name = function["name"]
        if name in rows:
            raise ValueError(f"{path}:{line_no}: duplicate function row {name}")
        rows[name] = value

    expected = set(BUNDLE_TARGETS)
    actual = set(rows)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"S5 retail bundle target mismatch: missing={missing}, extra={extra}")
    return rows


def _payload(rows: dict[str, dict[str, Any]], targets: tuple[str, ...]) -> str:
    return "".join(json.dumps(rows[name], sort_keys=True) + "\n" for name in targets)


def split(bundle: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read_rows(bundle)
    output_dir.mkdir(parents=True, exist_ok=True)

    subset_reports: dict[str, Any] = {}
    for key, targets in SUBSETS.items():
        payload = _payload(rows, targets)
        output = output_dir / OUTPUTS[key]
        output.write_text(payload, encoding="utf-8")
        subset_reports[key] = {
            "path": str(output),
            "target_count": len(targets),
            "targets": list(targets),
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }

    bundle_bytes = bundle.read_bytes()
    manifest = {
        "format": MANIFEST_FORMAT,
        "version": 1,
        "status": "exact-subsets-ready",
        "ready": True,
        "bundle": {
            "path": str(bundle),
            "format": FORMAT,
            "target_count": len(BUNDLE_TARGETS),
            "targets": list(BUNDLE_TARGETS),
            "sha256": hashlib.sha256(bundle_bytes).hexdigest(),
        },
        "subsets": subset_reports,
        "corrections": {
            "bmanager_subset_uses_correct_default_dispatcher_FUN_00647d80": True,
            "FUN_00647da0_plus_0x18_assumption_retired": True,
            "FUN_0070fe90_return_as_FUN_006485b0_stack_argument_retired": True,
        },
        "proof_scope": {
            "retail_machine_semantics_promoted": False,
            "retail_cadence_admitted": False,
            "host_fixed_step_substitution_allowed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }
    manifest_path = output_dir / "s5_retail_instruction_bundle_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = split(args.bundle, args.output_dir)
    print(f"format: {report['format']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(f"bundle_target_count: {report['bundle']['target_count']}")
    for key in SUBSETS:
        print(f"{key}_target_count: {report['subsets'][key]['target_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
