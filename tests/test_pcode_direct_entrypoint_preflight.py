from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_pcode_direct_entrypoint_preflight.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("pcode_direct_entrypoint_preflight", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compact(
    address: str,
    mnemonic: str,
    flows: list[str],
    flow_type: str | None = None,
) -> dict:
    if flow_type is None:
        flow_type = "UNCONDITIONAL_CALL" if mnemonic == "CALL" else "UNCONDITIONAL_JUMP"
    return {
        "format": "SHIFT.GhidraCompactInstructionStream/1",
        "kind": "instruction",
        "address": address,
        "mnemonic": mnemonic,
        "operands": [],
        "flow_type": flow_type,
        "flows": flows,
    }


def _instruction(address: str) -> dict:
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
        "pcode": [{"opcode": "COPY"}],
    }


def _function(address: str, instructions: list[str]) -> dict:
    return {
        "format": "REVENGINSTR.GhidraFunctionInstructions/1",
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
        "instructions": [_instruction(value) for value in instructions],
    }


def test_preflight_batches_direct_non_entry_targets(tmp_path: Path) -> None:
    tool = _load_tool()
    compact = tmp_path / "compact.jsonl.gz"
    corpus = tmp_path / "functions.jsonl.gz"

    compact_rows = [
        {
            "format": "SHIFT.GhidraCompactInstructionStream/1",
            "kind": "header",
            "program": "SHIFT.exe",
            "executable_md5": None,
            "language_id": "x86:LE:32:default",
            "image_base": "0x00400000",
            "pointer_size": 4,
        },
        _compact("0x00401000", "CALL", ["0x00402000"]),
        _compact("0x00401002", "CALL", ["0x00402004"]),
        _compact("0x00401004", "JMP", ["0x00401008"]),
        _compact("0x00401006", "JMP", ["0x00402006"]),
        _compact("0x00401008", "CALL", ["0x00403000"]),
        _compact("0x0040100a", "CALL", ["0x00500000"]),
        _compact(
            "0x0040100c", "JZ", ["0x00402008"], "CONDITIONAL_JUMP"
        ),
        _compact(
            "0x0040100e", "JNZ", ["0x00401010"], "CONDITIONAL_JUMP"
        ),
        _compact("0x00402000", "NOP", []),
        _compact("0x00402004", "NOP", []),
        _compact("0x00402006", "NOP", []),
        _compact("0x00402008", "NOP", []),
        _compact("0x00403000", "NOP", []),
    ]
    with gzip.open(compact, "wt", encoding="utf-8") as stream:
        for row in compact_rows:
            stream.write(json.dumps(row) + "\n")

    corpus_rows = [
        _function(
            "0x00401000",
            [
                "0x00401000",
                "0x00401002",
                "0x00401004",
                "0x00401006",
                "0x00401008",
                "0x0040100a",
                "0x0040100c",
                "0x0040100e",
                "0x00401010",
            ],
        ),
        _function(
            "0x00402000",
            ["0x00402000", "0x00402004", "0x00402006", "0x00402008"],
        ),
    ]
    with gzip.open(corpus, "wt", encoding="utf-8") as stream:
        for row in corpus_rows:
            stream.write(json.dumps(row) + "\n")

    report = tool.build(compact, corpus)

    assert report["format"] == "NFSShift.PcodeDirectEntrypointPreflight/2"
    assert report["function_corpus_count"] == 2
    assert report["direct_transfer_count"] == 8
    assert report["classification_counts"] == {
        "covered_function_entry": 1,
        "internal_jump": 1,
        "internal_conditional_branch": 1,
        "call_into_function_interior": 1,
        "jump_into_other_function_interior": 1,
        "conditional_branch_into_function_interior": 1,
        "orphan_direct_target": 1,
        "outside_instruction_stream": 1,
    }
    assert report["supplemental_entrypoint_unique_targets"] == [
        "0x00402004",
        "0x00402006",
        "0x00402008",
        "0x00403000",
    ]
    assert report["supplemental_entrypoint_candidate_count"] == 4
    assert all(row["target_is_instruction"] is True for row in report["candidates"])
    assert report["scope"]["indirect_transfers_included"] is False
    assert report["scope"]["direct_conditional_branches_included"] is True
    assert report["scope"]["candidate_is_not_semantic_proof"] is True
