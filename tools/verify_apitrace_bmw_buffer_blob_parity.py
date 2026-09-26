#!/usr/bin/env python3
"""Verify extracted BMW apitrace buffer blobs against canonical MEB artifacts.

This verifier consumes buffer_blob_evidence.json produced by
extract_apitrace_bmw_buffer_blobs.py --source-trace and compares the raw
runtime upload BLOB bytes directly with the deterministic MEB-derived
vertex/index artifacts. It deliberately does not infer parity from sizes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3DirectBlobParity/1"
EXPECTED_VB_SIZE = 269800
EXPECTED_IB_SIZES = (300, 12588, 14772, 1224, 1152, 168)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_bytes()


def compare(actual_path: Path, expected_path: Path, label: str) -> dict[str, Any]:
    actual = read(actual_path)
    expected = read(expected_path)
    reasons: list[str] = []
    if len(actual) != len(expected):
        reasons.append(f"length-mismatch:{len(actual)}:{len(expected)}")
    actual_sha = sha256(actual)
    expected_sha = sha256(expected)
    if actual != expected:
        reasons.append(f"sha256-mismatch:{actual_sha}:{expected_sha}")
    return {
        "label": label,
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "runtime_path": str(actual_path),
        "expected_path": str(expected_path),
        "runtime_size": len(actual),
        "expected_size": len(expected),
        "runtime_sha256": actual_sha,
        "expected_sha256": expected_sha,
        "blocking_reasons": reasons,
    }


def build_report(
    evidence: Mapping[str, Any],
    expected_dir: Path,
    evidence_base_dir: Path | None = None,
) -> dict[str, Any]:
    records = evidence.get("buffers") or []
    if not isinstance(records, list):
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["evidence:buffers-not-list"],
        }

    full = [
        row for row in records
        if isinstance(row, Mapping)
        and bool(row.get("full_buffer_candidate"))
        and bool(row.get("payload_path"))
    ]
    vb = [
        row for row in full
        if row.get("buffer_kind") == "vertex_buffer"
        and int(row.get("blob_size", -1)) == EXPECTED_VB_SIZE
    ]
    ib = [
        row for row in full
        if row.get("buffer_kind") == "index_buffer"
        and int(row.get("blob_size", -1)) in EXPECTED_IB_SIZES
    ]

    results: list[dict[str, Any]] = []
    blockers: list[str] = []

    if len(vb) != 1:
        blockers.append(f"runtime:expected-one-vertex-buffer:{len(vb)}")
    else:
        runtime_path = Path(str(vb[0]["payload_path"]))
        if not runtime_path.is_absolute():
            runtime_path = (evidence_base_dir or Path(".")).resolve() / runtime_path
        expected_path = expected_dir / "vertex_buffer.meb-order.bin"
        try:
            results.append(compare(runtime_path, expected_path, "vertex-buffer"))
        except FileNotFoundError as exc:
            blockers.append(f"file-not-found:{exc}")

    if len(ib) != len(EXPECTED_IB_SIZES):
        blockers.append(
            f"runtime:expected-six-index-buffers:{len(ib)}"
        )
    else:
        expected_by_size = {
            size: expected_dir / f"index_buffer_{index:02d}.uint16.bin"
            for index, size in enumerate(EXPECTED_IB_SIZES)
        }
        for row in sorted(ib, key=lambda item: int(item["blob_size"])):
            runtime_path = Path(str(row["payload_path"]))
            if not runtime_path.is_absolute():
                runtime_path = (evidence_base_dir or Path(".")).resolve() / runtime_path
            size = int(row["blob_size"])
            expected_path = expected_by_size[size]
            label = f"index-buffer:{size}-bytes"
            try:
                results.append(compare(runtime_path, expected_path, label))
            except FileNotFoundError as exc:
                blockers.append(f"file-not-found:{exc}")

    blockers.extend(
        reason
        for result in results
        for reason in result.get("blocking_reasons", [])
    )
    matches = sum(bool(result.get("ready")) for result in results)
    ready = len(results) == 7 and matches == 7 and not blockers

    return {
        "format": FORMAT,
        "status": "match" if ready else ("mismatch" if results and not blockers else "blocked"),
        "ready": ready,
        "expected": {
            "vertex_buffer_size": EXPECTED_VB_SIZE,
            "index_buffer_sizes": list(EXPECTED_IB_SIZES),
            "total_bytes": EXPECTED_VB_SIZE + sum(EXPECTED_IB_SIZES),
        },
        "runtime": {
            "payload_records": len(records),
            "full_buffer_candidates": len(full),
            "vertex_buffer_candidates": len(vb),
            "index_buffer_candidates": len(ib),
        },
        "matches": matches,
        "results": results,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "evidence_boundary": {
            "raw_runtime_vb_bytes": "proven" if ready else "not-proven",
            "raw_runtime_ib_bytes": "proven" if ready else "not-proven",
            "meb_byte_parity": "proven" if ready else "not-proven",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("buffer_blob_evidence", type=Path)
    parser.add_argument("expected_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    evidence = json.loads(args.buffer_blob_evidence.read_text(encoding="utf-8"))
    result = build_report(
        evidence,
        args.expected_dir.resolve(),
        args.buffer_blob_evidence.parent.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "ready": result["ready"],
        "matches": result["matches"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
