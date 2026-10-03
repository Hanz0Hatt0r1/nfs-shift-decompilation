import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "shift_live_dump" / "join_memory_wrapper_argument_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("memory_wrapper_argument_join_forwarded_inputs", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _arg(index, expression):
    return {"index": index, "expression": expression}


def test_release_tail_call_preserves_effective_input_provenance(tmp_path):
    module = _load_module()
    callsites_path = tmp_path / "callsites.json"
    forwarding_path = tmp_path / "forwarding.json"

    _write(
        callsites_path,
        {
            "format": "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1",
            "source": "SHIFT.exe.c",
            "source_sha256": "source-sha",
            "callsites": [
                {
                    "caller": "FUN_00100000",
                    "wrapper": "FUN_00886930",
                    "occurrence": 0,
                    "arguments_parse_complete": True,
                    "argument_count": 3,
                    "arguments": [
                        _arg(0, "ptr_from_declared_ecx"),
                        _arg(1, "byte_selector"),
                        _arg(2, "ptr_from_stack"),
                    ],
                    "ghidra_direct_edge": True,
                }
            ],
        },
    )
    _write(
        forwarding_path,
        {
            "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
            "wrappers": [
                {
                    "name": "FUN_00886930",
                    "input_storage": ["ECX:4", "DL:1", "Stack[0x4]:4"],
                    "backend_forwarded_input_storage": ["DL:1", "Stack[0x4]:4"],
                    "declared_input_storage_not_forwarded_to_backend": ["ECX:4"],
                    "forwarding_confirmed": True,
                    "call_sites": [
                        {
                            "instruction": "0x0088693b",
                            "target": "0x0064f4c0",
                            "target_name": "thunk_FUN_0064f3a0",
                            "target_calling_convention": "__fastcall",
                            "transfer_kind": "tail-call",
                            "arguments_resolved": True,
                            "incoming_state_uncertain": False,
                            "arguments": [
                                {
                                    "storage": "ECX:4",
                                    "source": "input:Stack[0x4]:4",
                                    "source_kind": "input",
                                    "resolved": True,
                                },
                                {
                                    "storage": "DL:1",
                                    "source": "input:DL:1",
                                    "source_kind": "input",
                                    "resolved": True,
                                },
                            ],
                        }
                    ],
                }
            ],
        },
    )

    report = module.join_memory_wrapper_argument_evidence(callsites_path, forwarding_path)
    row = report["rows"][0]

    assert row["forwarding_join_ready"] is True
    assert row["backend_calls"][0]["transfer_kind"] == "tail-call"
    assert row["backend_forwarded_input_storage"] == ["DL:1", "Stack[0x4]:4"]
    assert row["declared_input_storage_not_forwarded_to_backend"] == ["ECX:4"]
    assert row["source_arguments_forwarded_to_backend"] == [
        {
            "entry_storage": "DL:1",
            "source_argument_index": 1,
            "source_argument_expression": "byte_selector",
        },
        {
            "entry_storage": "Stack[0x4]:4",
            "source_argument_index": 2,
            "source_argument_expression": "ptr_from_stack",
        },
    ]
    assert row["source_arguments_not_forwarded_to_backend"] == [
        {
            "entry_storage": "ECX:4",
            "source_argument_index": 0,
            "source_argument_expression": "ptr_from_declared_ecx",
        }
    ]
    assert row["mapped_source_argument_indices"] == [1, 2]
    assert row["unmapped_source_argument_indices"] == [0]
    assert report["scope"]["backend_transfer_kind_preserved"] is True
    assert report["scope"]["backend_forwarded_input_storage_consumed"] is True
    assert report["scope"]["unforwarded_source_argument_semantics_proven"] is False
