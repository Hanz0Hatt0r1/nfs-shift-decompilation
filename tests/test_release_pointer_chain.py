import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_release_pointer_chain.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_release_pointer_chain", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands=None, *, fallthrough=None, target=None, ref_type="UNCONDITIONAL_CALL"):
    refs = [] if target is None else [{"to": target, "type": ref_type}]
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


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _backend_rows(*, backend_pointer_from="ECX", thunk_pointer_from="ECX"):
    release_backend = [
        _ins("0x0064f3a0", "PUSH", ["EBP"], fallthrough="0x0064f3a1"),
        _ins("0x0064f3a1", "MOV", ["EBP", "ESP"], fallthrough="0x0064f3a3"),
    ]
    if backend_pointer_from == "STACK":
        release_backend.append(
            _ins("0x0064f3a3", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x0064f3a6")
        )
        call_address = "0x0064f3a6"
    else:
        call_address = "0x0064f3a3"
    release_backend.append(
        _ins(call_address, "CALL", ["0x00657c30"], fallthrough="0x0064f3ab", target="0x00657c30")
    )
    release_backend.append(_ins("0x0064f3ab", "RET"))

    thunk = []
    if thunk_pointer_from == "STACK":
        thunk.extend(
            [
                _ins("0x0064f4c0", "PUSH", ["EBP"], fallthrough="0x0064f4c1"),
                _ins("0x0064f4c1", "MOV", ["EBP", "ESP"], fallthrough="0x0064f4c3"),
                _ins("0x0064f4c3", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x0064f4c6"),
                _ins("0x0064f4c6", "POP", ["EBP"], fallthrough="0x0064f4c7"),
                _ins("0x0064f4c7", "JMP", ["0x0064f3a0"], target="0x0064f3a0", ref_type="UNCONDITIONAL_JUMP"),
            ]
        )
    else:
        thunk.append(
            _ins("0x0064f4c0", "JMP", ["0x0064f3a0"], target="0x0064f3a0", ref_type="UNCONDITIONAL_JUMP")
        )

    free_diag = [_ins("0x00657c30", "RET")]
    return [
        _row("0x0064f4c0", "thunk_FUN_0064f3a0", thunk),
        _row("0x0064f3a0", "FUN_0064f3a0", release_backend),
        _row("0x00657c30", "FUN_00657c30", free_diag),
    ]


def _write_free_slice(path: Path, *, proven=True, storage="ECX:4"):
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1",
                "free_pointer_role_proven": proven,
                "free_pointer_entry_storage": storage if proven else None,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_forwarding(path: Path, *, source930="input:Stack[0x4]:4", source950="input:Stack[0x4]:4"):
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
                "wrappers": [
                    {
                        "address": "0x00886930",
                        "name": "FUN_00886930",
                        "forwarding_confirmed": True,
                        "call_sites": [
                            {
                                "instruction": "0x0088693b",
                                "target": "0x0064f4c0",
                                "transfer_kind": "tail-call",
                                "arguments": [
                                    {"storage": "ECX:4", "source": source930, "resolved": True},
                                    {"storage": "DL:1", "source": "input:DL:1", "resolved": True},
                                ],
                            }
                        ],
                    },
                    {
                        "address": "0x00886950",
                        "name": "FUN_00886950",
                        "forwarding_confirmed": True,
                        "call_sites": [
                            {
                                "instruction": "0x0088696c",
                                "target": "0x0064f4c0",
                                "transfer_kind": "tail-call",
                                "arguments": [
                                    {"storage": "ECX:4", "source": source950, "resolved": True},
                                    {"storage": "DL:1", "source": "input:DL:1", "resolved": True},
                                ],
                            },
                            {
                                "instruction": "0x00886966",
                                "target": "0x0064f260",
                                "transfer_kind": "tail-call",
                                "arguments": [
                                    {"storage": "ECX:4", "source": "input:Stack[0x8]:4", "resolved": True},
                                    {"storage": "EDX:4", "source": "input:Stack[0x4]:4", "resolved": True},
                                ],
                            },
                        ],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_release_pointer_traces_free_percent_p_to_wrapper_stack_storage(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free.json"
    forwarding = tmp_path / "forwarding.json"
    _write_jsonl(instructions, _backend_rows())
    _write_free_slice(free_slice)
    _write_forwarding(forwarding)

    report = module.analyze_release_pointer_chain(instructions, free_slice, forwarding)

    assert report["free_pointer_diagnostic_storage"] == "ECX:4"
    assert report["release_backend_trace"]["transfer_proven"] is True
    assert report["release_backend_trace"]["caller_entry_storage"] == "ECX:4"
    assert report["release_thunk_trace"]["transfer_proven"] is True
    assert report["release_thunk_pointer_entry_storage"] == "ECX:4"
    assert report["release_pointer_to_wrapper_storage_proven"] is True
    assert report["proven_wrapper_path_count"] == 2
    assert [row["wrapper_input_storage"] for row in report["wrapper_paths"]] == [
        "Stack[0x4]:4",
        "Stack[0x4]:4",
    ]
    # The alternate 0064f260 path is intentionally outside the proven diagnostic chain.
    assert all(row["transfer_instruction"] != "0x00886966" for row in report["wrapper_paths"])
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["delete_kind_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False


def test_release_pointer_can_trace_standard_stack_entry_between_functions(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free.json"
    forwarding = tmp_path / "forwarding.json"
    _write_jsonl(instructions, _backend_rows(backend_pointer_from="STACK", thunk_pointer_from="STACK"))
    _write_free_slice(free_slice, storage="ECX:4")
    _write_forwarding(forwarding, source930="input:Stack[0x4]:4", source950="input:Stack[0x4]:4")

    report = module.analyze_release_pointer_chain(instructions, free_slice, forwarding)

    assert report["release_backend_trace"]["caller_entry_storage"] == "Stack[0x4]:4"
    # FUN_0064f3a0 pointer is its first stack argument; the thunk derives that from
    # its own first stack argument and therefore the wrapper backend storage would
    # also need to be Stack[0x4]:4. Retail forwarding currently exposes only ECX/DL
    # for this thunk, so the final wrapper join must fail closed.
    assert report["release_thunk_trace"]["transfer_proven"] is False
    assert report["release_pointer_to_wrapper_storage_proven"] is False


def test_release_pointer_chain_fails_closed_without_free_diagnostic_role(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free.json"
    forwarding = tmp_path / "forwarding.json"
    _write_jsonl(instructions, _backend_rows())
    _write_free_slice(free_slice, proven=False)
    _write_forwarding(forwarding)

    report = module.analyze_release_pointer_chain(instructions, free_slice, forwarding)

    assert report["release_backend_trace"]["transfer_proven"] is False
    assert report["release_thunk_trace"]["transfer_proven"] is False
    assert report["wrapper_path_count"] == 0
    assert report["release_pointer_to_wrapper_storage_proven"] is False


def test_release_pointer_chain_rejects_non_input_wrapper_source(tmp_path):
    module = _load_module()
    instructions = tmp_path / "backend.jsonl"
    free_slice = tmp_path / "free.json"
    forwarding = tmp_path / "forwarding.json"
    _write_jsonl(instructions, _backend_rows())
    _write_free_slice(free_slice)
    _write_forwarding(forwarding, source930="constant:0x0", source950="unresolved")

    report = module.analyze_release_pointer_chain(instructions, free_slice, forwarding)

    assert report["wrapper_path_count"] == 2
    assert report["proven_wrapper_path_count"] == 0
    assert report["release_pointer_to_wrapper_storage_proven"] is False
