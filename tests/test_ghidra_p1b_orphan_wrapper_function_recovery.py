import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_p1b_orphan_wrapper_function_recovery.py"
    )
    spec = importlib.util.spec_from_file_location("p1b_orphan_wrapper_function_recovery", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fixture():
    module = _load_module()
    call_ref = {
        "from": "0x00001001",
        "type": "UNCONDITIONAL_CALL",
        "instruction": "CALL 0x00002000",
    }
    call = {
        "address": "0x00001001",
        "bytes": "e8fa0f0000",
        "mnemonic": "CALL",
        "text": "CALL 0x00002000",
        "references": [{"to": "0x00002000", "type": "UNCONDITIONAL_CALL"}],
        "pcode": [{}],
    }
    instructions = [
        {"address": "0x00001000", "bytes": "56", "mnemonic": "PUSH", "references": [], "pcode": [{}]},
        call,
        {"address": "0x00001006", "bytes": "c3", "mnemonic": "RET", "references": [], "pcode": [{}]},
    ]
    previous = {
        "objdump_unresolved_direct_calls": {
            "unmatched_callsites": [{"callsite": "0x00001001", "target": "0x00002000"}],
        },
        "inventory_only_function_body_candidates": {"functions": [{"address": "0x00002000"}]},
        "combined_function_instruction_exports": {
            "unique_function_count": 744,
            "unique_instruction_count": 1000,
            "unique_pcode_instruction_count": 1000,
        },
    }
    address_metadata = [
        {"requested": "0x00001001", "program": "SHIFT.exe", "instruction_mnemonic": "CALL", "function_containing": None},
        {"requested": "0x00002000", "function_at": {"entry": "0x00002000", "name": "FUN_00002000"}, "block": {"name": ".text"}},
    ]
    target_references = [{"requested": "0x00002000", "references": [call_ref]}]
    callsite_slices = [{"instructions": [call]}]
    candidate_metadata = [{
        "requested": "0x00001000",
        "function_at": None,
        "function_containing": None,
        "instruction_mnemonic": "PUSH",
        "block": {"name": ".text", "execute": True},
    }]
    entry_references = [{
        "requested": "0x00001000",
        "references": [{"from": "0x00003000", "type": "DATA", "instruction": "MOV dword ptr [0x00004000],0x1000"}],
    }]
    function_summaries = [{
        "entry": "0x00001000",
        "callsite": "0x00001001",
        "target": "0x00002000",
        "return": "0x00001006",
        "function_name": "FUN_00001000",
        "body_bytes": "7",
        "instruction_count": "3",
    }]
    function_exports = [{
        "found": True,
        "requested": "0x00001000",
        "function": {"address": "0x00001000", "name": "FUN_00001000", "size": 7},
        "instruction_count": 3,
        "instructions": instructions,
    }]
    recovered_target_references = [{
        "requested": "0x00002000",
        "references": [{
            **call_ref,
            "function_address": "0x00001000",
            "function_name": "FUN_00001000",
        }],
    }]
    args = (
        module.RETAIL_SHA256,
        previous,
        address_metadata,
        target_references,
        callsite_slices,
        candidate_metadata,
        entry_references,
        function_summaries,
        function_exports,
        recovered_target_references,
        {},
        "copy",
    )
    return module, args


def test_reconciles_orphan_call_and_adds_exact_wrapper_body():
    module, args = _fixture()
    report = module.compose_report(*args)
    assert report["unresolved_callsite_reconciliation"]["exact_ghidra_call_instruction_and_reference_count"] == 1
    assert report["unresolved_callsite_reconciliation"]["previously_inventory_only_callee_function_count_now_callsite_confirmed"] == 1
    assert report["recovered_orphan_wrapper_functions"]["function_count"] == 1
    assert report["recovered_orphan_wrapper_functions"]["instruction_count"] == 3
    assert report["combined_function_instruction_exports"]["unique_function_count"] == 745
    assert report["adjudication"]["caller_functions_added_to_original_project"] is False


def test_rejects_wrapper_without_exact_callsite_reference():
    module, args = _fixture()
    callsite_slices = [dict(args[4][0], instructions=[dict(args[4][0]["instructions"][0], references=[])])]
    with pytest.raises(ValueError, match="did not confirm exact CALL reference"):
        module.compose_report(*args[:4], callsite_slices, *args[5:])
