import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "join_memory_wrapper_argument_provenance.py"
    spec = importlib.util.spec_from_file_location("join_memory_wrapper_argument_provenance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _callsites() -> dict:
    return {
        "format": "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1",
        "callsites": [
            {
                "caller": "FUN_00100000",
                "wrapper": "FUN_00886900",
                "occurrence": 0,
                "source_statement": "p = FUN_00886900(0x38, pool_id, flags);",
                "arguments_parse_complete": True,
                "arguments": [
                    {"index": 0, "expression": "0x38", "integer_literals": [0x38], "is_exact_integer_literal": True, "exact_integer_value": 0x38},
                    {"index": 1, "expression": "pool_id", "integer_literals": [], "is_exact_integer_literal": False, "exact_integer_value": None},
                    {"index": 2, "expression": "flags", "integer_literals": [], "is_exact_integer_literal": False, "exact_integer_value": None},
                ],
                "ghidra_direct_edge": True,
            },
            {
                "caller": "FUN_00110000",
                "wrapper": "FUN_00886930",
                "occurrence": 0,
                "source_statement": "FUN_00886930(ptr, mode, 4);",
                "arguments_parse_complete": True,
                "arguments": [
                    {"index": 0, "expression": "ptr", "integer_literals": [], "is_exact_integer_literal": False, "exact_integer_value": None},
                    {"index": 1, "expression": "mode", "integer_literals": [], "is_exact_integer_literal": False, "exact_integer_value": None},
                    {"index": 2, "expression": "4", "integer_literals": [4], "is_exact_integer_literal": True, "exact_integer_value": 4},
                ],
                "ghidra_direct_edge": True,
            },
        ],
    }


def _forwarding() -> dict:
    return {
        "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
        "wrappers": [
            {
                "name": "FUN_00886900",
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
                            {"storage": "ECX:4", "source": "input:Stack[0x4]:4", "source_kind": "input"},
                            {"storage": "EDX:4", "source": "input:Stack[0x8]:4", "source_kind": "input"},
                            {"storage": "Stack[0x4]:4", "source": "input:Stack[0xc]:4", "source_kind": "input"},
                        ],
                    },
                    {
                        "instruction": "0x0088691f",
                        "target": "0x006382b0",
                        "target_name": "FUN_006382b0",
                        "target_calling_convention": "__fastcall",
                        "arguments_resolved": True,
                        "incoming_state_uncertain": False,
                        "arguments": [
                            {"storage": "ECX:4", "source": "input:Stack[0x4]:4", "source_kind": "input"},
                            {"storage": "EDX:4", "source": "constant:0x4", "source_kind": "constant"},
                        ],
                    },
                ],
            },
            {
                "name": "FUN_00886930",
                "input_storage": ["ECX:4", "DL:1", "Stack[0x4]:4"],
                "forwarding_confirmed": True,
                "call_sites": [
                    {
                        "instruction": "0x0088693b",
                        "target": "0x0064f4c0",
                        "target_name": "thunk_FUN_0064f3a0",
                        "target_calling_convention": "__fastcall",
                        "arguments_resolved": True,
                        "incoming_state_uncertain": False,
                        "arguments": [
                            {"storage": "ECX:4", "source": "input:ECX:4", "source_kind": "input"},
                            {"storage": "DL:1", "source": "low8(input:DL:1)", "source_kind": "derived-input"},
                        ],
                    }
                ],
            },
        ],
    }


def _row(report, wrapper):
    return next(row for row in report["rows"] if row["wrapper"] == wrapper)


