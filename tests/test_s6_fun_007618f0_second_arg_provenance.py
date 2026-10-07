from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools/ghidra/build_fun_007618f0_second_arg_worklist.py"
ANALYZER_PATH = ROOT / "tools/ghidra/analyze_fun_007618f0_second_arg_provenance.py"
OWNERSHIP = ROOT / "evidence/fun_007618f0_vehicle_load_data_ownership.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load(BUILDER_PATH, "phase738_builder")
analyzer = _load(ANALYZER_PATH, "phase738_analyzer")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _insn(address: str, mnemonic: str, operands: list[str], *, fallthrough: str | None, flows: list[str] | None = None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
        "flows": [] if flows is None else flows,
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": fallthrough,
        "pcode": [],
    }


def _worklist(caller: str = "0x00100000", callsite: str = "0x0010000d") -> dict:
    return {
        "format": analyzer.WORKLIST_FORMAT,
        "target": analyzer.TARGET,
        "direct_calls": [
            {
                "caller": caller,
                "caller_name": "FUN_00100000",
                "callsite": callsite,
                "target": analyzer.TARGET,
            }
        ],
    }


def test_worklist_builder_selects_only_direct_callers(tmp_path: Path) -> None:
    (tmp_path / "binary.json").write_text(
        json.dumps({"program_name": builder.PROGRAM, "executable_md5": builder.PE_MD5}),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            {"address": builder.TARGET, "name": builder.TARGET_NAME},
            {"address": "0x00100000", "name": "FUN_00100000"},
            {"address": "0x00200000", "name": "FUN_00200000"},
        ],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x00100000",
                "from_name": "FUN_00100000",
                "instruction": "0x0010000d",
                "to": builder.TARGET,
                "to_name": builder.TARGET_NAME,
                "indirect": False,
            },
            {
                "from_function": "0x00200000",
                "instruction": "0x00200010",
                "to": builder.TARGET,
                "indirect": True,
            },
        ],
    )
    report = builder.build_worklist(tmp_path)
    assert report["ready"] is True
    assert report["direct_call_count"] == 1
    assert report["direct_caller_count"] == 1
    assert report["instruction_export_targets"] == ["0x00100000"]
    assert report["semantic_owner_claimed"] is False


def test_analyzer_models_retail_two_push_order() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "MOV", ["ESI", "ECX"], fallthrough="0x00100002"),
        _insn("0x00100002", "MOV", ["EAX", "[ESI+0x66b4]"], fallthrough="0x00100008"),
        _insn("0x00100008", "PUSH", ["EAX"], fallthrough="0x00100009"),
        _insn("0x00100009", "PUSH", ["EBX"], fallthrough="0x0010000a"),
        _insn("0x0010000a", "MOV", ["ECX", "ESI"], fallthrough="0x0010000d"),
        _insn("0x0010000d", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["explicit_argument_push_count"] == 2
    assert call["param_1"]["push"] == "0x00100009"
    assert call["param_1"]["operand"] == "EBX"
    assert call["param_2"]["push"] == "0x00100008"
    assert call["param_2"]["origins"] == ["memory:[esi+0x66b4]"]
    assert call["param_2"]["flags"]["exact_single_physical_origin"] is True
    assert report["all_callsites_two_argument_pushes_ready"] is True
    assert report["all_callsites_arguments_physically_resolved"] is True
    assert report["semantic_owner_claimed"] is False


def test_analyzer_allows_receiver_move_between_pushes_and_call() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["EDX"], fallthrough="0x00100001"),
        _insn("0x00100001", "PUSH", ["EBX"], fallthrough="0x00100002"),
        _insn("0x00100002", "MOV", ["ECX", "ESI"], fallthrough="0x0010000d"),
        _insn("0x0010000d", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["param_1"]["origins"] == ["entry:EBX"]
    assert call["param_2"]["origins"] == ["entry:EDX"]


def test_analyzer_fails_closed_when_only_one_argument_push_exists() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["ESI"], fallthrough="0x00100002"),
        _insn("0x00100002", "MOV", ["ECX", "ESI"], fallthrough="0x0010000d"),
        _insn("0x0010000d", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["explicit_argument_push_count"] == 1
    assert call["param_1"] is not None
    assert call["param_2"] is None
    assert report["all_callsites_arguments_physically_resolved"] is False
    assert report["ready_for_source_owner_crosscheck"] is False


def test_analyzer_stops_at_previous_call() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["EDX"], fallthrough="0x00100001"),
        _insn("0x00100001", "CALL", ["0x00760000"], fallthrough="0x00100006", flows=["0x00760000"]),
        _insn("0x00100006", "PUSH", ["EBX"], fallthrough="0x0010000d"),
        _insn("0x0010000d", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    assert report["callsites"][0]["param_2"] is None


def test_analyzer_rejects_callsite_target_drift() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["EDX"], fallthrough="0x00100001"),
        _insn("0x00100001", "PUSH", ["EBX"], fallthrough="0x0010000d"),
        _insn("0x0010000d", "CALL", ["0x00760000"], fallthrough=None, flows=["0x00760000"]),
    ]
    try:
        analyzer.analyze(_worklist(), {caller: instructions})
    except ValueError as exc:
        assert "no longer targets" in str(exc)
    else:
        raise AssertionError("target drift must fail closed")


def test_positive_source_machine_owner_evidence() -> None:
    payload = json.loads(OWNERSHIP.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007618f0VehicleLoadDataOwnership/1"
    assert payload["source_owner"]["HDVehicle_pointer_offset"] == "0x66b4"
    assert payload["source_owner"]["allocation_size"] == "0x3848"
    assert payload["source_owner"]["allocation_failure_text"] == "Failed to allocate a vehicle load data buffer"
    assert payload["callsite"]["address"] == "0x0076e27f"
    assert payload["callsite"]["param_2"] == "*(HDVehicle+0x66b4)"
    assert payload["consumer_fields"]["derived_cg_height"] == "VehicleLoadData+0x338"
    assert payload["consumer_fields"]["front_wing_center"] == [
        "VehicleLoadData+0x918",
        "VehicleLoadData+0x920",
        "VehicleLoadData+0x928",
    ]
    assert payload["consumer_fields"]["front_wing_center_parser_property"] == "FWCenter"
    assert payload["scope"]["VehicleLoadData_owner_proven"] is True
    assert payload["scope"]["selected_BMW_FWCenter_numeric_value_proven"] is False
    assert payload["provider_frontier"]["external_provider_count_after"] == 7
