"""Freeze or replay the NFS Shift scan22 state-machine candidate audit."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from revenginstr.state_machine import main as state_machine_main

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "evidence/revenginstr_m23_direct_call_replay/screening-scan22"
EVIDENCE_DIR = ROOT / "evidence/revenginstr_m5_state_machine_replay/scan22"
REVENGINSTR_SOURCE_COMMIT = "ccfef5da1a52350efdb8d29608a27d4341009688"
INPUTS = {
    "cfg_v3": INPUT_DIR / "function-pcode-cfg-v3.jsonl",
    "pcode_flow": INPUT_DIR / "caller-pcode-flow/00a277d0.tsv",
    "parameter_loads": INPUT_DIR / "parameter-loads.tsv",
    "memory_stores": INPUT_DIR / "memory-store-access.jsonl",
}
ARTIFACT_NAME = "state-machine-candidate-audit-v1.json"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _build() -> tuple[bytes, dict[str, Any], dict[str, bytes]]:
    input_bytes = {name: path.read_bytes() for name, path in INPUTS.items()}
    with tempfile.TemporaryDirectory(prefix="nfs-state-machine-") as temporary:
        output = Path(temporary) / ARTIFACT_NAME
        arguments = [
            str(INPUTS["cfg_v3"]), str(INPUTS["pcode_flow"]),
            str(INPUTS["parameter_loads"]), str(INPUTS["memory_stores"]),
            "--output", str(output),
        ]
        with redirect_stdout(io.StringIO()):
            state_machine_main(arguments)
        report_bytes = output.read_bytes()

    report = json.loads(report_bytes)
    source = report["source"]
    metrics = {
        "program_id": report["program_id"],
        "function_count": source["function_count"],
        "pcode_operations": source["pcode_operations"],
        "parameter_load_rows": source["parameter_load_rows"],
        "memory_store_rows": source["memory_store_rows"],
        "unresolved_store_rows": source["unresolved_store_rows"],
        "candidate_count": source["candidate_count"],
    }
    return report_bytes, metrics, input_bytes


def _manifest(report_bytes: bytes, metrics: dict[str, Any], input_bytes: dict[str, bytes]) -> dict[str, Any]:
    return {
        "format": "NFS.RevenginstrStateMachineReplay/1",
        "revenginstr_source_commit": REVENGINSTR_SOURCE_COMMIT,
        "inputs": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(input_bytes[name]),
                "rows": max(0, len(input_bytes[name].splitlines()) - 1)
                if path.suffix == ".tsv" else len(input_bytes[name].splitlines()),
                "sha256": _sha256(input_bytes[name]),
            }
            for name, path in INPUTS.items()
        },
        "artifact": {
            "path": (EVIDENCE_DIR / ARTIFACT_NAME).relative_to(ROOT).as_posix(),
            "bytes": len(report_bytes),
            "sha256": _sha256(report_bytes),
        },
        "summary": metrics,
        "limitations": [
            "The report is a single-function structural candidate audit, not state semantics.",
            "Zero candidates means this bounded pattern was not observed in the selected function; it is not evidence that the function has no state behavior.",
            "The audit makes no branch-polarity, path-feasibility, or runtime value-flow claim.",
        ],
    }


def _schema_path() -> Path:
    value = os.environ.get("REVENGINSTR_REPO")
    if not value:
        raise ValueError("REVENGINSTR_REPO must point to the pinned revenginstr checkout")
    path = Path(value) / "schemas/state-machine-candidate-audit-v1.schema.json"
    if not path.is_file():
        raise FileNotFoundError(f"revenginstr schema not found: {path}")
    return path


def validate_frozen() -> dict[str, Any]:
    report_bytes, metrics, input_bytes = _build()
    if (EVIDENCE_DIR / ARTIFACT_NAME).read_bytes() != report_bytes:
        raise ValueError("state-machine candidate report changed on replay")
    expected_manifest = _manifest(report_bytes, metrics, input_bytes)
    if json.loads((EVIDENCE_DIR / "manifest.json").read_text(encoding="utf-8")) != expected_manifest:
        raise ValueError("state-machine candidate replay manifest changed")
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(report_bytes))
    return metrics


def freeze() -> dict[str, Any]:
    report_bytes, metrics, input_bytes = _build()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / ARTIFACT_NAME).write_bytes(report_bytes)
    manifest = _manifest(report_bytes, metrics, input_bytes)
    (EVIDENCE_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", help="write fresh consumer evidence and manifest")
    args = parser.parse_args()
    metrics = freeze() if args.freeze else validate_frozen()
    print(
        f"scan22 state-machine replay passed: {metrics['function_count']} function, "
        f"{metrics['candidate_count']} candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
