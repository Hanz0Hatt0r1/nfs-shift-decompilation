from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_vehicle_descriptor_physics_render_owner_frontier.py"
SPEC = importlib.util.spec_from_file_location("analyze_vehicle_descriptor_physics_render_owner_frontier", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _database(tmp_path: Path, *, extra_init_caller: bool = False) -> Path:
    root = tmp_path / "db"
    root.mkdir()
    _write_json(
        root / "binary.json",
        {
            "format": m.DB_FORMAT,
            "program_name": m.PROGRAM,
            "executable_md5": m.PE_MD5,
        },
    )
    function_rows = [
        {"address": "0x0074da70", "name": "FUN_0074da70", "size": 100, "calling_convention": "__thiscall"},
        {"address": "0x00798df0", "name": "FUN_00798df0", "size": 200, "calling_convention": "__thiscall"},
        {"address": m.HDVEHICLE_INIT, "name": "FUN_0076df50", "size": 300, "calling_convention": "__thiscall"},
    ]
    if extra_init_caller:
        function_rows.append(
            {"address": "0x00700000", "name": "FUN_00700000", "size": 10, "calling_convention": "__thiscall"}
        )
    _write_jsonl(root / "functions.jsonl", function_rows)

    call_rows = [
        {
            "from_function": "0x0074da70",
            "instruction": "0x0074dadf",
            "to": m.HDVEHICLE_INIT,
            "indirect": False,
        },
        {
            "from_function": "0x00798df0",
            "instruction": "0x00798f9c",
            "to": m.HDVEHICLE_INIT,
            "indirect": False,
        },
    ]
    if extra_init_caller:
        call_rows.append(
            {
                "from_function": "0x00700000",
                "instruction": "0x00700004",
                "to": m.HDVEHICLE_INIT,
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", call_rows)
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00abbb8c",
                "value": m.PHYSICS_MODEL_PROPERTY,
                "xrefs": ["0x00d6bacf"],
                "functions": ["0x00d6b610"],
            },
            {
                "address": "0x00abbbcc",
                "value": m.RENDER_MODEL_PROPERTY,
                "xrefs": ["0x00d6b929"],
                "functions": ["0x00d6b610"],
            },
        ],
    )
    return root


def _source(tmp_path: Path, *, physics_offset: str = "0x60") -> Path:
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        f"""
void {m.REFLECTION_FUNCTION}(void) {{
    FUN_00631740(&iStack_c, "Vehicle Render Model");
    FUN_0063a280(&DAT_00b81f20, 0, &iStack_c, 0x54, 3, &iStack_8);
    FUN_00631740(&iStack_c, "Vehicle Physics Model");
    FUN_0063a280(&DAT_00b81f20, 0, &iStack_c, {physics_offset}, 3, &iStack_8);
}}

void FUN_0074da70(void) {{
    FUN_0076df50(&DAT_00c13700, DAT_00c10b34, '\\0');
    FUN_007927c0((void *)(iVar4 + 0x340), (float *)(iVar4 + 0x4a0), (undefined4 *)(iVar4 + 0x4ac), '\\0');
}}

void FUN_00798df0(void) {{
    if (DAT_00c10b34 != 0) {{
        FUN_0076df50(&DAT_00c13700, *(undefined4 *)(this + 0x848), param_1);
    }}
}}
""",
        encoding="utf-8",
    )
    return source


def _render_owner(tmp_path: Path, *, frame_ready: bool = False) -> Path:
    return _write_json(
        tmp_path / "render.json",
        {
            "format": m.RENDER_OWNER_FORMAT,
            "ready": True,
            "vehicle_descriptor": {
                "render_model_field": m.RENDER_MODEL_FIELD,
                "render_model_property_name": m.RENDER_MODEL_PROPERTY,
            },
            "handoff": {
                "vehicle_render_hierarchy_owner_ready": True,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": frame_ready,
            },
        },
    )


def _sdf_receiver(tmp_path: Path, *, frame_ready: bool = False) -> Path:
    return _write_json(
        tmp_path / "sdf.json",
        {
            "format": m.SDF_RECEIVER_FORMAT,
            "ready": True,
            "status": "ready",
            "handoff": {
                "SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX": True,
                "SDF_model_to_VHF_vehicle_root_frame_relation_ready": frame_ready,
                "BODY0_bind_frame_proof_ready": False,
            },
        },
    )


def test_builds_exact_descriptor_physics_render_owner_frontier(tmp_path):
    report = m.analyze(
        _database(tmp_path),
        _source(tmp_path),
        _render_owner(tmp_path),
        _sdf_receiver(tmp_path),
    )

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["vehicle_details_reflection"]["render_model_field"] == "+0x54"
    assert report["vehicle_details_reflection"]["physics_model_field"] == "+0x60"
    assert report["vehicle_details_reflection"]["same_descriptor_class_proves_same_coordinate_frame"] is False

    callers = report["high_detail_vehicle_init_callers"]
    assert [row["function"] for row in callers] == ["0x0074da70", "0x00798df0"]
    assert callers[0]["second_argument_expression"] == "DAT_00c10b34"
    assert callers[0]["second_argument_mentions_DAT_00c10b34"] is True
    assert callers[1]["second_argument_expression"] == "*(undefined4*)(this+0x848)"
    assert callers[1]["second_argument_field_offsets"] == ["0x848"]
    assert all(row["second_argument_is_proven_VehicleDetails_plus_0x60"] is False for row in callers)

    worklist = report["targeted_instruction_worklist"]
    assert worklist["functions"] == ["0x0074da70", "0x00798df0"]
    assert worklist["neighbors_added"] is False
    assert report["handoff"]["vehicle_physics_model_to_HighDetailVehicle_Init_argument_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["scope"]["common_descriptor_class_promoted_to_frame_identity"] is False


def test_rejects_vehicle_physics_model_reflection_offset_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(
            _database(tmp_path),
            _source(tmp_path, physics_offset="0x64"),
            _render_owner(tmp_path),
            _sdf_receiver(tmp_path),
        )


def test_rejects_high_detail_vehicle_init_direct_caller_drift(tmp_path):
    with pytest.raises(ValueError, match="direct-caller drift"):
        m.analyze(
            _database(tmp_path, extra_init_caller=True),
            _source(tmp_path),
            _render_owner(tmp_path),
            _sdf_receiver(tmp_path),
        )


def test_rejects_upstream_frame_preclaim(tmp_path):
    with pytest.raises(ValueError, match="preclaims frame identity"):
        m.analyze(
            _database(tmp_path),
            _source(tmp_path),
            _render_owner(tmp_path, frame_ready=True),
            _sdf_receiver(tmp_path),
        )


def test_rejects_sdf_frame_preclaim(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims"):
        m.analyze(
            _database(tmp_path),
            _source(tmp_path),
            _render_owner(tmp_path),
            _sdf_receiver(tmp_path, frame_ready=True),
        )
