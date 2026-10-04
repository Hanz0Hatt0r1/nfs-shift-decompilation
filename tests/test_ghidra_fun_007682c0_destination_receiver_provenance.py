from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_fun_007682c0_destination_receiver_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_fun_007682c0_destination_receiver_provenance_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _varnode(text: str, *, register: bool = True):
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
):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {','.join(operands)}".strip(),
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


def _row(address: str, name: str, instructions: list[dict], *, convention: str):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": len(instructions),
            "calling_convention": convention,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _retail_export(tmp_path: Path, module, *, fingerprint_drift: bool = False) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({
            "program_name": module.PROGRAM,
            "executable_md5": module.PE_MD5,
        }),
        encoding="utf-8",
    )

    rows = []
    for address, expected in module.TARGETS.items():
        digest = expected["mnemonic_sha256"]
        if fingerprint_drift and address == "0x0076d100":
            digest = "0" * 64
        rows.append({
            "address": address,
            "name": expected["name"],
            "size": 32,
            "thunk": False,
            "external": False,
            "calling_convention": expected["calling_convention"],
            "signature": "undefined test(void)",
            "parameters": [],
            "mnemonic_sha256": digest,
        })
    _write_jsonl(root / "functions.jsonl", rows)
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": row["caller"],
                "from_name": module.TARGETS[row["caller"]]["name"],
                "instruction": row["callsite"],
                "to": row["callee"],
                "to_name": module.TARGETS[row["callee"]]["name"],
                "indirect": False,
            }
            for row in module.CALLS
        ],
    )
    return root