def test_projects_source_expressions_into_backend_physical_storage(tmp_path):
    module = _load_module()
    callsites = tmp_path / "callsites.json"
    forwarding = tmp_path / "forwarding.json"
    _write(callsites, _callsites())
    _write(forwarding, _forwarding())

    report = module.join_memory_wrapper_argument_provenance(callsites, forwarding)
    assert report["format"] == "SHIFT-MEMORY-WRAPPER-ARGUMENT-PROVENANCE/1"
    assert report["callsite_count"] == 2
    assert report["projection_complete_callsite_count"] == 2
    assert report["projection_incomplete_callsite_count"] == 0
    assert report["unresolved_backend_argument_count"] == 0
    assert report["all_callsites_projection_complete"] is True

    create = _row(report, "FUN_00886900")
    first = create["backend_calls"][0]
    assert [arg["projected_expression"] for arg in first["arguments"]] == [
        "source_arg[0](0x38)",
        "source_arg[1](pool_id)",
        "source_arg[2](flags)",
    ]
    fallback = create["backend_calls"][1]
    assert fallback["arguments"][1]["projected_expression"] == "constant:0x4"
    assert fallback["arguments"][1]["projection_kind"] == "wrapper-internal"

    release = _row(report, "FUN_00886930")
    args = release["backend_calls"][0]["arguments"]
    assert args[0]["projected_expression"] == "source_arg[0](ptr)"
    assert args[1]["projected_expression"] == "low8(source_arg[1](mode))"
    assert args[1]["source_argument_indices"] == [1]
    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_argument_count_mismatch_keeps_partial_projection_but_row_incomplete(tmp_path):
    module = _load_module()
    callsite_payload = _callsites()
    callsite_payload["callsites"] = [callsite_payload["callsites"][0]]
    callsite_payload["callsites"][0]["arguments"] = callsite_payload["callsites"][0]["arguments"][:2]
    callsites = tmp_path / "callsites.json"
    forwarding = tmp_path / "forwarding.json"
    _write(callsites, callsite_payload)
    _write(forwarding, _forwarding())

    report = module.join_memory_wrapper_argument_provenance(callsites, forwarding)
    row = report["rows"][0]
    assert row["projection_complete"] is False
    assert any("does not match wrapper input-storage count" in reason for reason in row["projection_reasons"])
    assert row["unresolved_backend_argument_count"] == 1
    first = row["backend_calls"][0]
    assert first["arguments"][0]["projection_resolved"] is True
    assert first["arguments"][2]["projection_resolved"] is False
    assert first["arguments"][2]["missing_input_storages"] == ["Stack[0xc]:4"]


def test_unconfirmed_forwarding_never_promotes_complete_projection(tmp_path):
    module = _load_module()
    callsite_payload = _callsites()
    callsite_payload["callsites"] = [callsite_payload["callsites"][1]]
    forwarding_payload = _forwarding()
    forwarding_payload["wrappers"] = [forwarding_payload["wrappers"][1]]
    forwarding_payload["wrappers"][0]["forwarding_confirmed"] = False
    callsites = tmp_path / "callsites.json"
    forwarding = tmp_path / "forwarding.json"
    _write(callsites, callsite_payload)
    _write(forwarding, forwarding_payload)

    report = module.join_memory_wrapper_argument_provenance(callsites, forwarding)
    row = report["rows"][0]
    assert row["forwarding_confirmed"] is False
    assert row["projection_complete"] is False
    assert "wrapper forwarding is not confirmed" in row["projection_reasons"]
    assert report["all_callsites_projection_complete"] is False


def test_missing_wrapper_forwarding_is_explicit(tmp_path):
    module = _load_module()
    callsite_payload = _callsites()
    callsite_payload["callsites"] = [callsite_payload["callsites"][0]]
    forwarding_payload = {"format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1", "wrappers": []}
    callsites = tmp_path / "callsites.json"
    forwarding = tmp_path / "forwarding.json"
    _write(callsites, callsite_payload)
    _write(forwarding, forwarding_payload)

    report = module.join_memory_wrapper_argument_provenance(callsites, forwarding)
    row = report["rows"][0]
    assert row["forwarding_wrapper_present"] is False
    assert row["backend_calls"] == []
    assert row["projection_complete"] is False
    assert row["projection_reasons"] == ["wrapper missing from forwarding report"]


def test_rejects_wrong_input_formats(tmp_path):
    module = _load_module()
    callsites = tmp_path / "callsites.json"
    forwarding = tmp_path / "forwarding.json"
    _write(callsites, {"format": "wrong"})
    _write(forwarding, _forwarding())

    try:
        module.join_memory_wrapper_argument_provenance(callsites, forwarding)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1" in str(exc)
    else:
        raise AssertionError("wrong callsite format must fail")
