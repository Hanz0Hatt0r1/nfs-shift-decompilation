import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "join_memory_wrapper_argument_evidence.py"
        spec = importlib.util.spec_from_file_location("join_memory_wrapper_argument_evidence", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _arg(index, expression):
    return {
        "index": index,
        "expression": expression,
        "kind": "compound-expression",
        "integer_literals": [],
        "simple_integer_value": None,
    }


def _callsites():
    return {
        "format": "SHIFT-MEMORY-WRAPPER-CALLSITES/1",
        "source": "SHIFT.exe.c",
        "source_sha256": "source-sha",
        "callsites": [
            {
                "caller": "FUN_00100000",
                "wrapper": "FUN_008868c0",
                "wrapper_address": "0x008868c0",
                "side": "create",
                "occurrence": 0,
                "observed_argument_count": 1,
                "physical_parameter_count": 1,
                "arity_matches_physical_parameter_count": True,
                "arguments": [_arg(0, "0xe4")],
                "ghidra_direct_edge": True,
            },
            {
                "caller": "FUN_00100010",
                "wrapper": "FUN_00886900",
                "wrapper_address": "0x00886900",
                "side": "create",
                "occurrence": 0,
                "observed_argument_count": 3,
                "physical_parameter_count": 3,
                "arity_matches_physical_parameter_count": True,
                "arguments": [
                    _arg(0, "count * 0x10"),
                    _arg(1, "pool_id"),
                    _arg(2, "4"),
                ],
                "ghidra_direct_edge": True,
            },
            {
                "caller": "FUN_00100020",
                "wrapper": "FUN_00886900",
                "wrapper_address": "0x00886900",
                "side": "create",
                "occurrence": 0,
                "observed_argument_count": 2,
                "physical_parameter_count": 3,
                "arity_matches_physical_parameter_count": False,
                "arguments": [_arg(0, "0x20"), _arg(1, "4")],
                "ghidra_direct_edge": False,
            },
        ],
    }


def _forward_arg(storage, source, source_kind="input"):
    return {
        "storage": storage,
        "source": source,
        "source_kind": source_kind,
        "resolved": source != "unresolved",
    }


def _forwarding():
    return {
        "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
        "wrappers": [
            {
                "name": "FUN_008868c0",
                "address": "0x008868c0",
                "input_storage": ["Stack[0x4]:4"],
                "forwarding_confirmed": True,
                "call_sites": [
                    {
                        "instruction": "0x008868c9",
                        "target": "0x006382b0",
                        "target_name": "FUN_006382b0",
                        "target_calling_convention": "__fastcall",
                        "arguments_resolved": True,
                        "incoming_state_uncertain": False,
                        "arguments": [
                            _forward_arg("ECX:4", "input:Stack[0x4]:4"),
                            _forward_arg("EDX:4", "constant:0x4", "constant"),
                        ],
                    }
                ],
            },
            {
                "name": "FUN_00886900",
                "address": "0x00886900",
                "input_storage": ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
                "forwarding_confirmed": True,
                "call_sites": [
                    {
                        "instruction": "0x00886911",
                        "target": "0x00638020",
                        "target_name": "FUN_00638020",
                        "target_calling_convention": "__fastcall",
                        "arguments_resolved": True,
                        "incoming_state_uncertain": False,
                        "arguments": [
                            _forward_arg("ECX:4", "input:Stack[0x4]:4"),
                            _forward_arg("EDX:4", "input:Stack[0x8]:4"),
                            _forward_arg("Stack[0x4]:4", "input:Stack[0xc]:4"),
                        ],
                    }
                ],
            },
        ],
    }


def _row(report, caller):
    return next(row for row in report["rows"] if row["caller"] == caller)


def test_joins_source_expressions_to_backend_storage_without_semantic_names(tmp_path):
    module = _load_module()
    callsites_path = tmp_path / "callsites.json"
    forwarding_path = tmp_path / "forwarding.json"
    _write(callsites_path, _callsites())
    _write(forwarding_path, _forwarding())

    report = module.join_memory_wrapper_argument_evidence(callsites_path, forwarding_path)

    assert report["format"] == "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
    assert report["callsite_count"] == 3
    assert report["forwarding_join_ready_callsite_count"] == 2
    assert report["ghidra_crosschecked_join_callsite_count"] == 2
    assert report["backend_argument_count"] == 8
    assert report["source_mapped_backend_argument_count"] == 4
    assert report["wrapper_internal_backend_argument_count"] == 1
    assert report["unresolved_backend_argument_count"] == 3

    c0 = _row(report, "FUN_00100000")
    args = c0["backend_calls"][0]["arguments"]
    assert args[0]["backend_storage"] == "ECX:4"
    assert args[0]["source_argument_index"] == 0
    assert args[0]["source_argument_expression"] == "0xe4"
    assert args[0]["source_argument_mapped"] is True
    assert args[1]["forwarding_source"] == "constant:0x4"
    assert args[1]["wrapper_internal_source"] is True
    assert args[1]["source_argument_index"] is None

    f900 = _row(report, "FUN_00100010")
    backend = f900["backend_calls"][0]["arguments"]
    assert [arg["source_argument_expression"] for arg in backend] == [
        "count * 0x10",
        "pool_id",
        "4",
    ]
    assert f900["mapped_source_argument_indices"] == [0, 1, 2]
    assert f900["unmapped_source_argument_indices"] == []

    mismatch = _row(report, "FUN_00100020")
    assert mismatch["forwarding_record_present"] is True
    assert mismatch["forwarding_confirmed"] is True
    assert mismatch["forwarding_join_ready"] is False
    assert mismatch["ghidra_crosschecked_join"] is False
    assert mismatch["mapped_source_argument_indices"] == []
    assert mismatch["unmapped_source_argument_indices"] == [0, 1]
    assert "source_arity_vs_forwarding_input_storage" in mismatch["missing"]
    assert "source_arity_vs_physical_parameter_count" in mismatch["missing"]
    assert all(
        arg["source_argument_mapped"] is False
        for arg in mismatch["backend_calls"][0]["arguments"]
    )

    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["allocation_size_role_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_missing_forwarding_record_is_preserved_as_blocker(tmp_path):
    module = _load_module()
    callsites = _callsites()
    callsites["callsites"] = [
        {
            "caller": "FUN_00100030",
            "wrapper": "FUN_00886930",
            "observed_argument_count": 3,
            "physical_parameter_count": 3,
            "arity_matches_physical_parameter_count": True,
            "arguments": [_arg(0, "ptr"), _arg(1, "kind"), _arg(2, "flags")],
            "ghidra_direct_edge": True,
        }
    ]
    callsites_path = tmp_path / "callsites.json"
    forwarding_path = tmp_path / "forwarding.json"
    _write(callsites_path, callsites)
    _write(forwarding_path, _forwarding())

    report = module.join_memory_wrapper_argument_evidence(callsites_path, forwarding_path)
    row = report["rows"][0]
    assert row["forwarding_record_present"] is False
    assert row["forwarding_join_ready"] is False
    assert row["missing"] == ["forwarding_record"]
    assert row["unmapped_source_argument_indices"] == [0, 1, 2]


def test_rejects_wrong_input_formats(tmp_path):
    module = _load_module()
    callsites_path = tmp_path / "callsites.json"
    forwarding_path = tmp_path / "forwarding.json"
    _write(callsites_path, {"format": "wrong"})
    _write(forwarding_path, _forwarding())

    try:
        module.join_memory_wrapper_argument_evidence(callsites_path, forwarding_path)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-CALLSITES/1" in str(exc)
    else:
        raise AssertionError("wrong callsite format must fail")
