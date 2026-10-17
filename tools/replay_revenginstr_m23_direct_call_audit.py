#!/usr/bin/env python3
"""Verify and replay the frozen M2.3 SHIFT direct-call audit evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


EVIDENCE_DIR = Path("evidence/revenginstr_m23_direct_call_replay")
PROGRAM_ID = "nfs-shift:SHIFT.exe"
AUDIT_VERSIONS = ("v1", "v2", "v3")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row_count(path: Path) -> int:
    if path.suffix == ".jsonl":
        return len(_read_jsonl(path))
    if path.suffix == ".tsv":
        with path.open(newline="") as stream:
            return max(0, sum(1 for _ in csv.reader(stream, delimiter="\t")) - 1)
    raise ValueError(f"unsupported evidence format: {path}")


def validate_frozen(evidence_dir: Path) -> dict[str, int]:
    """Check the manifest, digests, row counts, and fail-closed result summary."""
    manifest = json.loads((evidence_dir / "manifest.json").read_text())
    if manifest.get("format") != "NFS.RevenginstrM23DirectCallReplay/1":
        raise ValueError("unsupported frozen replay manifest")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("manifest has no artifacts")

    total_bytes = 0
    for record in artifacts:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"artifact path escapes the evidence directory: {relative}")
        path = evidence_dir / relative
        if not path.is_file():
            raise ValueError(f"missing artifact: {relative}")
        payload = path.read_bytes()
        if len(payload) != record["bytes"]:
            raise ValueError(f"byte count mismatch: {relative}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        if _row_count(path) != record["rows"]:
            raise ValueError(f"row count mismatch: {relative}")
        total_bytes += len(payload)

    candidates = manifest.get("candidates", {})
    if len(candidates) != 10:
        raise ValueError(f"expected ten frozen candidates, found {len(candidates)}")
    for entry, expected in candidates.items():
        folder = evidence_dir / entry
        pairs = _read_jsonl(folder / "field-access-pairs.jsonl")
        if len(pairs) != expected["field_access_pair_rows"]:
            raise ValueError(f"field-pair row count mismatch for {entry}")
        calls = _read_jsonl(folder / "direct-call-memory-effects.jsonl")
        call_counts = dict(sorted(Counter(row["status"] for row in calls).items()))
        if call_counts != expected["direct_call_effect_status_counts"]:
            raise ValueError(f"direct-call status summary mismatch for {entry}")
        if "no_explicit_memory_write" in call_counts:
            raise ValueError(f"unexpected write-free direct callee in candidate {entry}")

        audit_counts: dict[str, dict[str, int]] = {}
        for version in AUDIT_VERSIONS:
            rows = _read_jsonl(folder / f"audit-{version}.jsonl")
            counts = dict(sorted(Counter(row["status"] for row in rows).items()))
            if counts != expected["audit_status_counts"][version]:
                raise ValueError(f"audit status summary mismatch for {entry}/{version}")
            if any("runtime value-flow claim" not in row["claim_scope"] for row in rows):
                raise ValueError(f"audit scope overclaims value flow for {entry}/{version}")
            audit_counts[version] = counts
        if audit_counts["v2"] != audit_counts["v3"]:
            raise ValueError(f"/3 changed /2 statuses without an eligible write-free call: {entry}")

    return {"artifacts": len(artifacts), "candidates": len(candidates), "bytes": total_bytes}


def _run(binary: Path, arguments: list[str]) -> None:
    result = subprocess.run([str(binary), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed:\n{result.stdout}{result.stderr}")


def _split_pcode(source: Path, destination: Path) -> dict[str, Path]:
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"P-code TSV has no header: {source}")
        groups: dict[str, list[dict[str, str]]] = {}
        for row in reader:
            groups.setdefault(row["function_entry"], []).append(row)

    paths: dict[str, Path] = {}
    for entry, rows in groups.items():
        path = destination / f"{entry}.tsv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=reader.fieldnames, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        paths[entry] = path
    return paths


def replay(evidence_dir: Path, bin_dir: Path) -> dict[str, int]:
    """Regenerate all derived pairs, call effects, and audit versions exactly."""
    summary = validate_frozen(evidence_dir)
    names = (
        "revenginstr-receiver-field-access-pairs",
        "revenginstr-direct-call-memory-effects",
        "revenginstr-receiver-field-store-load-dominance-audit",
    )
    binaries = {name: bin_dir / name for name in names}
    missing = [str(path) for path in binaries.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing revenginstr command(s): " + ", ".join(missing))

    manifest = json.loads((evidence_dir / "manifest.json").read_text())
    with tempfile.TemporaryDirectory(prefix="revenginstr-m23-replay-") as temporary:
        temporary_dir = Path(temporary)
        for entry in manifest["candidates"]:
            folder = evidence_dir / entry
            scratch = temporary_dir / entry
            scratch.mkdir()
            pairs = scratch / "field-access-pairs.jsonl"
            _run(
                binaries[names[0]],
                [
                    str(folder / "parameter-stores.tsv"),
                    str(folder / "parameter-loads.tsv"),
                    "--program-id",
                    PROGRAM_ID,
                    "--output",
                    str(pairs),
                ],
            )
            if pairs.read_bytes() != (folder / "field-access-pairs.jsonl").read_bytes():
                raise ValueError(f"field access pairs changed on replay: {entry}")

            flow_dir = scratch / "flows"
            flow_dir.mkdir()
            flows = _split_pcode(folder / "bounded-pcode.tsv", flow_dir)
            caller = flows.get(entry)
            if caller is None:
                raise ValueError(f"bounded P-code export omits caller {entry}")
            with caller.open(newline="") as stream:
                calls = [
                    row["callee_entry"]
                    for row in csv.DictReader(stream, delimiter="\t")
                    if row["opcode"] == "CALL" and row["callee_entry"] not in {"", "-"}
                ]
            call_effects = scratch / "direct-call-memory-effects.jsonl"
            arguments = [str(caller), "--program-id", PROGRAM_ID]
            for target in sorted(set(calls)):
                if target in flows:
                    arguments.extend(["--callee-flow", target, str(flows[target])])
            arguments.extend(["--output", str(call_effects)])
            _run(binaries[names[1]], arguments)
            if call_effects.read_bytes() != (folder / "direct-call-memory-effects.jsonl").read_bytes():
                raise ValueError(f"direct-call effect rows changed on replay: {entry}")

            for version in AUDIT_VERSIONS:
                output = scratch / f"audit-{version}.jsonl"
                command = [str(pairs), str(folder / "function-pcode-cfg-v3.jsonl")]
                if version in {"v2", "v3"}:
                    command.extend(["--memory-store-access-jsonl", str(folder / "memory-store-access.jsonl")])
                if version == "v3":
                    command.extend(["--direct-call-memory-effect-jsonl", str(call_effects)])
                command.extend(["--output", str(output)])
                _run(binaries[names[2]], command)
                if output.read_bytes() != (folder / f"audit-{version}.jsonl").read_bytes():
                    raise ValueError(f"{version} audit changed on replay: {entry}")

    return {
        **summary,
        "replayed_candidates": len(manifest["candidates"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True, help="revenginstr virtualenv bin directory")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    evidence_dir = arguments.repository_root / EVIDENCE_DIR
    summary = replay(evidence_dir, arguments.bin_dir)
    print(
        f"M2.3 frozen replay passed: {summary['replayed_candidates']} candidates, "
        f"{summary['artifacts']} artifacts, {summary['bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
