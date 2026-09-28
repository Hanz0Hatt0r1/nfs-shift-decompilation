#!/usr/bin/env python3
"""Profile the real D3D9 shader corpus stored in SHIFT BFF archives.

The audit deduplicates exact raw FXO payloads before decoding. It then parses
all embedded shader blobs through the canonical shader IR/token decoder and
reports observed opcode/stage/model distributions. No generated shader is
considered equivalent merely because it shares an opcode profile.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import ExitStack
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from shader_asm import parse_program
from shader_ir import parse_shader_blobs
from shift_importer import BFF


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        path = Path(source)
        if path.suffix.lower() != ".zip":
            paths.append(path)
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-fxo-corpus-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _profile_payload(payload: bytes) -> dict[str, Any]:
    blobs = parse_shader_blobs(payload)
    stages = Counter()
    shader_models = Counter()
    opcodes = Counter()
    unsupported = Counter()
    instruction_count = 0
    programs: list[dict[str, Any]] = []

    for blob in blobs:
        program = parse_program(
            payload,
            blob.offset,
            blob.end,
            blob.stage,
            blob.major,
            blob.minor,
        )
        stage = str(program.stage)
        model = f"{program.major}.{program.minor}"
        stages[stage] += 1
        shader_models[model] += 1
        instruction_count += len(program.instructions)

        for instruction in program.instructions:
            opcodes[str(instruction.name)] += 1
        for opcode in program.unsupported_opcodes:
            unsupported[str(opcode)] += 1

        programs.append({
            "offset": int(blob.offset),
            "end": int(blob.end),
            "stage": stage,
            "shader_model": [program.major, program.minor],
            "instruction_count": len(program.instructions),
            "unsupported_opcodes": list(program.unsupported_opcodes),
        })

    return {
        "blob_count": len(blobs),
        "program_count": len(programs),
        "instruction_count": instruction_count,
        "stages": dict(sorted(stages.items())),
        "shader_models": dict(sorted(shader_models.items())),
        "opcodes": dict(sorted(opcodes.items())),
        "unsupported_opcodes": dict(sorted(unsupported.items())),
        "programs": programs,
    }


def profile_shader_corpus(inputs: Iterable[str | Path]) -> dict[str, Any]:
    raw_payloads: dict[str, dict[str, Any]] = {}
    archive_count = 0
    entry_count = 0
    fxo_entry_count = 0

    with ExitStack() as stack:
        bff_paths = _materialize_bffs(inputs, stack)
        for bff_path in bff_paths:
            archive_count += 1
        with BFF(bff_path) as archive:
            for entry in archive.entries:
                entry_count += 1
                if not entry.path.lower().endswith(".fxo"):
                    continue
                fxo_entry_count += 1
                raw = archive.raw_payload(entry)
                digest = _sha256(raw)
                record = raw_payloads.setdefault(
                    digest,
                    {
                        "raw_sha256": digest,
                        "type": int(entry.type),
                        "compressed_size": int(entry.compressed_size),
                        "uncompressed_size": int(entry.uncompressed_size),
                        "archive_count": 0,
                        "entry_count": 0,
                        "archives": set(),
                        "paths": set(),
                        "source_archive": str(bff_path),
                        "source_path": entry.path,
                    },
                )
                record["entry_count"] += 1
                record.setdefault("source_entry_index", int(entry.index))
                record["archives"].add(archive.path.name)
                record["paths"].add(entry.path)

    decoded = []
    stage_counts = Counter()
    model_counts = Counter()
    opcode_counts = Counter()
    unsupported_counts = Counter()
    decode_failures = []

    with ExitStack():
        for digest, record in sorted(raw_payloads.items()):
            try:
                with BFF(Path(record["source_archive"])) as archive:
                    entry = archive.entries[int(record["source_entry_index"])]
                    payload = archive.extract_entry(entry, type2="lzx")
                profile = _profile_payload(payload)
        except Exception as exc:
            decode_failures.append({
                "raw_sha256": digest,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        record = dict(record)
        record["archive_count"] = len(record["archives"])
        record["archives"] = sorted(record["archives"])
        record["paths"] = sorted(record["paths"])
        record["profile"] = profile
        decoded.append(record)
        stage_counts.update(profile["stages"])
        model_counts.update(profile["shader_models"])
        opcode_counts.update(profile["opcodes"])
        unsupported_counts.update(profile["unsupported_opcodes"])

    return {
        "format": "SHIFT.FXOShaderCorpusAudit/1",
        "version": 1,
        "archive_count": archive_count,
        "entry_count": entry_count,
        "fxo_entry_count": fxo_entry_count,
        "unique_raw_fxo_payloads": len(raw_payloads),
        "decoded_unique_payloads": len(decoded),
        "decode_failures": decode_failures,
        "summary": {
            "stage_counts": dict(sorted(stage_counts.items())),
            "shader_model_counts": dict(sorted(model_counts.items())),
            "opcode_counts": dict(
                sorted(opcode_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
            "unsupported_opcode_counts": dict(
                sorted(unsupported_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
        },
        "payloads": decoded,
        "ready": bool(raw_payloads) and not decode_failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = profile_shader_corpus(args.inputs)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
