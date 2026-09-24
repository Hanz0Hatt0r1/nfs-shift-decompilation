#!/usr/bin/env python3
"""Analyze a collected SHIFT MEB evidence bundle without loading its corpus into RAM.

The input ZIP may contain a very large resources.jsonl. This tool streams that
member line-by-line and emits only aggregate evidence plus a few bounded examples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, TextIO


FORMAT = "SHIFT.MEBEvidenceBundle/1"
ANALYZER_VERSION = "116.0"
COLOR_PROPERTIES = ("460", "461")
EXPECTED = {
    "460": [4, 6, 0],
    "461": [4, 6, 1],
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _iter_jsonl(zf: zipfile.ZipFile, name: str) -> TextIO:
    raw = zf.open(name, "r")
    import io
    return io.TextIOWrapper(raw, encoding="utf-8")


def analyze_bundle(path: Path) -> dict[str, Any]:
    bundle_hash = sha256_file(path)
    with zipfile.ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        required = {"summary.json", "resources.jsonl", "errors.json"}
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"evidence bundle is missing required members: {missing}")

        summary = json.loads(zf.read("summary.json").decode("utf-8"))
        if summary.get("format") != FORMAT:
            raise ValueError(
                f"unsupported evidence bundle format: {summary.get('format')!r}"
            )

        property_counts: Counter[str] = Counter()
        descriptor_counts: Counter[str] = Counter()
        exact_descriptor_counts: Counter[str] = Counter()
        payload_observed_counts: Counter[str] = Counter()
        payload_match_counts: Counter[str] = Counter()
        descriptor_observed_counts: Counter[str] = Counter()
        archive_counts: Counter[str] = Counter()
        payload_bytes: Counter[str] = Counter()
        resource_count = 0
        color_resource_count = 0
        examples: dict[str, list[dict[str, Any]]] = {
            "descriptor_mismatch": [],
            "property_absent": [],
        }

        with _iter_jsonl(zf, "resources.jsonl") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                resource_count += 1
                source = row.get("source") or {}
                archive = source.get("archive")
                if archive:
                    archive_counts[str(archive)] += 1

                found = {str(x) for x in row.get("color_properties_found") or []}
                if found:
                    color_resource_count += 1

                descriptors = {
                    str(d.get("id")): d
                    for d in row.get("mesh", {}).get("property_descriptors", [])
                    if isinstance(d, dict)
                }
                reports = row.get("color_reports") or {}

                for pid in COLOR_PROPERTIES:
                    if pid not in found:
                        if len(examples["property_absent"]) < 8:
                            examples["property_absent"].append({
                                "line": line_number,
                                "resource_id": row.get("id"),
                                "property_id": pid,
                            })
                        continue

                    property_counts[pid] += 1
                    descriptor = descriptors.get(pid)
                    if descriptor is not None:
                        descriptor_counts[pid] += 1
                        words = descriptor.get("words")
                        if words == EXPECTED[pid]:
                            exact_descriptor_counts[pid] += 1
                        elif len(examples["descriptor_mismatch"]) < 8:
                            examples["descriptor_mismatch"].append({
                                "line": line_number,
                                "resource_id": row.get("id"),
                                "property_id": pid,
                                "observed_words": words,
                                "expected_words": EXPECTED[pid],
                            })

                    report = reports.get(pid) or {}
                    source_info = report.get("source") or {}
                    if source_info.get("descriptor_range_status") == "observed":
                        descriptor_observed_counts[pid] += 1
                    if source_info.get("payload_range_status") == "observed":
                        payload_observed_counts[pid] += 1
                    if source_info.get("decoded_stream_matches_payload_status") == "observed":
                        payload_match_counts[pid] += 1
                    payload_range = source_info.get("payload_range") or {}
                    if isinstance(payload_range.get("length"), int):
                        payload_bytes[pid] += payload_range["length"]

        errors = json.loads(zf.read("errors.json").decode("utf-8"))

        properties: dict[str, Any] = {}
        for pid in COLOR_PROPERTIES:
            present = property_counts[pid]
            descriptor = descriptor_counts[pid]
            exact = exact_descriptor_counts[pid]
            properties[pid] = {
                "resources_with_property": present,
                "descriptor_records": descriptor,
                "exact_expected_descriptors": exact,
                "descriptor_exactness": (
                    "all-observed" if present and exact == present
                    else "none-observed" if present == 0
                    else "mixed"
                ),
                "descriptor_range_observed": descriptor_observed_counts[pid],
                "payload_range_observed": payload_observed_counts[pid],
                "decoded_stream_matches_payload": payload_match_counts[pid],
                "payload_bytes_total": payload_bytes[pid],
                "expected_descriptor_words": EXPECTED[pid],
                "corpus_presence": "observed" if present else "not-observed",
            }

        source = summary.get("source_evidence") or {}
        source_status = "observed" if source.get("supplied") else "not-supplied"
        exact_460 = (
            resource_count > 0
            and property_counts["460"] == resource_count
            and exact_descriptor_counts["460"] == resource_count
            and descriptor_observed_counts["460"] == resource_count
            and payload_observed_counts["460"] == resource_count
            and payload_match_counts["460"] == resource_count
        )

        return {
            "format": "SHIFT.MEBCorpusEvidence/1",
            "analyzer_version": ANALYZER_VERSION,
            "bundle": {
                "path": str(path),
                "sha256": bundle_hash,
                "collector_version": summary.get("collector_version"),
                "created_utc": summary.get("created_utc"),
            },
            "scan": {
                "resources": resource_count,
                "color_resources": color_resource_count,
                "archives_with_resources": len(archive_counts),
                "errors": len(errors),
            },
            "properties": properties,
            "conclusions": {
                "color0_460_exact_descriptor_corpus": (
                    "proven" if exact_460 else "not-proven"
                ),
                "color1_461_corpus_presence": (
                    "observed" if property_counts["461"] else "not-observed"
                ),
                "source_evidence": source_status,
                "overall_type_bridge": (
                    "460-compatible-with-[4,6,0]"
                    if exact_460
                    else "incomplete"
                ),
            },
            "archives": {
                "count": len(archive_counts),
                "top_by_color_resource_count": [
                    {"archive": archive, "resources": count}
                    for archive, count in archive_counts.most_common(20)
                ],
            },
            "examples": examples,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stream-analyze a SHIFT MEB evidence ZIP without loading resources.jsonl into RAM."
    )
    parser.add_argument("bundle", help="SHIFT MEB evidence ZIP")
    parser.add_argument("-o", "--output", help="Optional JSON report path")
    args = parser.parse_args(argv)

    report = analyze_bundle(Path(args.bundle).expanduser().resolve())
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).expanduser().resolve().write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
