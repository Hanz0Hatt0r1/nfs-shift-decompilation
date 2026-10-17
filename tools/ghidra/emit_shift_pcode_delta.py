#!/usr/bin/env python3
"""Emit newly lowerable SHIFT functions as one supplemental P-code C shard."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

from revenginstr.pcode.c_lowering import (
    CORPUS_FORMAT,
    MANIFEST_FORMAT,
    SPACES_FORMAT,
    PcodeLoweringError,
    compile_function,
)


FUNCTION = re.compile(r"\bint rvi_([0-9a-f]{8})\(RviPcodeContext \*ctx\)")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def rejection_reason(error: PcodeLoweringError) -> str:
    _, separator, reason = str(error).partition(": ")
    return re.sub(r"0x[0-9a-fA-F]+", "0x<offset>", reason if separator else str(error))


def emit(corpus: Path, manifest_path: Path, spaces_path: Path, base_dir: Path,
         output_dir: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    spaces = json.loads(spaces_path.read_text())
    base_path = base_dir / "build-report.json"
    base = json.loads(base_path.read_text())
    source = {
        "program": manifest.get("program"),
        "language_id": manifest.get("language_id"),
        "corpus_sha256": digest(corpus),
        "manifest_sha256": digest(manifest_path),
        "address_spaces_sha256": digest(spaces_path),
    }
    if manifest.get("format") != MANIFEST_FORMAT or spaces.get("format") != SPACES_FORMAT:
        raise ValueError("unexpected corpus manifest or address-space format")
    if manifest.get("output_sha256") != source["corpus_sha256"] or spaces.get("language_id") != source["language_id"]:
        raise ValueError("corpus, manifest, and address-space table do not match")
    if base.get("format") != "REVENGINSTR.PcodeCFunctionShardBuild/1" or base.get("source") != source:
        raise ValueError("base shard build was made from a different corpus or address-space table")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    existing: set[int] = set()
    shards = sorted(base_dir.glob("shard-*.c"))
    for path in shards:
        with path.open(errors="replace") as stream:
            for line in stream:
                match = FUNCTION.search(line)
                if match:
                    existing.add(int(match.group(1), 16))
    expected = base.get("functions", {}).get("lowerable")
    if len(existing) != expected or not shards:
        raise ValueError("base shard function inventory does not match its build report")

    added = rejected = records = instructions = operations = 0
    reasons: collections.Counter[str] = collections.Counter()
    first = last = None
    runtime_written = False
    source_path = output_dir / "shift-pcode-delta.c"
    temporary = source_path.with_suffix(".c.tmp")
    with temporary.open("w") as output:
        with gzip.open(corpus, "rt", encoding="utf-8") as stream:
            for line_no, raw in enumerate(stream, 1):
                row = json.loads(raw)
                if not isinstance(row, dict) or row.get("format") != CORPUS_FORMAT:
                    raise ValueError(f"{corpus}:{line_no}: unexpected function record")
                records += 1
                if row.get("found") is not True:
                    continue
                address_text = row["function"]["address"]
                if int(address_text, 16) in existing:
                    continue
                try:
                    function_source, operation_count = compile_function(row, spaces, include_runtime=False)
                except PcodeLoweringError as error:
                    rejected += 1
                    reasons[rejection_reason(error)] += 1
                    continue
                if not runtime_written:
                    runtime_source, _ = compile_function(row, spaces)
                    function_marker = f"int rvi_{int(address_text, 16):08x}(RviPcodeContext *ctx) {{"
                    runtime_start = runtime_source.find("\n") + 1
                    runtime_end = runtime_source.find(function_marker, runtime_start)
                    if runtime_start == 0 or runtime_end < 0:
                        raise ValueError("shared lowerer output has no runtime/function boundary")
                    output.write(runtime_source[runtime_start:runtime_end])
                    runtime_written = True
                output.write(function_source)
                added += 1
                instructions += row["instruction_count"]
                operations += operation_count
                first = first or address_text
                last = address_text
    temporary.replace(source_path)
    if records != manifest.get("exported_function_count"):
        raise ValueError("corpus record count does not match its manifest")
    report = {
        "format": "NFSShift.PcodeLoweringSupplementalShard/1",
        "source": source,
        "base_build_report_sha256": digest(base_path),
        "base_lowerable_functions": len(existing),
        "records": records,
        "added_functions": added,
        "first_added_function": first,
        "last_added_function": last,
        "added_instructions": instructions,
        "added_pcode_operations": operations,
        "remaining_rejected_functions": rejected,
        "rejection_reasons": [
            {"functions": count, "reason": reason}
            for reason, count in sorted(reasons.items())
        ],
        "source_file": source_path.name,
        "source_bytes": source_path.stat().st_size,
        "source_sha256": digest(source_path),
    }
    (output_dir / "delta-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("address_spaces", type=Path)
    parser.add_argument("base_shards", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = emit(args.corpus, args.manifest, args.address_spaces, args.base_shards, args.output_dir)
    print(f"added {report['added_functions']} functions; {report['remaining_rejected_functions']} still rejected")


if __name__ == "__main__":
    main()
