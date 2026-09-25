"""Build a compact manifest for the real SHIFT decompilation research inputs.

The manifest records file identity only. Retail binaries/archives stay outside the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

FORMAT = "SHIFT.RetailResearchManifest/1"


def _fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": str(path),
        "filename": path.name,
        "bytes": size,
        "sha256": digest.hexdigest(),
        "exists": True,
    }


def build_retail_research_manifest(
    files: Iterable[str | Path],
    *,
    expected_sha256: dict[str, str] | None = None,
) -> dict:
    expected_sha256 = expected_sha256 or {}
    artifacts = []
    blockers = []

    for value in files:
        path = Path(value)
        if not path.is_file():
            artifacts.append({
                "path": str(path),
                "filename": path.name,
                "exists": False,
                "status": "missing",
            })
            blockers.append(f"retail-manifest:file-missing:{path}")
            continue

        row = _fingerprint(path)
        expected = expected_sha256.get(path.name)
        if expected is not None:
            row["expected_sha256"] = expected
            row["sha256_status"] = "match" if row["sha256"] == expected else "mismatch"
            if row["sha256_status"] != "match":
                blockers.append(f"retail-manifest:sha256-mismatch:{path.name}")
        else:
            row["sha256_status"] = "not-compared"
        row["status"] = "observed"
        artifacts.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "artifacts": artifacts,
        "policy": {
            "binary_content_committed": False,
            "identity_only": True,
            "allows_inference": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fingerprint real SHIFT research inputs")
    parser.add_argument("output")
    parser.add_argument("files", nargs="+")
    parser.add_argument(
        "--expected-sha256",
        action="append",
        default=[],
        metavar="NAME=SHA256",
    )
    args = parser.parse_args(argv)

    expected = {}
    for spec in args.expected_sha256:
        name, separator, digest = spec.partition("=")
        if not separator or len(digest) != 64:
            parser.error("expected NAME=64-hex-SHA256")
        expected[name] = digest.lower()

    report = build_retail_research_manifest(args.files, expected_sha256=expected)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "artifacts": len(report["artifacts"]),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
