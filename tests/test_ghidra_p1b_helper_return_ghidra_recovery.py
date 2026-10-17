import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_p1b_helper_return_ghidra_recovery.py"
    )
    spec = importlib.util.spec_from_file_location("p1b_helper_return_ghidra_recovery", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _instruction(address, mnemonic, operands, *, pcode=None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
        "pcode": pcode or [],
    }


def test_indexes_only_ghidra_confirmed_call_targets_and_starts_at_function_entry():
    module = _load_module()
    functions = [
        {
            "address": "0x00001000",
            "name": "FUN_00001000",
            "size": 6,
            "mnemonic_sha256": "abc",
        },
        {"address": "0x00003000", "name": "FUN_00003000", "size": 1, "mnemonic_sha256": "def"},
    ]
    callgraph = [
        {
            "from_function": "0x00002000",
            "from_name": "FUN_00002000",
            "instruction": "0x00002004",
            "to": "0x00001000",
            "to_name": "FUN_00001000",
            "indirect": False,
        }
    ]
    target_exports = [
        {
            "found": True,
            "requested": "0x00001000",
            "function": {"address": "0x00001000", "name": "FUN_00001000", "size": 6},
            "instruction_count": 3,
            "instructions": [
                _instruction("0x00000fff", "CALL", ["0x00002000"], pcode=[{}]),
                _instruction("0x00001000", "LEA", ["EAX", "[ECX + 0x374]"], pcode=[{}]),
                _instruction("0x00001005", "RET", [], pcode=[{}]),
            ],
        }
    ]
    prior_exports = [
        {
            "found": True,
            "function": {"address": "0x00002000"},
            "instruction_count": 1,
            "instructions": [_instruction("0x00002000", "RET", [], pcode=[{}])],
        }
    ]
    unconfirmed_exports = [
        {
            "found": True,
            "requested": "0x00003000",
            "function": {"address": "0x00003000", "name": "FUN_00003000", "size": 1},
            "instruction_count": 1,
            "instructions": [_instruction("0x00003000", "RET", [], pcode=[{}])],
        }
    ]

    report = module.compose_report(
        [(0x2004, 0x1000), (0x2010, 0x3000)],
        callgraph,
        functions,
        target_exports,
        prior_exports,
        {"callgraph.jsonl": "callgraph-hash"},
        "target-hash",
        "prior-hash",
        module.RETAIL_SHA256,
        unconfirmed_exports,
        "unconfirmed-hash",
    )

    unresolved = report["objdump_unresolved_direct_calls"]
    assert unresolved["callsite_count"] == 2
    assert unresolved["exact_ghidra_direct_callgraph_match_count"] == 1
    assert unresolved["unmatched_callsite_count"] == 1
    assert unresolved["unconfirmed_target_function_entry_count"] == 1
    assert unresolved["unique_confirmed_target_function_count"] == 1
    assert report["function_body_recovery"]["qualified_entry_argument_plus_0x374_function_count"] == 1
    function = report["function_body_recovery"]["recovered_functions"][0]
    assert function["helper_return_probe"]["qualified_entry_argument_plus_0x374"] is True
    assert function["helper_return_probe"]["return_argument_channel"] == "ecx"
    assert report["adjudication"]["automatic_function_renaming_performed"] is False
    assert report["adjudication"]["p1_3_control_producer_complete"] is False
    candidates = report["inventory_only_function_body_candidates"]
    assert candidates["exact_unresolved_callsite_callgraph_match_count"] == 0
    assert candidates["instruction_export_sha256"] == "unconfirmed-hash"
    assert candidates["functions"][0]["address"] == "0x00003000"
    assert report["combined_function_instruction_exports"]["unique_function_count"] == 3


def test_rejects_instruction_export_with_unconfirmed_target():
    module = _load_module()
    with pytest.raises(ValueError, match="does not match confirmed target function set"):
        module.compose_report(
            [(0x2004, 0x1000)],
            [],
            [{"address": "0x00001000", "name": "FUN_00001000", "size": 1}],
            [
                {
                    "found": True,
                    "function": {"address": "0x00001000"},
                    "instructions": [_instruction("0x00001000", "RET", [])],
                }
            ],
            [],
            {},
            "target-hash",
            "prior-hash",
            module.RETAIL_SHA256,
        )


def test_rejects_another_executable():
    module = _load_module()
    with pytest.raises(ValueError, match="unexpected SHIFT retail executable"):
        module.compose_report([], [], [], [], [], {}, "x", "y", "0" * 64)
