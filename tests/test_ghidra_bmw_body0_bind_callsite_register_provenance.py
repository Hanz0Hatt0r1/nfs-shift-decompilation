import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_bmw_body0_bind_callsite_register_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_bmw_body0_bind_callsite_register_provenance", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _instruction(
    address,
    mnemonic,
    operands,
    *,
    flows=None,
    fallthrough=None,
    flow_type="FALL_THROUGH",
    pcode=None,
):
    text = mnemonic + (" " + ", ".join(operands) if operands else "")
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands,
        "flows": [] if flows is None else flows,
        "fallthrough": fallthrough,
        "flow_type": flow_type,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _row(address, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _frontier(module, callers):
    return {
        "format": module.FRONTIER_FORMAT,
        "pose_writer_candidate": {
            "function": module.POSE_WRITER,
            "direct_caller_count": len(callers),
            "direct_callers": callers,
            "bind_initializer_semantics_proven": False,
        },
        "targeted_proof_worklist": {
            "function_targets": sorted(
                {row["caller"] for row in callers} | {module.POSE_WRITER},
                key=lambda value: int(value, 0),
            )
        },
        "scope": {
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
        },
    }


def _caller(caller, callsite, candidate_class):
    return {
        "caller": caller,
        "caller_name": "FUN_" + caller[2:],
        "callsite": callsite,
        "candidate_class": candidate_class,
        "from_BODY_builder": {"reachable": candidate_class.startswith("builder-")},
        "from_SDF_loader": {"reachable": False},
        "bind_initializer_semantics_proven": False,
        "BODY0_pointer_proven": False,
        "origin_basis_value_provenance_proven": False,
    }


def _write(path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _fixture(tmp_path):
    module = _load_module()
    caller_a = "0x00700000"
    call_a = "0x00700009"
    caller_b = "0x00710000"
    call_b = "0x00710002"
    frontier = _frontier(
        module,
        [
            _caller(caller_a, call_a, "builder-reachable-pose-writer-caller"),
            _caller(caller_b, call_b, "unjoined-direct-pose-writer-caller"),
        ],
    )
    frontier_path = _write(tmp_path / "frontier.json", frontier)

    row_a = _row(
        caller_a,
        [
            _instruction(
                caller_a,
                "MOV",
                ["ESI", "ECX"],
                fallthrough="0x00700002",
            ),
            _instruction(
                "0x00700002",
                "CALL",
                ["0x00600000"],
                flows=["0x00600000"],
                fallthrough="0x00700007",
                flow_type="UNCONDITIONAL_CALL",
            ),
            _instruction(
                "0x00700007",
                "MOV",
                ["ECX", "ESI"],
                fallthrough=call_a,
            ),
            _instruction(
                call_a,
                "CALL",
                [module.POSE_WRITER],
                flows=[module.POSE_WRITER],
                fallthrough="0x0070000e",
                flow_type="UNCONDITIONAL_CALL",
            ),
            _instruction(
                "0x0070000e",
                "RET",
                [],
                fallthrough=None,
                flow_type="TERMINATOR",
            ),
        ],
    )
    row_b = _row(
        caller_b,
        [
            _instruction(
                caller_b,
                "MOV",
                ["ECX", "dword ptr [EAX + 0x10]"],
                fallthrough=call_b,
            ),
            _instruction(
                call_b,
                "CALL",
                [module.POSE_WRITER],
                flows=[module.POSE_WRITER],
                fallthrough="0x00710007",
                flow_type="UNCONDITIONAL_CALL",
            ),
            _instruction(
                "0x00710007",
                "RET",
                [],
                fallthrough=None,
                flow_type="TERMINATOR",
            ),
        ],
    )
    instruction_path = _write_rows(tmp_path / "instructions.jsonl", [row_a, row_b])
    return module, frontier_path, instruction_path, caller_a, call_a, caller_b, call_b


def test_traces_all_path_register_origins_at_exact_pose_writer_callsites(tmp_path):
    module, frontier_path, instruction_path, caller_a, call_a, caller_b, call_b = _fixture(tmp_path)

    report = module.analyze_bmw_body0_bind_callsite_register_provenance(
        frontier_path, instruction_path
    )

    assert report["format"] == "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1"
    assert report["target"]["direct_caller_count"] == 2
    assert report["analysis"]["analyzed_callsite_count"] == 2
    assert report["analysis"]["all_frontier_callsites_analyzed"] is True
    by_callsite = {
        row["callsite"]: row for row in report["analysis"]["callsites"]
    }

    first = by_callsite[call_a]
    assert first["caller"] == caller_a
    assert first["registers_before_call"]["ECX"]["origins"] == ["entry:ECX"]
    assert first["registers_before_call"]["ESI"]["origins"] == ["entry:ECX"]
    assert first["registers_before_call"]["EAX"]["contains_unknown_or_derived"] is True
    assert first["exact_entry_register_aliases"]["ECX"] == "ECX"
    assert first["exact_entry_register_aliases"]["ESI"] == "ECX"
    assert first["physical_register_provenance_ready"] is True
    assert first["BODY0_pointer_proven"] is False
    assert first["bind_initializer_semantics_proven"] is False
    assert first["lexical_window_is_path_proof"] is False
    assert first["lexical_pre_call_window"][-1]["address"] == call_a

    second = by_callsite[call_b]
    assert second["caller"] == caller_b
    assert second["registers_before_call"]["ECX"]["origins"] == [
        "memory:dword ptr [eax + 0x10]"
    ]
    assert second["registers_before_call"]["ECX"]["exact_single_origin"] is True
    assert second["registers_before_call"]["ECX"]["contains_memory_origin"] is True
    assert second["BODY_pointer_register_proven"] is False

    blocker_ids = {row["id"] for row in report["blockers"]}
    assert blocker_ids == {
        "pose-writer-physical-ABI-semantic-binding-unproven",
        "BODY0-pointer-at-bind-callsite-unproven",
        "bind-origin-basis-value-provenance-unproven",
        "stack-argument-value-provenance-unmodeled",
    }
    assert report["handoff"]["pose_writer_callsite_register_provenance_ready"] is True
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["register_engine_reused_from_FUN_00765470_proof"] is True


def test_caller_saved_ecx_stays_unknown_without_restore(tmp_path):
    module, frontier_path, instruction_path, caller_a, call_a, *_ = _fixture(tmp_path)
    rows = module._read_rows(instruction_path)
    row_a = rows[0]
    row_a["instructions"] = [
        _instruction(
            caller_a,
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough=call_a,
            flow_type="UNCONDITIONAL_CALL",
        ),
        _instruction(
            call_a,
            "CALL",
            [module.POSE_WRITER],
            flows=[module.POSE_WRITER],
            fallthrough="0x0070000e",
            flow_type="UNCONDITIONAL_CALL",
        ),
        _instruction(
            "0x0070000e",
            "RET",
            [],
            flow_type="TERMINATOR",
        ),
    ]
    row_a["instruction_count"] = len(row_a["instructions"])
    _write_rows(instruction_path, rows)

    report = module.analyze_bmw_body0_bind_callsite_register_provenance(
        frontier_path, instruction_path
    )
    first = next(
        row for row in report["analysis"]["callsites"] if row["callsite"] == call_a
    )
    assert first["registers_before_call"]["ECX"]["origins"] == [
        "unknown:ECX@0x00700000:call-clobber"
    ]
    assert "ECX" in first["unresolved_or_ambiguous_registers"]


def test_missing_required_caller_instruction_row_is_rejected(tmp_path):
    module, frontier_path, instruction_path, *_ = _fixture(tmp_path)
    rows = module._read_rows(instruction_path)
    _write_rows(instruction_path, rows[:1])

    with pytest.raises(ValueError, match="missing required pose-writer caller"):
        module.analyze_bmw_body0_bind_callsite_register_provenance(
            frontier_path, instruction_path
        )


def test_wrong_target_at_frontier_callsite_is_rejected(tmp_path):
    module, frontier_path, instruction_path, _, call_a, *_ = _fixture(tmp_path)
    rows = module._read_rows(instruction_path)
    for instruction in rows[0]["instructions"]:
        if instruction["address"] == call_a:
            instruction["operands"] = ["0x007b0000"]
            instruction["flows"] = ["0x007b0000"]
    _write_rows(instruction_path, rows)

    with pytest.raises(ValueError, match="expected direct target"):
        module.analyze_bmw_body0_bind_callsite_register_provenance(
            frontier_path, instruction_path
        )


def test_duplicate_instruction_rows_are_rejected(tmp_path):
    module, frontier_path, instruction_path, *_ = _fixture(tmp_path)
    rows = module._read_rows(instruction_path)
    _write_rows(instruction_path, rows + [rows[0]])

    with pytest.raises(ValueError, match="duplicate instruction row"):
        module.analyze_bmw_body0_bind_callsite_register_provenance(
            frontier_path, instruction_path
        )


def test_empty_frontier_caller_set_remains_blocked(tmp_path):
    module = _load_module()
    frontier_path = _write(tmp_path / "frontier.json", _frontier(module, []))
    instruction_path = _write_rows(tmp_path / "instructions.jsonl", [])

    report = module.analyze_bmw_body0_bind_callsite_register_provenance(
        frontier_path, instruction_path
    )

    assert report["analysis"]["analyzed_callsite_count"] == 0
    assert report["handoff"]["pose_writer_callsite_register_provenance_ready"] is False
    assert {row["id"] for row in report["blockers"]} == {
        "pose-writer-direct-caller-set-empty"
    }


def test_frontier_semantic_preclaim_is_rejected(tmp_path):
    module, frontier_path, instruction_path, *_ = _fixture(tmp_path)
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    frontier["pose_writer_candidate"]["bind_initializer_semantics_proven"] = True
    _write(frontier_path, frontier)

    with pytest.raises(ValueError, match="preclaims bind initializer semantics"):
        module.analyze_bmw_body0_bind_callsite_register_provenance(
            frontier_path, instruction_path
        )
