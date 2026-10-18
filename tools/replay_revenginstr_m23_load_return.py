#!/usr/bin/env python3
"""Freeze and replay one bounded parameter-load-to-return structural witness."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "evidence/revenginstr_m23_direct_call_replay/screening-scan18"
LOAD_PATH = INPUT_DIR / "parameter-loads.tsv"
FLOW_PATH = INPUT_DIR / "caller-pcode-flow/00a2c5d0.tsv"
EVIDENCE_DIR = ROOT / "evidence/revenginstr_m23_load_return_replay"
OUTPUT_NAME = "load-return-paths.jsonl"
PROGRAM_ID = "nfs-shift:SHIFT.exe"
FUNCTION_ENTRY = "00a2c5d0"
REVENGINSTR_SOURCE_COMMIT = "08a31b94c304f8b7a57996974dafe352413f7924"
FORMAT = "NFS.RevenginstrM23LoadReturnReplay/1"
LOAD_FORMAT = "REVENGINSTR.GhidraParameterLoadField/1"
GRAPH_FORMAT = "REVENGINSTR.ReceiverProvenanceGraph/1"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _records(raw: bytes) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"JSONL line {line_no}: blank record")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL line {line_no}: expected object")
        rows.append(row)
    return rows


def _input_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t", strict=True))
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "rows": len(rows),
        "sha256": _sha256(raw),
    }


def _filtered_load_bytes(raw: bytes) -> tuple[bytes, int]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""), delimiter="\t", strict=True)
    fields = reader.fieldnames
    if not fields or "function_entry" not in fields:
        raise ValueError("parameter-load TSV has an unexpected header")
    rows = [row for row in reader if row.get("function_entry") == FUNCTION_ENTRY]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8"), len(rows)


def _schema_validator() -> Draft202012Validator:
    repository = os.environ.get("REVENGINSTR_REPO")
    if not repository:
        raise ValueError("REVENGINSTR_REPO must point to the pinned revenginstr checkout")
    repo = Path(repository)
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != REVENGINSTR_SOURCE_COMMIT:
        raise ValueError("REVENGINSTR_REPO does not match the frozen source commit")
    schema = json.loads(
        (repo / "schemas/receiver-provenance-graph-v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_graphs(graphs: list[dict[str, Any]], validator: Draft202012Validator) -> None:
    for graph in graphs:
        validator.validate(graph)
        if graph.get("format") != GRAPH_FORMAT or graph.get("graph_id") is None:
            raise ValueError("unexpected receiver provenance graph")
        edges = graph.get("edges", [])
        if len(edges) != 1 or edges[0].get("relation") != "return_flow":
            raise ValueError("unexpected load-return graph edge")
        provenance = edges[0].get("provenance", [])
        if len(provenance) < 2 or provenance[0].get("source_format") != LOAD_FORMAT:
            raise ValueError("load-return graph is missing its parameter-load source")
        load_identity = json.loads(provenance[0]["source_id"])
        operation_identities = [json.loads(item["source_id"]) for item in provenance[1:]]
        if (
            load_identity[0] != PROGRAM_ID
            or load_identity[1] != FUNCTION_ENTRY
            or operation_identities[0][4] != "LOAD"
            or operation_identities[-1][4] != "RETURN"
            or any(identity[0] != PROGRAM_ID or identity[1] != FUNCTION_ENTRY for identity in operation_identities)
        ):
            raise ValueError("load-return path does not match the selected function")


def _invoke(binary: Path, loads_path: Path, flow_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        [
            str(binary), str(loads_path), str(flow_path), "--program-id", PROGRAM_ID,
            "--output", str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed:\n{result.stdout}{result.stderr}")


def _generate(bin_dir: Path) -> tuple[bytes, dict[str, Any]]:
    binary = bin_dir / "revenginstr-receiver-load-return-flow"
    if not binary.is_file():
        raise FileNotFoundError(f"missing revenginstr command: {binary}")
    validator = _schema_validator()
    load_raw, flow_raw = LOAD_PATH.read_bytes(), FLOW_PATH.read_bytes()
    filtered_loads, function_load_rows = _filtered_load_bytes(load_raw)
    with tempfile.TemporaryDirectory(prefix="revenginstr-load-return-") as temporary:
        scratch = Path(temporary)
        filtered_path, output_path = scratch / "parameter-loads.tsv", scratch / OUTPUT_NAME
        filtered_path.write_bytes(filtered_loads)
        _invoke(binary, filtered_path, FLOW_PATH, output_path)
        output_raw = output_path.read_bytes()
    graphs = _records(output_raw)
    _validate_graphs(graphs, validator)
    if function_load_rows != 7 or len(graphs) != 3:
        raise ValueError("scan18 load-return population changed")
    inputs = [_input_record(LOAD_PATH), _input_record(FLOW_PATH)]
    artifact = {
        "path": OUTPUT_NAME,
        "bytes": len(output_raw),
        "rows": len(graphs),
        "sha256": _sha256(output_raw),
    }
    manifest = {
        "format": FORMAT,
        "program_id": PROGRAM_ID,
        "function_entry": FUNCTION_ENTRY,
        "revenginstr_source_commit": REVENGINSTR_SOURCE_COMMIT,
        "inputs": inputs,
        "filtered_parameter_load_rows": function_load_rows,
        "artifact": artifact,
        "summary": {
            "parameter_load_rows_in_scan18": inputs[0]["rows"],
            "parameter_load_rows_for_function": function_load_rows,
            "load_return_paths": len(graphs),
        },
        "getter_semantics_confirmed": False,
        "limitations": [
            "Parameter-rooted field-load values reaching RETURN are structural paths, not getter/accessor labels.",
            "The export does not prove branch feasibility, returned object identity, or runtime behavior.",
        ],
    }
    return output_raw, manifest


def _check_frozen() -> tuple[dict[str, Any], bytes]:
    validator = _schema_validator()
    manifest = json.loads((EVIDENCE_DIR / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("format") != FORMAT
        or manifest.get("program_id") != PROGRAM_ID
        or manifest.get("function_entry") != FUNCTION_ENTRY
        or manifest.get("revenginstr_source_commit") != REVENGINSTR_SOURCE_COMMIT
    ):
        raise ValueError("unsupported load-return replay manifest")
    inputs = [_input_record(LOAD_PATH), _input_record(FLOW_PATH)]
    if manifest.get("inputs") != inputs:
        raise ValueError("frozen load-return input digest changed")
    raw = (EVIDENCE_DIR / OUTPUT_NAME).read_bytes()
    graphs = _records(raw)
    _validate_graphs(graphs, validator)
    filtered_raw, function_load_rows = _filtered_load_bytes(LOAD_PATH.read_bytes())
    if function_load_rows != 7 or len(graphs) != 3:
        raise ValueError("frozen load-return population changed")
    expected = {
        "format": FORMAT,
        "program_id": PROGRAM_ID,
        "function_entry": FUNCTION_ENTRY,
        "revenginstr_source_commit": REVENGINSTR_SOURCE_COMMIT,
        "inputs": inputs,
        "filtered_parameter_load_rows": function_load_rows,
        "artifact": {
            "path": OUTPUT_NAME,
            "bytes": len(raw),
            "rows": len(graphs),
            "sha256": _sha256(raw),
        },
        "summary": {
            "parameter_load_rows_in_scan18": inputs[0]["rows"],
            "parameter_load_rows_for_function": function_load_rows,
            "load_return_paths": len(graphs),
        },
        "getter_semantics_confirmed": False,
        "limitations": [
            "Parameter-rooted field-load values reaching RETURN are structural paths, not getter/accessor labels.",
            "The export does not prove branch feasibility, returned object identity, or runtime behavior.",
        ],
    }
    if manifest != expected:
        raise ValueError("load-return replay manifest changed")
    return manifest, filtered_raw


def validate_frozen() -> dict[str, Any]:
    manifest, _filtered = _check_frozen()
    return manifest["summary"]


def replay(bin_dir: Path) -> dict[str, Any]:
    manifest, filtered_loads = _check_frozen()
    binary = bin_dir / "revenginstr-receiver-load-return-flow"
    if not binary.is_file():
        raise FileNotFoundError(f"missing revenginstr command: {binary}")
    with tempfile.TemporaryDirectory(prefix="revenginstr-load-return-replay-") as temporary:
        scratch = Path(temporary)
        filtered_path, output_path = scratch / "parameter-loads.tsv", scratch / OUTPUT_NAME
        filtered_path.write_bytes(filtered_loads)
        _invoke(binary, filtered_path, FLOW_PATH, output_path)
        if output_path.read_bytes() != (EVIDENCE_DIR / manifest["artifact"]["path"]).read_bytes():
            raise ValueError("load-return paths changed on replay")
    return manifest["summary"]


def freeze(bin_dir: Path) -> dict[str, Any]:
    raw, manifest = _generate(bin_dir)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / OUTPUT_NAME).write_bytes(raw)
    (EVIDENCE_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest["summary"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    summary = freeze(args.bin_dir) if args.freeze else replay(args.bin_dir)
    print(
        "M2.3 load-return replay passed: "
        f"{summary['parameter_load_rows_for_function']} field loads, "
        f"{summary['load_return_paths']} paths"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
