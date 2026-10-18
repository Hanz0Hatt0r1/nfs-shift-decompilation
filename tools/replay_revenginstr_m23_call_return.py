#!/usr/bin/env python3
"""Freeze and replay structural call-result-to-return paths from M2.3 exports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "evidence/revenginstr_m23_direct_call_replay"
EVIDENCE_DIR = ROOT / "evidence/revenginstr_m23_call_return_replay"
PROGRAM_ID = "nfs-shift:SHIFT.exe"
REVENGINSTR_SOURCE_COMMIT = "08a31b94c304f8b7a57996974dafe352413f7924"
FORMAT = "NFS.RevenginstrM23CallReturnReplay/1"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonl_rows(raw: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"JSONL line {line_no}: blank record")
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"JSONL line {line_no}: expected object")
        records.append(record)
    return records


def _flow_paths() -> list[Path]:
    return sorted(
        path for path in INPUT_DIR.rglob("*.tsv")
        if "pcode-flow" in path.name or "pcode-flow" in str(path.parent)
    )


def _input_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t", strict=True))
    if rows and not {"function_entry", "op_address", "op_time", "opcode"} <= set(rows[0]):
        raise ValueError(f"unexpected P-code flow header: {path}")
    return {
        "path": path.relative_to(INPUT_DIR).as_posix(),
        "bytes": len(raw),
        "rows": len(rows),
        "sha256": _sha256(raw),
    }


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
    schema_path = repo / "schemas/receiver-provenance-graph-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _graph_function_entry(graph: dict[str, Any]) -> str:
    edge = graph["edges"][0]
    identity = json.loads(edge["provenance"][0]["source_id"])
    if len(identity) != 5 or identity[0] != PROGRAM_ID:
        raise ValueError("call-return provenance has an unexpected identity")
    if identity[4] not in {"CALL", "CALLIND"}:
        raise ValueError("call-return path does not start at a call result")
    terminal = json.loads(edge["provenance"][-1]["source_id"])
    if terminal[4] != "RETURN" or terminal[1] != identity[1]:
        raise ValueError("call-return path does not end at a return in the same function")
    return identity[1]


def _summary(
    inputs: list[dict[str, Any]],
    output_records: list[dict[str, Any]],
    output_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    scan_paths: Counter[str] = Counter()
    function_entries: set[str] = set()
    opcodes: Counter[str] = Counter()
    graph_ids: set[str] = set()
    for output in output_records:
        source_path = output["input_path"]
        scan = Path(source_path).parts[0]
        graphs = output_rows[source_path]
        scan_paths[scan] += len(graphs)
        for graph in graphs:
            graph_id = graph["graph_id"]
            if graph_id in graph_ids:
                raise ValueError("duplicate call-return graph identity across frozen inputs")
            graph_ids.add(graph_id)
            function_entries.add(_graph_function_entry(graph))
            opcode = json.loads(graph["edges"][0]["provenance"][0]["source_id"])[4]
            opcodes[opcode] += 1
    return {
        "source_file_count": len(inputs),
        "source_rows": sum(record["rows"] for record in inputs),
        "source_files_with_paths": len(output_records),
        "call_return_paths": len(graph_ids),
        "functions_with_paths": len(function_entries),
        "paths_by_scan": dict(sorted(scan_paths.items())),
        "paths_by_call_opcode": dict(sorted(opcodes.items())),
    }


def _manifest(
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    output_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "program_id": PROGRAM_ID,
        "revenginstr_source_commit": REVENGINSTR_SOURCE_COMMIT,
        "claim_scope": "structural_call_result_to_function_return",
        "factory_semantics_confirmed": False,
        "inputs": inputs,
        "outputs": outputs,
        "summary": _summary(inputs, outputs, output_rows),
        "limitations": [
            "A call result reaching a function return is a structural path, not a factory label.",
            "The export does not prove execution feasibility, returned object identity, or runtime type.",
            "CALLIND paths do not identify a statically resolved callee.",
        ],
    }


def _validate_graphs(
    graphs: list[dict[str, Any]], validator: Draft202012Validator, source_path: Path
) -> None:
    with source_path.open(newline="", encoding="utf-8") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t", strict=True))
    source_functions = {row["function_entry"] for row in source_rows}
    if len(source_functions) > 1:
        raise ValueError(f"P-code flow source contains multiple functions: {source_path}")
    for graph in graphs:
        validator.validate(graph)
        if graph.get("format") != "REVENGINSTR.ReceiverProvenanceGraph/1":
            raise ValueError("unexpected call-return graph format")
        if len(graph.get("edges", [])) != 1 or graph["edges"][0].get("relation") != "return_flow":
            raise ValueError("unexpected call-return graph edge")
        if _graph_function_entry(graph) not in source_functions:
            raise ValueError("call-return graph is not supported by its declared P-code input")


def _invoke(binary: Path, source_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        [
            str(binary), str(source_path), "--program-id", PROGRAM_ID,
            "--output", str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed:\n{result.stdout}{result.stderr}")


def _generate(bin_dir: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    binary = bin_dir / "revenginstr-receiver-call-return-flow"
    if not binary.is_file():
        raise FileNotFoundError(f"missing revenginstr command: {binary}")
    validator = _schema_validator()
    inputs = [_input_record(path) for path in _flow_paths()]
    artifacts: dict[str, bytes] = {}
    outputs: list[dict[str, Any]] = []
    output_rows: dict[str, list[dict[str, Any]]] = {}
    with tempfile.TemporaryDirectory(prefix="revenginstr-call-return-") as temporary:
        scratch = Path(temporary)
        for index, source in enumerate(_flow_paths()):
            input_path = inputs[index]["path"]
            raw_output = scratch / f"{index}.jsonl"
            _invoke(binary, source, raw_output)
            raw = raw_output.read_bytes()
            graphs = _jsonl_rows(raw)
            _validate_graphs(graphs, validator, source)
            if not graphs:
                continue
            output_path = (Path("call-return-paths") / input_path).with_suffix(".jsonl")
            artifacts[output_path.as_posix()] = raw
            output_rows[input_path] = graphs
            outputs.append({
                "input_path": input_path,
                "path": output_path.as_posix(),
                "bytes": len(raw),
                "rows": len(graphs),
                "sha256": _sha256(raw),
            })
    outputs.sort(key=lambda record: record["input_path"])
    return artifacts, _manifest(inputs, outputs, output_rows)


def _check_frozen() -> tuple[dict[str, Any], dict[str, bytes]]:
    validator = _schema_validator()
    manifest_path = EVIDENCE_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("program_id") != PROGRAM_ID:
        raise ValueError("unsupported M2.3 call-return replay manifest")
    if manifest.get("revenginstr_source_commit") != REVENGINSTR_SOURCE_COMMIT:
        raise ValueError("call-return replay uses an unexpected revenginstr commit")
    actual_inputs = [_input_record(path) for path in _flow_paths()]
    if manifest.get("inputs") != actual_inputs:
        raise ValueError("frozen P-code flow input list or digest changed")

    artifacts: dict[str, bytes] = {}
    output_rows: dict[str, list[dict[str, Any]]] = {}
    output_records = manifest.get("outputs")
    if not isinstance(output_records, list):
        raise ValueError("call-return outputs must be an array")
    known_inputs = {record["path"] for record in actual_inputs}
    for record in output_records:
        input_path = record.get("input_path")
        if input_path not in known_inputs:
            raise ValueError("call-return output refers to an unknown input")
        relative = Path(record.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("call-return output path escapes its evidence directory")
        raw = (EVIDENCE_DIR / relative).read_bytes()
        graphs = _jsonl_rows(raw)
        source = INPUT_DIR / input_path
        _validate_graphs(graphs, validator, source)
        expected = {
            "input_path": input_path,
            "path": relative.as_posix(),
            "bytes": len(raw),
            "rows": len(graphs),
            "sha256": _sha256(raw),
        }
        if record != expected or not graphs:
            raise ValueError("call-return output digest/count changed")
        if input_path in output_rows:
            raise ValueError("duplicate call-return output input")
        artifacts[relative.as_posix()] = raw
        output_rows[input_path] = graphs
    expected_manifest = _manifest(actual_inputs, output_records, output_rows)
    if manifest != expected_manifest:
        raise ValueError("call-return replay summary or limitations changed")
    return manifest, artifacts


def validate_frozen() -> dict[str, Any]:
    """Verify pinned source exports, graph outputs, schema, and summary."""
    manifest, _artifacts = _check_frozen()
    return manifest["summary"]


def replay(bin_dir: Path) -> dict[str, Any]:
    """Regenerate each graph with the pinned generic CLI and compare byte-for-byte."""
    manifest, artifacts = _check_frozen()
    binary = bin_dir / "revenginstr-receiver-call-return-flow"
    if not binary.is_file():
        raise FileNotFoundError(f"missing revenginstr command: {binary}")
    output_by_input = {record["input_path"]: record["path"] for record in manifest["outputs"]}
    with tempfile.TemporaryDirectory(prefix="revenginstr-call-return-replay-") as temporary:
        scratch = Path(temporary)
        for index, source_record in enumerate(manifest["inputs"]):
            source = INPUT_DIR / source_record["path"]
            generated = scratch / f"{index}.jsonl"
            _invoke(binary, source, generated)
            raw = generated.read_bytes()
            frozen_path = output_by_input.get(source_record["path"])
            if frozen_path is None:
                if raw:
                    raise ValueError(f"new call-return path found for {source_record['path']}")
            elif artifacts[frozen_path] != raw:
                raise ValueError(f"call-return output changed for {source_record['path']}")
    return manifest["summary"]


def freeze(bin_dir: Path) -> dict[str, Any]:
    """Write a new path-only artifact set from the frozen M2.3 P-code exports."""
    artifacts, manifest = _generate(bin_dir)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for relative, raw in artifacts.items():
        output = EVIDENCE_DIR / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
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
        "M2.3 call-return replay passed: "
        f"{summary['source_file_count']} inputs, {summary['call_return_paths']} paths, "
        f"{summary['functions_with_paths']} functions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
