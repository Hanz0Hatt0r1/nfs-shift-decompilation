import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_release_wrapper_callsites.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_release_wrapper_callsites", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands=None, *, fallthrough=None, target=None):
    refs = [] if target is None else [{"to": target, "type": "UNCONDITIONAL_CALL"}]
    flows = [] if target is None else [target]
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": " ".join([mnemonic] + list(operands or [])),
        "operands": list(operands or []),
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": flows,
        "references": refs,
    }


def _row(address, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "size": len(instructions),
            "calling_convention": "__cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_inventory(path: Path):
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1",
                "selected_caller_count": 2,
                "truncated": False,
                "callers": [
                    {
                        "address": "0x00100000",
                        "call_count": 1,
                        "calls": [
                            {
                                "instruction": "0x0010000a",
                                "wrapper_address": "0x00886930",
                                "wrapper": "FUN_00886930",
                            }
                        ],
                    },
                    {
                        "address": "0x00200000",
                        "call_count": 1,
                        "calls": [
                            {
                                "instruction": "0x00200010",
                                "wrapper_address": "0x00886950",
                                "wrapper": "FUN_00886950",
                            }
                        ],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_callsites_recover_dl_constants_and_pointer_duplication(tmp_path):
    module = _load_module()
    inventory = tmp_path / "inventory.json"
    instructions = tmp_path / "callers.jsonl"
    _write_inventory(inventory)

    caller_930 = [
        _ins("0x00100000", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x00100004"),
        _ins("0x00100004", "PUSH", ["ECX"], fallthrough="0x00100005"),
        _ins("0x00100005", "XOR", ["EDX", "EDX"], fallthrough="0x00100007"),
        _ins("0x00100007", "NOP", [], fallthrough="0x0010000a"),
        _ins("0x0010000a", "CALL", ["0x00886930"], fallthrough="0x0010000f", target="0x00886930"),
        _ins("0x0010000f", "RET"),
    ]
    caller_950 = [
        _ins("0x00200000", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x00200004"),
        _ins("0x00200004", "MOV", ["EAX", "dword ptr [ESP + 0x8]"], fallthrough="0x00200008"),
        _ins("0x00200008", "PUSH", ["EAX"], fallthrough="0x00200009"),
        _ins("0x00200009", "PUSH", ["ECX"], fallthrough="0x0020000a"),
        _ins("0x0020000a", "MOV", ["DL", "0x1"], fallthrough="0x0020000d"),
        _ins("0x0020000d", "NOP", [], fallthrough="0x00200010"),
        _ins("0x00200010", "CALL", ["0x00886950"], fallthrough="0x00200015", target="0x00886950"),
        _ins("0x00200015", "RET"),
    ]
    _write_jsonl(
        instructions,
        [_row("0x00100000", caller_930), _row("0x00200000", caller_950)],
    )

    report = module.analyze_release_wrapper_callsites(inventory, instructions)

    assert report["callsite_count"] == 2
    assert report["resolved_callsite_count"] == 2
    assert report["all_selected_callsites_resolved"] is True
    first, second = report["callsites"]
    assert first["wrapper"] == "FUN_00886930"
    assert first["dl_source"] == "low8(constant:0x0)"
    assert first["dl_constant_low8"] == 0
    assert first["released_pointer_candidate_source"] == "input:Stack[0x4]:4"
    assert first["ecx_matches_stack_pointer_source"] is True
    assert second["wrapper"] == "FUN_00886950"
    assert second["dl_source"] == "constant:0x1"
    assert second["dl_constant_low8"] == 1
    assert second["released_pointer_candidate_source"] == "input:Stack[0x4]:4"
    assert second["ecx_matches_stack_pointer_source"] is True
    stack8 = next(item for item in second["arguments"] if item["storage"] == "Stack[0x8]:4")
    assert stack8["source"] == "input:Stack[0x8]:4"
    assert report["dl_constant_low8_histogram"] == [
        {"value": 0, "count": 1},
        {"value": 1, "count": 1},
    ]
    assert report["ecx_stack_pointer_duplicate_count"] == 2
    assert report["ecx_stack_pointer_duplicate_fraction"] == 1.0
    assert report["scope"]["release_byte_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False


def test_prior_unknown_call_keeps_release_callsite_fail_closed(tmp_path):
    module = _load_module()
    inventory = tmp_path / "inventory.json"
    instructions = tmp_path / "callers.jsonl"
    inventory.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1",
                "selected_caller_count": 1,
                "truncated": False,
                "callers": [
                    {
                        "address": "0x00100000",
                        "calls": [
                            {
                                "instruction": "0x00100010",
                                "wrapper_address": "0x00886930",
                                "wrapper": "FUN_00886930",
                            }
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    caller = [
        _ins("0x00100000", "CALL", ["0x00123456"], fallthrough="0x00100005", target="0x00123456"),
        _ins("0x00100005", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x00100009"),
        _ins("0x00100009", "PUSH", ["ECX"], fallthrough="0x0010000a"),
        _ins("0x0010000a", "XOR", ["EDX", "EDX"], fallthrough="0x0010000c"),
        _ins("0x0010000c", "NOP", [], fallthrough="0x00100010"),
        _ins("0x00100010", "CALL", ["0x00886930"], fallthrough="0x00100015", target="0x00886930"),
        _ins("0x00100015", "RET"),
    ]
    _write_jsonl(instructions, [_row("0x00100000", caller)])

    report = module.analyze_release_wrapper_callsites(inventory, instructions)

    assert report["resolved_callsite_count"] == 0
    assert report["all_selected_callsites_resolved"] is False
    site = report["callsites"][0]
    assert site["incoming_state_uncertain"] is True
    assert any("call target is not a modeled backend" in reason for reason in site["uncertainty_reasons"])
    assert report["dl_constant_low8_histogram"] == []


def test_missing_caller_export_is_reported(tmp_path):
    module = _load_module()
    inventory = tmp_path / "inventory.json"
    instructions = tmp_path / "callers.jsonl"
    _write_inventory(inventory)
    _write_jsonl(instructions, [_row("0x00100000", [_ins("0x00100000", "RET")])])

    report = module.analyze_release_wrapper_callsites(inventory, instructions)

    assert report["missing_caller_exports"] == ["0x00200000"]
    assert report["all_selected_callsites_resolved"] is False
