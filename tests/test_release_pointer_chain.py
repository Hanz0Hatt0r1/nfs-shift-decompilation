import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_release_pointer_chain.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_release_pointer_chain", ANALYZER)
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


def _row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {"address": address, "name": name, "size": len(instructions)},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _rows():
    backend = [
        _ins("0x0064f3a0", "MOV", ["ECX", "EDX"]),
        _ins(
            "0x0064f3a2",
            "CALL",
            ["0x00657c30"],
            refs=[{"to": "0x00657c30", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00657c30"],
        ),
    ]
    thunk = [
        _ins("0x0064f4c0", "MOV", ["EDX", "ECX"]),
        _ins(
            "0x0064f4c2",
            "JMP",
            ["0x0064f3a0"],
            refs=[{"to": "0x0064f3a0", "type": "UNCONDITIONAL_JUMP"}],
            flows=["0x0064f3a0"],
        ),
    ]
    return [
        _row("0x0064f4c0", "thunk_FUN_0064f3a0", thunk),
        _row("0x0064f3a0", "FUN_0064f3a0", backend),
        _row("0x00657c30", "FUN_00657c30", [_ins("0x00657c30", "RET")]),
    ]


def _slice(storage="ECX:4", proven=True):
    return {
        "format": "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1",
        "free_pointer_role_proven": proven,
        "free_pointer_entry_storage": storage if proven else None,
    }


def test_traces_free_percent_p_back_to_release_thunk_entry(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free_slice.json"
    _write_jsonl(instructions, _rows())
    free_slice.write_text(json.dumps(_slice()), encoding="utf-8")

    report = module.analyze_release_pointer_chain(instructions, free_slice)

    assert report["format"] == "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
    assert report["free_pointer_storage"] == "ECX:4"
    assert report["release_backend_pointer_storage"] == "EDX:4"
    assert report["release_thunk_pointer_storage"] == "ECX:4"
    assert report["release_pointer_chain_proven"] is True
    assert report["missing"] == []
    assert report["hops"] == [
        {
            "from": "0x0064f3a0",
            "to": "0x00657c30",
            "instruction": "0x0064f3a2",
            "transfer_kind": "call",
            "target_storage": "ECX:4",
            "source": "entry:EDX:4",
            "source_entry_storage": "EDX:4",
            "proven": True,
            "reasons": [],
        },
        {
            "from": "0x0064f4c0",
            "to": "0x0064f3a0",
            "instruction": "0x0064f4c2",
            "transfer_kind": "tail-call",
            "target_storage": "EDX:4",
            "source": "entry:ECX:4",
            "source_entry_storage": "ECX:4",
            "proven": True,
            "reasons": [],
        },
    ]
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["delete_kind_role_proven"] is False
    assert report["scope"]["wrapper_source_pointer_role_proven"] is False


def test_maps_first_callee_stack_parameter_from_last_push(tmp_path):
    module = _load_module()
    rows = _rows()
    backend = next(row for row in rows if row["function"]["address"] == "0x0064f3a0")
    backend["instructions"] = [
        _ins("0x0064f3a0", "PUSH", ["EDX"]),
        _ins(
            "0x0064f3a2",
            "CALL",
            ["0x00657c30"],
            refs=[{"to": "0x00657c30", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00657c30"],
        ),
    ]
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free_slice.json"
    _write_jsonl(instructions, rows)
    free_slice.write_text(json.dumps(_slice(storage="Stack[0x4]:4")), encoding="utf-8")

    report = module.analyze_release_pointer_chain(instructions, free_slice)
    assert report["release_backend_pointer_storage"] == "EDX:4"
    assert report["release_thunk_pointer_storage"] == "ECX:4"
    assert report["release_pointer_chain_proven"] is True


def test_missing_free_diagnostic_proof_blocks_chain(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free_slice.json"
    _write_jsonl(instructions, _rows())
    free_slice.write_text(json.dumps(_slice(proven=False)), encoding="utf-8")

    report = module.analyze_release_pointer_chain(instructions, free_slice)
    assert report["release_pointer_chain_proven"] is False
    assert report["release_thunk_pointer_storage"] is None
    assert report["hops"] == []
    assert "free_diagnostic_pointer_storage_not_proven" in report["missing"]


def test_volatile_clobber_between_entry_and_free_call_fails_closed(tmp_path):
    module = _load_module()
    rows = _rows()
    backend = next(row for row in rows if row["function"]["address"] == "0x0064f3a0")
    backend["instructions"] = [
        _ins("0x0064f3a0", "MOV", ["ECX", "EDX"]),
        _ins(
            "0x0064f3a1",
            "CALL",
            ["0x00601000"],
            refs=[{"to": "0x00601000", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00601000"],
        ),
        _ins(
            "0x0064f3a6",
            "CALL",
            ["0x00657c30"],
            refs=[{"to": "0x00657c30", "type": "UNCONDITIONAL_CALL"}],
            flows=["0x00657c30"],
        ),
    ]
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free_slice.json"
    _write_jsonl(instructions, rows)
    free_slice.write_text(json.dumps(_slice()), encoding="utf-8")

    report = module.analyze_release_pointer_chain(instructions, free_slice)
    assert report["release_pointer_chain_proven"] is False
    assert report["hops"][0]["proven"] is False
    assert "release_backend_to_free_backend_pointer_not_proven" in report["missing"]
