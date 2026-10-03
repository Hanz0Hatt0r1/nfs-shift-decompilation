from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_global_vehicle_body_owner_continuity.py"


def _module():
    spec = importlib.util.spec_from_file_location("global_vehicle_body_owner_continuity", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _source(*, body_owner_arg: str = "this") -> str:
    return f"""
void __thiscall FUN_00770e80(void *this,double a,double b,char mode)
{{
  FUN_0076d100(this,mode);
  FUN_00765470(this,0.5,(double *)0);
  FUN_007b8810(this);
  FUN_0076d100(this,mode);
  FUN_00765470(this,0.5,(double *)0);
  FUN_007b8810(this);
}}

void __thiscall FUN_00765470(void *this,double param_1,double *param_2)
{{
  FUN_00763570(this,param_1);
  FUN_007b3f40(this,param_1);
  FUN_007b4110(this,param_1);
  FUN_007b2270({body_owner_arg},param_1);
}}
"""


def _function(address: str, name: str, cc: str = "__thiscall") -> dict:
    return {"address": address, "name": name, "calling_convention": cc}


def _call(address: str, target: str) -> dict:
    return {
        "address": address,
        "mnemonic": "CALL",
        "operands": [target],
        "text": f"CALL {target}",
        "flows": [target],
        "pcode": [{"opcode": "CALL", "text": f"CALL {target}"}],
    }


def _mov(address: str, dst: str, src: str) -> dict:
    return {
        "address": address,
        "mnemonic": "MOV",
        "operands": [dst, src],
        "text": f"MOV {dst},{src}",
        "flows": [],
        "pcode": [{"opcode": "COPY", "text": f"{dst} = {src}"}],
    }


def _fixture(tmp_path: Path, *, body_owner_arg: str = "this", clobber_receiver: bool = False):
    m = _module()
    source_text = _source(body_owner_arg=body_owner_arg)
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(source_text, encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

    global_identity = _write_json(
        tmp_path / "global.json",
        {
            "format": m.GLOBAL_FORMAT,
            "identity_join": {
                "global_outer_receiver_is_vehicle_component_base": True,
                "same_numeric_address": True,
                "outer_update_receiver_address": "0x00c13700",
            },
            "handoff": {
                "global_vehicle_component_base_identity_ready": True,
                "outer_receiver_to_BODY_owner_continuity_proven": False,
            },
        },
    )
    chassis = _write_json(
        tmp_path / "chassis.json",
        {
            "format": m.CHASSIS_FORMAT,
            "selection": {
                "main_chassis_BODY_selected": True,
                "selected_BODY_index": 0,
            },
            "handoff": {"vehicle_BODY_selection_ready": False},
        },
    )
    body = _write_json(
        tmp_path / "body.json",
        {
            "format": m.BODY_FORMAT,
            "source": {
                "executable_md5": m.PE_MD5,
                "decompile_sha256": m.SOURCE_SHA256,
            },
            "functions": {
                "FUN_00765470": {"address": m.HALF_STEP},
                "FUN_007b2270": {
                    "address": m.BODY_ARRAY_LOOP,
                    "body_count_offset": "0x10",
                    "body_array_offset": "0x14",
                    "body_stride": "0x170",
                },
            },
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_json(ghidra / "binary.json", {"executable_md5": m.PE_MD5})
    functions = [
        _function(m.OUTER_UPDATE, "FUN_00770e80"),
        _function(m.HALF_STEP, "FUN_00765470"),
        _function("0x00763570", "FUN_00763570"),
        _function("0x007b3f40", "FUN_007b3f40"),
        _function("0x007b4110", "FUN_007b4110"),
        _function(m.BODY_ARRAY_LOOP, "FUN_007b2270"),
    ]
    _write_jsonl(ghidra / "functions.jsonl", functions)
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {"from_function": m.OUTER_UPDATE, "to": m.HALF_STEP, "instruction": "0x00770fac", "indirect": False},
            {"from_function": m.OUTER_UPDATE, "to": m.HALF_STEP, "instruction": "0x00770fdc", "indirect": False},
            {"from_function": m.HALF_STEP, "to": m.BODY_ARRAY_LOOP, "instruction": m.HALF_STEP_BODY_CALL, "indirect": False},
        ],
    )

    instructions = [
        _mov("0x00765480", "ESI", "ECX"),
        _call("0x007657b2", "0x00763570"),
        _call("0x007657bd", "0x007b3f40"),
        _call("0x007657c8", "0x007b4110"),
    ]
    if clobber_receiver:
        instructions.append(_mov("0x00765820", "ESI", "EAX"))
    instructions.extend(
        [
            _mov("0x00765825", "ECX", "ESI"),
            _call(m.HALF_STEP_BODY_CALL, m.BODY_ARRAY_LOOP),
        ]
    )
    instruction_export = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            {
                "format": m.INSTRUCTION_FORMAT,
                "found": True,
                "requested": m.HALF_STEP,
                "function": _function(m.HALF_STEP, "FUN_00765470"),
                "instructions": instructions,
            }
        ],
    )
    return m, source, source_sha, ghidra, instruction_export, global_identity, chassis, body


