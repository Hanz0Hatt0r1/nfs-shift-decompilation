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


def test_full_corpus_pcode_inventory_is_pinned_and_consistent() -> None:
    report = json.loads((ROOT / "evidence/pcode_instruction_coverage_20261017.json").read_text())
    full = json.loads((ROOT / "evidence/full_function_instruction_corpus_20261017.json").read_text())
    assert report["source"]["sha256"] == full["authority"]["portable_function_corpus_sha256"]
    assert report["functions"] == {"records": 41538, "found": 41538, "missing": 0}
    assert report["instructions"] == {
        "total": 2088152,
        "with_pcode": 2085683,
        "without_pcode": 2469,
        "without_pcode_mnemonics": {"NOP": 2460, "WAIT": 9},
    }
    assert report["pcode"]["operations"] == full["coverage"]["pcode_operation_count"] == 9600713
    assert report["pcode"]["unique_opcodes"] == len(report["pcode"]["opcode_counts"]) == 56


def test_full_corpus_userop_coverage_is_hash_pinned_and_resolved() -> None:
    report = json.loads((ROOT / "evidence/pcode_userop_coverage_20261017.json").read_text())
    full = json.loads((ROOT / "evidence/full_function_instruction_corpus_20261017.json").read_text())
    assert report["format"] == "REVENGINSTR.PcodeUseropCoverage/1"
    assert report["source"]["program"] == full["authority"]["ghidra_program"] == "SHIFT.exe"
    assert report["source"]["language_id"] == full["authority"]["language_id"] == "x86:LE:32:default"
    assert report["source"]["corpus_sha256"] == full["authority"]["portable_function_corpus_sha256"]
    assert report["source"]["manifest_sha256"] == full["authority"]["corpus_manifest_sha256"]
    assert report["corpus"] == {
        "callother_operations": 283,
        "functions": 41538,
        "instructions": 2088152,
        "pcode_operations": 9600713,
    }
    assert len(report["used_userops"]) == 32
    assert report["unmapped_userops"] == []
    assert sum(row["uses"] for row in report["used_userops"]) == 283


def test_full_corpus_address_space_coverage_is_hash_pinned_and_resolved() -> None:
    report = json.loads((ROOT / "evidence/pcode_address_space_coverage_20261017.json").read_text())
    full = json.loads((ROOT / "evidence/full_function_instruction_corpus_20261017.json").read_text())
    assert report["format"] == "REVENGINSTR.PcodeAddressSpaceCoverage/1"
    assert report["source"]["program"] == full["authority"]["ghidra_program"] == "SHIFT.exe"
    assert report["source"]["language_id"] == full["authority"]["language_id"] == "x86:LE:32:default"
    assert report["source"]["corpus_sha256"] == full["authority"]["portable_function_corpus_sha256"]
    assert report["source"]["manifest_sha256"] == full["authority"]["corpus_manifest_sha256"]
    assert report["corpus"] == {
        "functions": 41538,
        "instructions": 2088152,
        "load_operations": 589262,
        "pcode_operations": 9600713,
        "store_operations": 704175,
    }
    assert report["used_address_spaces"] == [{
        "name": "ram",
        "space_id": "0x1a1",
        "load_operations": 589262,
        "store_operations": 704175,
        "operations": 1293437,
    }]
    assert report["unmapped_address_spaces"] == []
