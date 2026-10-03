import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_free_diagnostic_slice.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_free_diagnostic_slice", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands=None, *, refs=None, flows=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": " ".join([mnemonic] + list(operands or [])),
        "operands": list(operands or []),
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": list(flows or []),
        "references": list(refs or []),
    }


def _row(instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": "0x00657c30",
        "found": True,
        "function": {
            "address": "0x00657c30",
            "name": "FUN_00657c30",
            "size": len(instructions),
            "calling_convention": "__fastcall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_ghidra(root):
    root.mkdir()
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00aee94c",
                "value": "Error freeing small alloc (no head) '0x%p' from pool: '%s'\n",
                "xrefs": ["0x00657cb1"],
                "functions": ["0x00657c30"],
            }
        ],
    )


def test_proves_percent_p_from_entry_ecx_without_promoting_pool_selector(tmp_path):
    module = _load_module()
    instructions = [
        _ins("0x00657c30", "PUSH", ["EBP"]),
        _ins("0x00657c31", "MOV", ["EBP", "ESP"]),
        _ins("0x00657cad", "PUSH", ["EDX"]),
        _ins("0x00657cae", "PUSH", ["ECX"]),
        _ins(
            "0x00657cb1",
            "PUSH",
            ["0x00aee94c"],
            refs=[{"to": "0x00aee94c", "type": "DATA"}],
        ),
        _ins(
            "0x00657cb6",
            "CALL",
            ["0x00601000"],
            refs=[{"to": "0x00601000", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00601000"],
        ),
    ]
    export = tmp_path / "backend.jsonl"
    ghidra = tmp_path / "ghidra"
    _write_jsonl(export, [_row(instructions)])
    _write_ghidra(ghidra)

    report = module.analyze_free_diagnostic_slice(export, ghidra)

    assert report["format"] == "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"
    assert report["covered_diagnostic_xref_count"] == 1
    assert report["proven_site_count"] == 1
    assert report["free_pointer_role_proven"] is True
    assert report["free_pointer_entry_storage"] == "ECX:4"

    site = report["sites"][0]
    assert [arg["source"] for arg in site["arguments"][:3]] == [
        "diagnostic-format",
        "entry:ECX:4",
        "entry:EDX:4",
    ]
    assert site["pointer_vararg"]["entry_storage"] == "ECX:4"
    assert report["scope"]["pool_selector_role_proven"] is False
    assert report["scope"]["release_chain_argument_provenance_proven"] is False
    assert report["scope"]["release_flag_role_proven"] is False


def test_resolves_standard_ebp_stack_pointer_input(tmp_path):
    module = _load_module()
    instructions = [
        _ins("0x00657c30", "PUSH", ["EBP"]),
        _ins("0x00657c31", "MOV", ["EBP", "ESP"]),
        _ins("0x00657ca8", "MOV", ["EAX", "dword ptr [EBP + 0x8]"]),
        _ins("0x00657cad", "PUSH", ["EDX"]),
        _ins("0x00657cae", "PUSH", ["EAX"]),
        _ins(
            "0x00657cb1",
            "PUSH",
            ["0x00aee94c"],
            refs=[{"to": "0x00aee94c", "type": "DATA"}],
        ),
        _ins(
            "0x00657cb6",
            "CALL",
            ["0x00601000"],
            refs=[{"to": "0x00601000", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00601000"],
        ),
    ]
    export = tmp_path / "backend.jsonl"
    ghidra = tmp_path / "ghidra"
    _write_jsonl(export, [_row(instructions)])
    _write_ghidra(ghidra)

    report = module.analyze_free_diagnostic_slice(export, ghidra)
    assert report["free_pointer_role_proven"] is True
    assert report["free_pointer_entry_storage"] == "Stack[0x4]:4"


def test_branch_between_format_xref_and_call_fails_closed(tmp_path):
    module = _load_module()
    instructions = [
        _ins("0x00657c30", "PUSH", ["EBP"]),
        _ins("0x00657c31", "MOV", ["EBP", "ESP"]),
        _ins("0x00657cad", "PUSH", ["EDX"]),
        _ins("0x00657cae", "PUSH", ["ECX"]),
        _ins(
            "0x00657cb1",
            "PUSH",
            ["0x00aee94c"],
            refs=[{"to": "0x00aee94c", "type": "DATA"}],
        ),
        _ins("0x00657cb3", "JNZ", ["0x00657cc0"], flows=["0x00657cc0"]),
        _ins(
            "0x00657cb6",
            "CALL",
            ["0x00601000"],
            refs=[{"to": "0x00601000", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00601000"],
        ),
    ]
    export = tmp_path / "backend.jsonl"
    ghidra = tmp_path / "ghidra"
    _write_jsonl(export, [_row(instructions)])
    _write_ghidra(ghidra)

    report = module.analyze_free_diagnostic_slice(export, ghidra)
    assert report["free_pointer_role_proven"] is False
    assert report["proven_site_count"] == 0
    assert report["sites"][0]["diagnostic_call_found"] is False