def _build(fixture):
    m, source, source_sha, ghidra, instructions, global_identity, chassis, body = fixture
    report = m.analyze_global_vehicle_body_owner_continuity(
        source,
        ghidra,
        instructions,
        global_identity,
        chassis,
        body,
        expected_source_sha256=source_sha,
    )
    return m, report


def test_source_and_machine_receiver_continuity_admits_chassis_body_zero(tmp_path: Path):
    m, report = _build(_fixture(tmp_path))
    assert report["format"] == "SHIFT.GlobalVehicleBodyOwnerContinuity/1"
    assert report["source_receiver_join"]["outer_receiver_forwarded_to_half_step"] is True
    assert report["source_receiver_join"]["half_step_receiver_forwarded_to_BODY_owner"] is True
    trace = report["machine_receiver_join"]["receiver_trace"]
    assert trace["evidence_state"] == "verified"
    assert trace["status"] == "exact-entry-ECX-value-preserved"
    assert any(step["kind"] == "callee-saved-register-preserved-across-direct-call" for step in trace["chain"])
    assert report["identity_join"]["BODY_array_owner_is_global_vehicle_base"] is True
    assert report["handoff"]["outer_receiver_to_BODY_owner_continuity_proven"] is True
    assert report["handoff"]["vehicle_BODY_selection_ready"] is True
    assert report["handoff"]["selected_BODY_index"] == 0
    assert report["handoff"]["phase698_positive_selection_admissible"] is True
    assert report["blockers"] == []


def test_source_receiver_divergence_keeps_handoff_closed(tmp_path: Path):
    _, report = _build(_fixture(tmp_path, body_owner_arg="param_2"))
    assert report["source_receiver_join"]["half_step_receiver_forwarded_to_BODY_owner"] is False
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["selected_BODY_index"] is None
    assert [row["id"] for row in report["blockers"]] == [
        "half-step-to-BODY-owner-source-receiver"
    ]


def test_machine_receiver_clobber_keeps_handoff_closed(tmp_path: Path):
    _, report = _build(_fixture(tmp_path, clobber_receiver=True))
    trace = report["machine_receiver_join"]["receiver_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "receiver-register-redefined"
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["phase698_positive_selection_admissible"] is False
    assert report["blockers"][0]["id"] == "half-step-to-BODY-owner-machine-receiver"


def test_callgraph_or_binary_drift_fails_closed(tmp_path: Path):
    fixture = _fixture(tmp_path)
    m, source, source_sha, ghidra, instructions, global_identity, chassis, body = fixture
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {"from_function": m.OUTER_UPDATE, "to": m.HALF_STEP, "instruction": "0x00770fac", "indirect": False},
            {"from_function": m.OUTER_UPDATE, "to": m.HALF_STEP, "instruction": "0x00770fdc", "indirect": False},
            {"from_function": m.HALF_STEP, "to": m.BODY_ARRAY_LOOP, "instruction": "0x0076582b", "indirect": False},
        ],
    )
    with pytest.raises(ValueError, match="half-step -> BODY-array direct callsite drift"):
        m.analyze_global_vehicle_body_owner_continuity(
            source, ghidra, instructions, global_identity, chassis, body,
            expected_source_sha256=source_sha,
        )


def test_circular_preclaim_is_rejected(tmp_path: Path):
    fixture = _fixture(tmp_path)
    m, source, source_sha, ghidra, instructions, global_identity, chassis, body = fixture
    value = json.loads(global_identity.read_text(encoding="utf-8"))
    value["handoff"]["outer_receiver_to_BODY_owner_continuity_proven"] = True
    global_identity.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="preclaims BODY owner continuity"):
        m.analyze_global_vehicle_body_owner_continuity(
            source, ghidra, instructions, global_identity, chassis, body,
            expected_source_sha256=source_sha,
        )
