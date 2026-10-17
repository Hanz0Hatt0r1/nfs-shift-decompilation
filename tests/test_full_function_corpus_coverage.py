from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/ghidra"))

import build_full_function_corpus_coverage as coverage


def _instruction(address: str, pcode: list[dict]) -> dict:
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": "NOP",
        "text": "NOP",
        "operands": [],
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": pcode,
    }


def _function(address: str, instructions: list[dict]) -> dict:
    return {
        "format": coverage.GENERIC_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "resolved_address": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions),
            "calling_convention": "cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def test_full_function_corpus_must_match_hashes_and_inventory(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"fixture executable")
    monkeypatch.setattr(coverage, "RETAIL_SHA256", hashlib.sha256(executable.read_bytes()).hexdigest())
    monkeypatch.setattr(coverage, "RETAIL_MD5", hashlib.md5(executable.read_bytes()).hexdigest())

    inventory = tmp_path / "functions.tsv.gz"
    with gzip.open(inventory, "wt", encoding="utf-8") as handle:
        handle.write("entry\tname\taddress_count\tis_external\tsignature\n")
        handle.write("00401000\tFUN_00401000\t1\tfalse\tvoid()\n")
        handle.write("00401002\tFUN_00401002\t2\tfalse\tvoid()\n")

    corpus = tmp_path / "functions.jsonl.gz"
    rows = [
        _function("0x00401000", [_instruction("0x00401000", [{"opcode": "COPY"}])]),
        _function("0x00401002", [
            _instruction("0x00401002", [{"opcode": "COPY"}]),
            _instruction("0x00401003", []),
        ]),
    ]
    with gzip.open(corpus, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    manifest_path = tmp_path / "functions.jsonl.gz.manifest.json"
    manifest_path.write_text(json.dumps({
        "format": coverage.CORPUS_FORMAT,
        "program": "SHIFT.exe",
        "executable_md5": coverage.RETAIL_MD5,
        "language_id": "x86:LE:32:default",
        "function_count": 2,
        "function_offset": 0,
        "function_limit": 0,
        "exported_function_count": 2,
        "instruction_count": 3,
        "first_function_address": "0x00401000",
        "last_function_address": "0x00401002",
        "complete": True,
        "gzip": True,
        "output_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
    }), encoding="utf-8")

    report = coverage.build(executable, inventory, corpus, manifest_path)
    assert report["coverage"] == {
        "ghidra_function_count": 2,
        "exported_function_count": 2,
        "full_function_inventory_covered": True,
        "machine_instruction_count": 3,
        "pcode_instruction_count": 2,
        "pcode_operation_count": 2,
        "instructions_without_pcode": 1,
        "pcode_empty_instruction_mnemonic_counts": {"NOP": 1},
        "full_pcode_instruction_coverage": False,
    }

    manifest_path.write_text(manifest_path.read_text().replace(hashlib.sha256(corpus.read_bytes()).hexdigest(), "0" * 64))
    with pytest.raises(ValueError, match="SHA-256"):
        coverage.build(executable, inventory, corpus, manifest_path)


def test_shift_full_corpus_runner_delegates_to_generic_exporter() -> None:
    runner = (ROOT / "tools/ghidra/run_shift_full_function_corpus.sh").read_text(encoding="utf-8")
    assert 'REVENGINSTR_REPO=${REVENGINSTR_REPO:-' in runner
    assert 'scripts/run_ghidra_function_instructions.sh' in runner
    assert '--all "$OFFSET" "$LIMIT"' in runner
    assert '[[ "$OUTPUT" != *.gz ]]' in runner