def _global_identity(tmp_path: Path, module, *, ready: bool = True) -> Path:
    path = tmp_path / "global_identity.json"
    value = {
        "format": module.GLOBAL_IDENTITY_FORMAT,
        "identity_join": {
            "global_vehicle_address": module.GLOBAL_VEHICLE_ADDRESS,
            "global_vehicle_component_base_identity_ready": True,
            "BODY_array_owner_pointer_loaded_from_global_vehicle_base": True,
            "BODY_array_owner_is_global_vehicle_base": False,
            "BODY_array_owner_pointer_field_offset": module.BODY_OWNER_FIELD_OFFSET,
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_name": module.BMW_CHASSIS_BODY_NAME,
            "main_chassis_BODY_index": module.BMW_CHASSIS_BODY_INDEX,
            "global_vehicle_BODY_owner_identity_ready": ready,
        },
        "handoff": {
            "vehicle_BODY_selection_ready": ready,
            "selected_BODY_index": module.BMW_CHASSIS_BODY_INDEX,
            "phase700_runtime_handoff_admissible": ready,
        },
        "blockers": [] if ready else ["not-ready"],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _outer_direct(module):
    return [
        _ins(
            "0x00770e80", "MOV", ["ESI", "ECX"],
            fallthrough="0x00770e82", outputs=("ESI",),
        ),
        _ins(
            "0x00770e82", "MOV", ["ECX", "ESI"],
            fallthrough="0x00770f8f", outputs=("ECX",),
        ),
        _ins(
            "0x00770f8f", "CALL", ["0x0076d100"],
            fallthrough="0x00770f94", flows=["0x0076d100"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x00770f94", "MOV", ["ECX", "ESI"],
            fallthrough="0x00770fbf", outputs=("ECX",),
        ),
        _ins(
            "0x00770fbf", "CALL", ["0x0076d100"],
            fallthrough="0x00770fc4", flows=["0x0076d100"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x00770fc4", "RET", [], flow_type="TERMINATOR"),
    ]


def _outer_owner_field(module):
    return [
        _ins(
            "0x00770e80", "MOV", ["ESI", "ECX"],
            fallthrough="0x00770e82", outputs=("ESI",),
        ),
        _ins(
            "0x00770e82", "MOV", ["ECX", "[ESI+0x339c]"],
            fallthrough="0x00770f8f", outputs=("ECX",),
        ),
        _ins(
            "0x00770f8f", "CALL", ["0x0076d100"],
            fallthrough="0x00770f94", flows=["0x0076d100"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x00770f94", "MOV", ["ECX", "[ESI+0x339c]"],
            fallthrough="0x00770fbf", outputs=("ECX",),
        ),
        _ins(
            "0x00770fbf", "CALL", ["0x0076d100"],
            fallthrough="0x00770fc4", flows=["0x0076d100"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x00770fc4", "RET", [], flow_type="TERMINATOR"),
    ]


def _physics_pass(module):
    return [
        _ins(
            "0x0076d100", "MOV", ["ESI", "ECX"],
            fallthrough="0x0076d102", outputs=("ESI",),
        ),
        _ins(
            "0x0076d102", "CALL", ["0x00700000"],
            fallthrough="0x0076d2bc", flows=["0x00700000"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x0076d2bc", "MOV", ["ECX", "ESI"],
            fallthrough="0x0076d2c1", outputs=("ECX",),
        ),
        _ins(
            "0x0076d2c1", "CALL", ["0x00769ef0"],
            fallthrough="0x0076d2c6", flows=["0x00769ef0"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076d2c6", "RET", [], flow_type="TERMINATOR"),
    ]


def _tail(module):
    return [
        _ins(
            "0x00769ef0", "MOV", ["ESI", "ECX"],
            fallthrough="0x00769ef2", outputs=("ESI",),
        ),
        _ins(
            "0x00769ef2", "CALL", ["0x00700010"],
            fallthrough="0x0076a1e3", flows=["0x00700010"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x0076a1e3", "MOV", ["ECX", "ESI"],
            fallthrough="0x0076a1e8", outputs=("ECX",),
        ),
        _ins(
            "0x0076a1e8", "CALL", ["0x007682c0"],
            fallthrough="0x0076a1ed", flows=["0x007682c0"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076a1ed", "RET", [], flow_type="TERMINATOR"),
    ]


def _instruction_export(tmp_path: Path, module, *, outer=None, physics=None, tail=None) -> Path:
    path = tmp_path / "targeted.jsonl"
    _write_jsonl(
        path,
        [
            _row(
                "0x00770e80", "FUN_00770e80",
                _outer_direct(module) if outer is None else outer,
                convention="__thiscall",
            ),
            _row(
                "0x0076d100", "FUN_0076d100",
                _physics_pass(module) if physics is None else physics,
                convention="__thiscall",
            ),
            _row(
                "0x00769ef0", "FUN_00769ef0",
                _tail(module) if tail is None else tail,
                convention="__fastcall",
            ),
        ],
    )
    return path


def test_direct_global_receiver_chain_stays_semantically_blocked(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    instructions = _instruction_export(tmp_path, module)
    identity = _global_identity(tmp_path, module)

    report = module.analyze_fun_007682c0_destination_receiver_provenance(
        root, instructions, identity
    )

    assert report["format"] == module.FORMAT
    assert report["ready"] is True
    assert report["status"] == "receiver-provenance-ready-semantic-join-blocked"
    assert report["analysis"]["receiver_provenance_ready"] is True
    assert report["analysis"]["both_physics_pass_receivers_same_origin"] is True
    assert report["analysis"]["outer_entry_relative_FUN_007682c0_receiver_origins"] == [
        "entry:ECX"
    ]
    assert report["analysis"]["direct_global_vehicle_receiver_chain_observed"] is True
    assert report["analysis"]["receiver_to_retail_BMW_chassis_BODY0_join_proven"] is False
    assert report["handoff"]["FUN_007682c0_delta_consumer_internalization_ready"] is False
    assert report["handoff"]["phase696_typed_delta_consumer_must_remain_external"] is True
    assert report["blocking_reasons"][-1]["id"] == (
        "fun-007682c0-receiver-to-retail-BODY0-semantic-join-unproven"
    )


def test_owner_field_displacement_is_candidate_not_body0_proof(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    instructions = _instruction_export(tmp_path, module, outer=_outer_owner_field(module))
    identity = _global_identity(tmp_path, module)

    report = module.analyze_fun_007682c0_destination_receiver_provenance(
        root, instructions, identity
    )

    assert report["ready"] is True
    assert report["analysis"]["outer_entry_relative_FUN_007682c0_receiver_origins"] == [
        "memory:[esi+0x339c]"
    ]
    assert report["analysis"]["owner_field_displacement_candidate_observed"] is True
    assert report["analysis"]["receiver_to_retail_BMW_chassis_BODY0_join_proven"] is False
    blocker = report["blocking_reasons"][-1]
    assert blocker["owner_field_displacement_candidate_observed"] is True
    assert "base register" in blocker["required_evidence"]
    assert report["scope"]["memory_displacement_match_used_as_BODY_identity"] is False


def test_different_pass_receivers_are_reported_without_guessing_owner(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    outer = _outer_direct(module)
    outer[3] = _ins(
        "0x00770f94", "MOV", ["ECX", "[ESI+0x339c]"],
        fallthrough="0x00770fbf", outputs=("ECX",),
    )
    instructions = _instruction_export(tmp_path, module, outer=outer)
    identity = _global_identity(tmp_path, module)

    report = module.analyze_fun_007682c0_destination_receiver_provenance(
        root, instructions, identity
    )

    assert report["ready"] is True
    assert report["analysis"]["both_physics_pass_receivers_same_origin"] is False
    assert report["analysis"]["outer_entry_relative_FUN_007682c0_receiver_origins"] is None
    assert any(
        blocker["id"] == "physics-pass-receivers-differ"
        for blocker in report["blocking_reasons"]
    )
    assert report["handoff"]["FUN_007682c0_delta_consumer_internalization_ready"] is False


def test_derived_tail_receiver_keeps_cross_function_chain_uncomposed(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    physics = _physics_pass(module)
    physics[2] = _ins(
        "0x0076d2bc", "MOV", ["ECX", "[ESI+0x20]"],
        fallthrough="0x0076d2c1", outputs=("ECX",),
    )
    instructions = _instruction_export(tmp_path, module, physics=physics)
    identity = _global_identity(tmp_path, module)

    report = module.analyze_fun_007682c0_destination_receiver_provenance(
        root, instructions, identity
    )

    assert report["ready"] is True
    assert report["analysis"]["physics_pass_to_tail_entry_ECX_continuity_proven"] is False
    assert report["analysis"]["outer_entry_relative_FUN_007682c0_receiver_origins"] is None
    assert any(
        blocker["id"] == "pass-receiver-to-fun-007682c0-entry-continuity-unproven"
        for blocker in report["blocking_reasons"]
    )


def test_rejects_wrong_direct_call_target(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    tail = _tail(module)
    tail[3] = _ins(
        "0x0076a1e8", "CALL", ["0x007682d0"],
        fallthrough="0x0076a1ed", flows=["0x007682d0"],
        flow_type="UNCONDITIONAL_CALL",
    )
    instructions = _instruction_export(tmp_path, module, tail=tail)
    identity = _global_identity(tmp_path, module)

    with pytest.raises(ValueError, match="expected direct target 0x007682c0"):
        module.analyze_fun_007682c0_destination_receiver_provenance(
            root, instructions, identity
        )


def test_rejects_retail_mnemonic_fingerprint_drift(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module, fingerprint_drift=True)
    instructions = _instruction_export(tmp_path, module)
    identity = _global_identity(tmp_path, module)

    with pytest.raises(ValueError, match="0x0076d100: mnemonic fingerprint drift"):
        module.analyze_fun_007682c0_destination_receiver_provenance(
            root, instructions, identity
        )


def test_rejects_nonpositive_global_body_owner_identity(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    instructions = _instruction_export(tmp_path, module)
    identity = _global_identity(tmp_path, module, ready=False)

    with pytest.raises(ValueError, match="global BODY-owner identity has blockers"):
        module.analyze_fun_007682c0_destination_receiver_provenance(
            root, instructions, identity
        )
