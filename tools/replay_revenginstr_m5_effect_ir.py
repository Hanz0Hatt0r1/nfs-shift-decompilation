"""Freeze or replay the scan22 FunctionEffectIR/2 consumer evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from revenginstr.effect_ir import build_function_effect_ir
from revenginstr.structured_summary import build_function_summaries

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "evidence/revenginstr_m23_direct_call_replay/screening-scan22"
EVIDENCE_DIR = ROOT / "evidence/revenginstr_m5_effect_ir_replay/scan22"
PROGRAM_ID = "nfs-shift:SHIFT.exe"
FUNCTION_ENTRY = "00a277d0"
REVENGINSTR_SOURCE_COMMIT = "b6b1ceebdb167181aeb0d4313711ad990149b925"

INPUTS = {
    "parameter_stores": INPUT_DIR / "parameter-stores.tsv",
    "parameter_loads": INPUT_DIR / "parameter-loads.tsv",
    "pcode_flow": INPUT_DIR / "caller-pcode-flow/00a277d0.tsv",
}
ARTIFACT_NAMES = ("function-effect-ir-v2.jsonl", "function-summary-v2.jsonl")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonl(records: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(record, sort_keys=True) + "\n" for record in records).encode("utf-8")


def _read_jsonl(raw: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"JSONL line {line_no}: blank record")
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"JSONL line {line_no}: expected object")
        records.append(record)
    return records


def _build() -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    input_bytes = {name: path.read_bytes() for name, path in INPUTS.items()}
    effects = build_function_effect_ir(
        PROGRAM_ID,
        parameter_store_tsv=INPUTS["parameter_stores"],
        parameter_load_tsv=INPUTS["parameter_loads"],
        pcode_flow_tsv=INPUTS["pcode_flow"],
        include_generic_memory_ops=True,
    )
    effect_bytes = _jsonl(effects)
    summaries = build_function_summaries(effects, source_sha256=_sha256(effect_bytes))
    summary_bytes = _jsonl(summaries)
    artifacts = {
        ARTIFACT_NAMES[0]: effect_bytes,
        ARTIFACT_NAMES[1]: summary_bytes,
    }
    effect_counts = Counter(
        effect["kind"] for record in effects for effect in record["effects"]
    )
    claim_counts = Counter(
        claim["kind"] for record in summaries for claim in record["claims"]
    )
    metrics = {
        "program_id": PROGRAM_ID,
        "function_entry": FUNCTION_ENTRY,
        "effect_functions": len(effects),
        "effects": sum(len(record["effects"]) for record in effects),
        "effects_by_kind": dict(sorted(effect_counts.items())),
        "summary_functions": len(summaries),
        "summary_claims": sum(len(record["claims"]) for record in summaries),
        "summary_claims_by_kind": dict(sorted(claim_counts.items())),
    }
    return artifacts, metrics, input_bytes


def _manifest(artifacts: dict[str, bytes], metrics: dict[str, Any], input_bytes: dict[str, bytes]) -> dict[str, Any]:
    return {
        "format": "NFS.RevenginstrM5EffectIRReplay/1",
        "program_id": PROGRAM_ID,
        "function_entry": FUNCTION_ENTRY,
        "revenginstr_source_commit": REVENGINSTR_SOURCE_COMMIT,
        "inputs": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(input_bytes[name]),
                "rows": max(0, len(input_bytes[name].splitlines()) - 1),
                "sha256": _sha256(input_bytes[name]),
            }
            for name, path in INPUTS.items()
        },
        "artifacts": {
            name: {
                "bytes": len(raw),
                "rows": len(_read_jsonl(raw)),
                "sha256": _sha256(raw),
            }
            for name, raw in artifacts.items()
        },
        "summary": metrics,
        "limitations": [
            "P-code LOAD/STORE rows record exact High-P-code operations, not runtime execution.",
            "Generic memory rows preserve operand tokens and do not resolve globals, pointer aliases, or write-to-read flow.",
            "Parameter-rooted field facts are structural projections; they do not assert semantic roles.",
        ],
    }


def _schema_dir() -> Path:
    value = os.environ.get("REVENGINSTR_REPO")
    if not value:
        raise ValueError("REVENGINSTR_REPO must point to the pinned revenginstr checkout")
    path = Path(value) / "schemas"
    if not path.is_dir():
        raise FileNotFoundError(f"revenginstr schema directory not found: {path}")
    return path


def validate_frozen() -> dict[str, Any]:
    artifacts, metrics, input_bytes = _build()
    expected_manifest = _manifest(artifacts, metrics, input_bytes)
    manifest_path = EVIDENCE_DIR / "manifest.json"
    if json.loads(manifest_path.read_text(encoding="utf-8")) != expected_manifest:
        raise ValueError("FunctionEffectIR/2 replay manifest changed")
    for name, expected in artifacts.items():
        if (EVIDENCE_DIR / name).read_bytes() != expected:
            raise ValueError(f"{name} changed on replay")

    schema_dir = _schema_dir()
    for filename, artifact_name in zip(
        ("function-effect-ir-v2.schema.json", "function-summary-v2.schema.json"), ARTIFACT_NAMES
    ):
        schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for record in _read_jsonl(artifacts[artifact_name]):
            validator.validate(record)
    return metrics


def freeze() -> dict[str, Any]:
    artifacts, metrics, input_bytes = _build()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for name, raw in artifacts.items():
        (EVIDENCE_DIR / name).write_bytes(raw)
    manifest = _manifest(artifacts, metrics, input_bytes)
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
        f"FunctionEffectIR/2 replay passed: {metrics['effects']} effects, "
        f"{metrics['summary_claims']} summary claims"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
