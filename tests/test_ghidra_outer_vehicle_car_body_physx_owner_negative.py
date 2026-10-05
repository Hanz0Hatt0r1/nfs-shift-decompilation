from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "classify_outer_vehicle_car_body_physx_owner.py"
SPEC = importlib.util.spec_from_file_location("classify_outer_vehicle_car_body_physx_owner", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _db(tmp_path: Path) -> Path:
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
    return root


def _upstream(path: Path, *, preclaim: bool = False) -> Path:
    return _write_json(
        path,
        {
            "format": m.UPSTREAM_FORMAT,
            "ready": True,
            "chassis_init": {
                "embedded_owner_edges": [
                    {"offset": "+0x34", "callee": "0x00777cd0", "kind": "loaded-pointer"},
                    {"offset": "+0x534", "callees": ["0x007a3d60"]},
                ]
            },
            "handoff": {
                "HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain": True,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
            },
        },
    )


def _source(path: Path, *, producer_slot: str = "0x1c") -> Path:
    # Put a call before the definition to ensure the source extractor selects a
    # real function definition rather than the first lexical occurrence.
    text = f'''\
void noise(void) {{ FUN_007798a0(0,0,0,0,0,0,0,0); }}

uint __fastcall FUN_007506b0(int param_1)
{{
  DAT_00c13384 = (int *)NxCreatePhysicsSDK(0x2080100,DAT_00c13388,DAT_00c1338c,&local_7c,0);
  if (DAT_00c13384 == (int *)0x0) {{
    FUN_0062de20("Failed to Create PhysX SDK");
    FUN_0062de50(0xb089d0,".\\\\Source\\\\System\\\\PhysicsSystem.cpp",0xe8,0xb08af0,'\\0');
  }}
  DAT_00c133ac = (int *)(**(code **)(*DAT_00c13384 + 0x10))(&local_128);
  return 1;
}}

uint __thiscall
FUN_007798a0(void *this,undefined4 *param_1,int *param_2,int param_3,char param_4,int param_5,
            undefined2 *param_6,int *param_7)
{{
  piVar11 = (int *)(**(code **)(*DAT_00c133ac + {producer_slot}))(local_c0);
  if (piVar11 != (int *)0x0) {{
    *param_2 = param_3;
    param_2[1] = (int)piVar11;
    piVar11[1] = (int)param_2;
  }}
  return 1;
}}

void __fastcall FUN_00777cd0(int *param_1)
{{
  uVar2 = (**(code **)(*param_1 + 0x4c))();
  local_8 = (**(code **)(*param_1 + 0x50))();
}}

void __thiscall FUN_007ac2f0(void *this,char param_1)
{{
  piVar1 = *(int **)((int)this + 0x34);
  FUN_007ab4e0(piVar1,local_58);
  (**(code **)(*piVar1 + 0xe0))(local_58 + 0xf);
  (**(code **)(*piVar1 + 0xe4))(local_58 + 0xc);
}}

void __fastcall FUN_007ac4d0(int param_1,char param_2,undefined4 param_3,int *param_4,int *param_5)
{{
  FUN_007798a0(piVar5,&local_4c,(int *)(param_1 + 0x30),(int)local_14,(char)param_4 != '\\0',*piVar8,local_1c,param_5);
  param_4 = *(int **)(param_1 + 0x34);
  FUN_00777cd0(param_4);
}}

void __fastcall FUN_007ab8e0(int param_1,char param_2)
{{
  piVar1 = *(int **)(param_1 + 0x34);
  if (piVar1 != (int *)0x0) {{
    FUN_00776d00(piVar1);
    (**(code **)(*DAT_00c133ac + 0x20))(piVar1);
    *(undefined4 *)(param_1 + 0x34) = 0;
  }}
}}
'''
    path.write_text(text, encoding="utf-8")
    return path


def test_retires_car_body_plus_34_as_positive_vhf_owner_candidate(tmp_path):
    report = m.analyze(
        _db(tmp_path),
        _upstream(tmp_path / "upstream.json"),
        _source(tmp_path / "SHIFT.exe.c"),
    )

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["ownership_chain"]["same_physics_owner_for_create_and_release"] is True
    assert report["ownership_chain"]["physx_owned_lifetime_ready"] is True
    assert report["negative_classification"]["car_body_plus_0x34_physx_owned_lifetime_proven"] is True
    assert report["negative_classification"]["car_body_plus_0x34_is_admissible_standalone_VHF_identity_anchor"] is False
    assert report["negative_classification"]["car_body_plus_0x34_branch_removed_from_positive_VHF_owner_search"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["physx_subclass_name_invented"] is False
    assert report["scope"]["absence_of_all_render_aliases_claimed"] is False


def test_rejects_physics_scene_create_slot_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(
            _db(tmp_path),
            _upstream(tmp_path / "upstream.json"),
            _source(tmp_path / "SHIFT.exe.c", producer_slot="0x24"),
        )


def test_rejects_upstream_vhf_preclaim(tmp_path):
    with pytest.raises(ValueError, match="preclaims VHF-root identity"):
        m.analyze(
            _db(tmp_path),
            _upstream(tmp_path / "upstream.json", preclaim=True),
            _source(tmp_path / "SHIFT.exe.c"),
        )


def test_rejects_missing_loaded_pointer_edge(tmp_path):
    upstream = json.loads(_upstream(tmp_path / "upstream.json").read_text(encoding="utf-8"))
    upstream["chassis_init"]["embedded_owner_edges"] = []
    (tmp_path / "upstream.json").write_text(json.dumps(upstream) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="loaded-pointer edge missing"):
        m.analyze(_db(tmp_path), tmp_path / "upstream.json", _source(tmp_path / "SHIFT.exe.c"))


def test_rejects_retail_binary_identity_drift(tmp_path):
    root = _db(tmp_path)
    binary = json.loads((root / "binary.json").read_text(encoding="utf-8"))
    binary["executable_md5"] = "0" * 32
    (root / "binary.json").write_text(json.dumps(binary) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity drift"):
        m.analyze(root, _upstream(tmp_path / "upstream.json"), _source(tmp_path / "SHIFT.exe.c"))
