from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_transform_sink_receiver_provenance.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_sink_receiver", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _varnode(text: str, *, register: bool = True) -> dict:
    return {
        "text": text,
        "space": "register" if register else "unique",
        "offset": "0x0",
        "size": 4,
        "constant": False,
        "register": register,
        "unique": not register,
    }


def _ins(
    address: str,
    mnemonic: str,
    operands: list[str],
    *,
    fallthrough: str | None = None,
    flows: list[str] | None = None,
    flow_type: str = "FALL_THROUGH",
    outputs: tuple[str, ...] = (),
) -> dict:
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {' '.join(operands)}".strip(),
        "operands": list(operands),
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else list(flows),
        "references": [],
        "pcode": [
            {
                "opcode": "COPY",
                "text": f"{register} = COPY unknown",
                "output": _varnode(register),
                "inputs": [],
            }
            for register in outputs
        ],
    }


def _call(address: str, target: str, fallthrough: str) -> dict:
    return _ins(
        address,
        "CALL",
        [target],
        fallthrough=fallthrough,
        flows=[target],
        flow_type="UNCONDITIONAL_CALL",
    )


def _ret(address: str) -> dict:
    return _ins(address, "RET", [], flow_type="TERMINATOR")


def _positive_instructions() -> list[dict]:
    return [
        _ins("0x007927c0", "MOV", ["ESI", "ECX"], fallthrough="0x007927f7", outputs=("ESI",)),
        _ins("0x007927f7", "MOV", ["ECX", "ESI"], fallthrough="0x007927fd", outputs=("ECX",)),
        _call("0x007927fd", "0x007af6e0", "0x00792808"),
        _ins("0x00792808", "MOV", ["ECX", "ESI"], fallthrough="0x0079280e", outputs=("ECX",)),
        _call("0x0079280e", "0x007876e0", "0x00792820"),
        _ins("0x00792820", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x00792828", outputs=("ECX",)),
        _call("0x00792828", "0x007afb60", "0x00792831"),
        _ins("0x00792831", "MOV", ["ECX", "ESI"], fallthrough="0x00792837", outputs=("ECX",)),
        _call("0x00792837", "0x004a7870", "0x0079287e"),
        _ins("0x0079287e", "MOV", ["ECX", "[ESI+0x24]"], fallthrough="0x00792884", outputs=("ECX",)),
        _call("0x00792884", "0x00787160", "0x007928dc"),
        _ins("0x007928dc", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x007928e3", outputs=("ECX",)),
        _call("0x007928e3", "0x007633b0", "0x007928ea"),
        _ins("0x007928ea", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x007928f0", outputs=("ECX",)),
        _call("0x007928f0", "0x007ac2f0", "0x007928f5"),
        _ret("0x007928f5"),
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _frontier(tmp_path: Path, *, preclaim: bool = False) -> Path:
    path = tmp_path / "frontier.json"
    path.write_text(
        json.dumps(
            {
                "format": MODULE.FRONTIER_FORMAT,
                "version": 1,
                "status": "frontier-ready",
                "ready": True,
                "retail": {
                    "outer_vehicle_setter_direct_calls": [
                        {"instruction": instruction, "callee": callee}
                        for instruction, callee in MODULE._frontier_builder.OUTER_SETTER_CALLS
                    ]
                },
                "handoff": {
                    "outer_vehicle_spawn_path_static_frontier_ready": True,
                    "outer_vehicle_transform_fanout_static_frontier_ready": True,
                    "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
                    "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
                },
                "scope": {
                    "callgraph_adjacency_used_as_frame_identity": False,
                    "outer_vehicle_root_equated_to_VHF_root": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _instruction_export(tmp_path: Path, instructions: list[dict]) -> Path:
    path = tmp_path / "outer.jsonl"
    _write_jsonl(
        path,
        [
            {
                "format": MODULE.INSTRUCTION_FORMAT,
                "program": "SHIFT.exe",
                "requested": MODULE.OUTER_SETTER,
                "found": True,
                "function": {
                    "address": MODULE.OUTER_SETTER,
                    "name": "FUN_007927c0",
                    "size": 340,
                    "calling_convention": "__thiscall",
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        ],
    )
    return path


def test_groups_deterministic_receiver_origins_without_promoting_identity(tmp_path):
    report = MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
        _frontier(tmp_path),
        _instruction_export(tmp_path, _positive_instructions()),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "receiver-frontier-ready"
    rows = {row["callee"]: row for row in report["sink_receiver_analyses"]}

    assert rows["0x007876e0"]["ECX_origins_before_call"] == ["entry:ECX"]
    assert rows["0x007876e0"]["ECX_origin_classification"] == "exact-outer-setter-entry-ECX"
    assert rows["0x007afb60"]["ECX_origins_before_call"] == ["memory:[esi+0x20]"]
    assert rows["0x007633b0"]["ECX_origins_before_call"] == ["memory:[esi+0x20]"]
    assert rows["0x007ac2f0"]["ECX_origins_before_call"] == ["memory:[esi+0x20]"]
    assert rows["0x00787160"]["ECX_origins_before_call"] == ["memory:[esi+0x24]"]

    assert rows["0x007afb60"]["same_ECX_origin_expression_set_as_HDVehicle_sink"] is True
    assert rows["0x007ac2f0"]["same_ECX_origin_expression_set_as_HDVehicle_sink"] is True
    assert rows["0x007876e0"]["same_ECX_origin_expression_set_as_HDVehicle_sink"] is False
    assert all(row["same_ECX_origin_expression_is_pointer_equality"] is False for row in rows.values())
    assert all(row["same_ECX_origin_expression_is_frame_identity"] is False for row in rows.values())

    assert len(report["next_owner_candidates"]) == 3
    assert report["fastcall_ECX_candidate"]["callee"] == "0x00787160"
    assert report["handoff"]["outer_setter_sink_ECX_provenance_unambiguous"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["matching_origin_expression_promoted_to_pointer_equality"] is False
    assert report["scope"]["fastcall_ECX_promoted_to_this_receiver"] is False


def test_divergent_reachable_paths_keep_sink_receiver_ambiguous(tmp_path):
    instructions = [
        _ins("0x007927c0", "MOV", ["ESI", "ECX"], fallthrough="0x007927c2", outputs=("ESI",)),
        _ins(
            "0x007927c2",
            "JNZ",
            ["0x00792808"],
            fallthrough="0x007927c4",
            flows=["0x00792808"],
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins("0x007927c4", "MOV", ["ECX", "ESI"], fallthrough="0x007927c6", outputs=("ECX",)),
        _ins(
            "0x007927c6",
            "JMP",
            ["0x0079280e"],
            flows=["0x0079280e"],
            flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins("0x00792808", "MOV", ["ECX", "EDI"], fallthrough="0x0079280e", outputs=("ECX",)),
        _call("0x0079280e", "0x007876e0", "0x00792820"),
        _ins("0x00792820", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x00792828", outputs=("ECX",)),
        _call("0x00792828", "0x007afb60", "0x0079287e"),
        _ins("0x0079287e", "MOV", ["ECX", "[ESI+0x24]"], fallthrough="0x00792884", outputs=("ECX",)),
        _call("0x00792884", "0x00787160", "0x007928dc"),
        _ins("0x007928dc", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x007928e3", outputs=("ECX",)),
        _call("0x007928e3", "0x007633b0", "0x007928ea"),
        _ins("0x007928ea", "MOV", ["ECX", "[ESI+0x20]"], fallthrough="0x007928f0", outputs=("ECX",)),
        _call("0x007928f0", "0x007ac2f0", "0x007928f5"),
        _ret("0x007928f5"),
    ]
    report = MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
        _frontier(tmp_path), _instruction_export(tmp_path, instructions)
    )
    first = next(row for row in report["sink_receiver_analyses"] if row["callee"] == "0x007876e0")
    assert first["ECX_origins_before_call"] == ["entry:ECX", "entry:EDI"]
    assert first["ECX_origin_deterministic"] is False
    assert report["status"] == "receiver-frontier-ambiguous"
    assert report["handoff"]["outer_setter_sink_ECX_provenance_unambiguous"] is False
    assert report["blockers"][0]["id"] == "outer-setter-sink-ECX-origin-ambiguity"


def test_wrong_direct_target_fails_closed(tmp_path):
    instructions = _positive_instructions()
    index = next(i for i, row in enumerate(instructions) if row["address"] == "0x00792828")
    instructions[index] = _call("0x00792828", "0x007afb70", "0x00792831")
    with pytest.raises(ValueError, match="expected direct target 0x007afb60"):
        MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
            _frontier(tmp_path), _instruction_export(tmp_path, instructions)
        )


def test_missing_outer_setter_instruction_row_fails_closed(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="instruction export missing required function"):
        MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
            _frontier(tmp_path), path
        )


def test_frontier_preclaim_of_vhf_root_identity_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims outer Vehicle/VHF root identity"):
        MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
            _frontier(tmp_path, preclaim=True),
            _instruction_export(tmp_path, _positive_instructions()),
        )


def test_frontier_fanout_drift_is_rejected(tmp_path):
    value = json.loads(_frontier(tmp_path).read_text(encoding="utf-8"))
    value["retail"]["outer_vehicle_setter_direct_calls"].pop()
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="fan-out drift"):
        MODULE.analyze_outer_vehicle_transform_sink_receiver_provenance(
            path, _instruction_export(tmp_path, _positive_instructions())
        )
