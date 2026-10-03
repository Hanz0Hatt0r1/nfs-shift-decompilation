import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_memory_backend_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_memory_backend_evidence", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic="NOP", *, flows=None, refs=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic,
        "operands": [],
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
        "function": {
            "address": address,
            "name": name,
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


def _instruction_rows():
    return [
        _row(
            "0x00638020",
            "FUN_00638020",
            [
                _ins("0x00638020"),
                _ins("0x006381b1"),
            ],
        ),
        _row("0x006382b0", "FUN_006382b0", [_ins("0x006382b0")]),
        _row("0x0064f260", "FUN_0064f260", [_ins("0x0064f260")]),
        _row(
            "0x0064f4c0",
            "thunk_FUN_0064f3a0",
            [
                _ins(
                    "0x0064f4c0",
                    "JMP",
                    flows=["0x0064f3a0"],
                    refs=[{"to": "0x0064f3a0", "type": "UNCONDITIONAL_JUMP"}],
                )
            ],
        ),
        _row(
            "0x0064f3a0",
            "FUN_0064f3a0",
            [
                _ins(
                    "0x0064f3b2",
                    "CALL",
                    flows=["0x00657c30"],
                    refs=[{"to": "0x00657c30", "type": "UNCONDITIONAL_CALL"}],
                )
            ],
        ),
        _row(
            "0x00657c30",
            "FUN_00657c30",
            [
                _ins("0x00657c30"),
                _ins("0x00657c88"),
            ],
        ),
    ]


def _write_ghidra(root):
    root.mkdir()
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00aec0e8",
                "value": "Unable to allocate %d bytes of memory from the pool (%s)",
                "xrefs": ["0x006381b1"],
                "functions": ["0x00638020"],
            },
            {
                "address": "0x00aec120",
                "value": "Error freeing small alloc (no head) '0x%p' from pool: '%s'",
                "xrefs": ["0x00657c88"],
                "functions": ["0x00657c30"],
            },
        ],
    )
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": "0x0064f4c0",
                "instruction": "0x0064f4c0",
                "to": "0x0064f3a0",
                "to_name": "FUN_0064f3a0",
                "indirect": False,
            },
            {
                "from_function": "0x0064f3a0",
                "instruction": "0x0064f3b2",
                "to": "0x00657c30",
                "to_name": "FUN_00657c30",
                "indirect": False,
            },
        ],
    )


def test_crosschecks_backend_instruction_bodies_and_pool_diagnostics(tmp_path):
    module = _load_module()
    instructions = tmp_path / "memory_backend_instructions.jsonl"
    ghidra = tmp_path / "ghidra"
    _write_jsonl(instructions, _instruction_rows())
    _write_ghidra(ghidra)

    report = module.analyze_memory_backend_evidence(instructions, ghidra)

    assert report["format"] == "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
    assert report["target_count"] == 6
    assert report["all_targets_present"] is True
    assert report["allocation_backend_diagnostic_proven"] is True
    assert report["free_backend_diagnostic_proven"] is True
    assert report["release_thunk_to_free_diagnostic_path"] == [
        "0x0064f4c0",
        "0x0064f3a0",
        "0x00657c30",
    ]
    assert report["release_thunk_to_free_diagnostic_path_proven"] is True

    by_address = {row["address"]: row for row in report["functions"]}
    alloc = by_address["0x00638020"]["diagnostic_references"][0]
    assert alloc["kind"] == "pool-allocation-diagnostic"
    assert alloc["instruction_export_xrefs"] == ["0x006381b1"]
    assert alloc["xref_instruction_covered"] is True

    free = by_address["0x00657c30"]["diagnostic_references"][0]
    assert free["kind"] == "pool-free-diagnostic"
    assert free["instruction_export_xrefs"] == ["0x00657c88"]

    thunk = by_address["0x0064f4c0"]
    assert thunk["direct_transfers"] == [
        {
            "instruction": "0x0064f4c0",
            "transfer_kind": "tail-call",
            "target": "0x0064f3a0",
            "target_in_backend_cluster": True,
        }
    ]

    assert report["scope"]["allocation_size_role_proven"] is False
    assert report["scope"]["pool_selector_role_proven"] is False
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_missing_targeted_backend_fails_closed(tmp_path):
    module = _load_module()
    instructions = tmp_path / "memory_backend_instructions.jsonl"
    ghidra = tmp_path / "ghidra"
    _write_jsonl(instructions, _instruction_rows()[:-1])
    _write_ghidra(ghidra)

    try:
        module.analyze_memory_backend_evidence(instructions, ghidra)
    except ValueError as exc:
        assert "instruction export missing backend targets" in str(exc)
        assert "0x00657c30" in str(exc)
    else:
        raise AssertionError("missing backend target must fail closed")
