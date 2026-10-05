from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_vehicle_render_hierarchy_resource_owner.py"
SPEC = importlib.util.spec_from_file_location("analyze_vehicle_render_hierarchy_resource_owner", TOOL)
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


def _source(
    path: Path,
    *,
    property_offset: str = "0x54",
    materialize_slot: str = "0x24",
    runtime_store_offset: str = "0x178",
    vhf_extension: str = ".vhf",
    vehicle_shader: str = r"render\\shaders\\vehicles_basic.fx",
) -> Path:
    text = f'''\
undefined4 __thiscall FUN_004a5800(void *this,int *param_1)
{{
  piVar1 = (int *)((int)this + 0x10);
  iVar3 = *(int *)(iVar4 + 0xc);
  _Str2 = (char *)FUN_00403cb0(param_1);
  _Str1 = *(char **)(iVar3 + 0x10);
  iVar3 = __stricmp(_Str1,_Str2);
  if (iVar3 == 0) return *(undefined4 *)(iVar4 + 0xc);
  return 0;
}}

void __fastcall FUN_00484720(void *param_1)
{{
  piVar1 = (int *)((int)param_1 + 0xa0);
  piVar6 = piVar1;
  this = (void *)thunk_FUN_0047f675();
  iVar3 = FUN_004a5800(this,piVar6);
  if (iVar3 != 0) {{
    puVar4 = thunk_FUN_00d6e910(iVar3);
    *(undefined4 **)((int)param_1 + 0xf0) = puVar4;
    FUN_00483c50(param_1);
  }}
}}

undefined4 * __fastcall thunk_FUN_00d6e910(int param_1)
{{
  puVar1 = (undefined4 *)FUN_008868c0(0x370);
  puVar1 = FUN_004a27e0(puVar1);
  FUN_004a3000(puVar1,param_1);
  return puVar1;
}}

void __thiscall FUN_004a3000(void *this,int param_1)
{{
  FUN_00632920((void *)((int)this + 0x14),(int *)(param_1 + 0x14));
  FUN_00632920((void *)((int)this + 0x54),(int *)(param_1 + 0x54));
}}

undefined4 __fastcall FUN_00483c50(void *param_1)
{{
  pcVar7 = *(char **)(*(int *)((int)param_1 + 0xf0) + 0x14);
  puVar13 = *(undefined1 **)(*(int *)((int)param_1 + 0xf0) + 0x54);
  FUN_00636310(local_64,"rcf");
  local_150 = *(undefined4 *)((int)param_1 + 0xf0);
  FUN_004aecd0((int *)((int)param_1 + 0x1340),&local_158);
  return 1;
}}

void __fastcall FUN_004848bc(int *param_1)
{{
  FUN_00481e20(param_1 + 0x280,param_1 + 0x44);
  FUN_00483540((uint)param_1);
  FUN_004ae150(param_1 + 0x4d0,unaff_EBP + -0x50,(uint)(param_1 + 0x280));
}}

void __fastcall FUN_00480700(int param_1)
{{
  FUN_0042fc90(local_50,(undefined4 *)(param_1 + 0x1028));
  FUN_004a8c20(param_1 + 0x1340,local_50);
}}

undefined4 __fastcall FUN_004aecd0(int *param_1,int *param_2)
{{
  local_10 = param_2;
  *(int **)((int)&uStack_454 + uVar11 * -10 + iVar5 + iVar4) = local_10;
  FUN_004aea10(param_1,&local_20,*(uint *)((int)&uStack_454 + uVar11 * -10 + iVar5 + iVar4));
  return 1;
}}

void __fastcall FUN_004aea10(int param_1,undefined4 param_2,uint param_3)
{{
  uVar1 = param_3;
  iVar9 = *(int *)(*(int *)(param_3 + 8) + 0x54);
  pcVar2 = *(char **)(*(int *)(uVar1 + 8) + 0x14);
  puVar3 = *(undefined1 **)(*(int *)(uVar1 + 8) + 0x54);
  piVar4 = (int *)FUN_0069c0b0(param_2);
  uVar5 = (**(code **)(*piVar4 + {materialize_slot}))();
  *(undefined4 *)(local_18 + {runtime_store_offset}) = uVar5;
}}

undefined4 __thiscall FUN_0043e670(void *this,int param_1,int *param_2)
{{
  FUN_00636310(local_44,"{vhf_extension}");
  local_2c = (int *)FUN_0069c0b0(&local_24);
  uVar3 = (**(code **)(*local_2c + {materialize_slot}))();
  return uVar3;
}}

int * __fastcall FUN_0069c0b9(undefined4 param_1)
{{
  piVar8 = FUN_0069bac0(cVar13,pvVar14);
  return piVar8;
}}

int * __fastcall FUN_00699b10(void *param_1,undefined4 *param_2,int *param_3,uint *param_4,uint *param_5,int *param_6)
{{
  iVar12 = __stricmp(pcVar4,"HIERARCHY");
  iVar12 = __stricmp(pcVar4,"OBJECT");
  iVar12 = __stricmp(local_40,"DAMAGE");
  return piVar8;
}}

int __thiscall FUN_004a8740(void *this,int *param_1,char param_2)
{{
  FUN_00631740(&local_2c,"{vehicle_shader}");
  FUN_00631740(&local_28,"render\\\\shaders\\\\wheels.fx");
  return 1;
}}

undefined4 thunk_FUN_00d6b610(void)
{{
  FUN_00631740(&iStack_c,"Vehicle Render Model");
  FUN_0063a280(&DAT_00b81f20,0,&iStack_c,{property_offset},3,&iStack_8);
  return 1;
}}
'''
    path.write_text(text, encoding="utf-8")
    return path


def test_proves_selected_vehicle_render_hierarchy_owner(tmp_path):
    report = m.analyze(_db(tmp_path), _source(tmp_path / "SHIFT.exe.c"))

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["vehicle_descriptor"]["render_model_property_name"] == "Vehicle Render Model"
    assert report["vehicle_descriptor"]["render_model_field"] == "+0x54"
    assert report["vehicle_descriptor"]["selected_registry_descriptor_to_participant_copy_ready"] is True
    assert report["render_hierarchy_owner"]["materialized_runtime_object_field"] == "+0x178"
    assert report["render_hierarchy_owner"]["vehicle_render_hierarchy_owner_ready"] is True
    assert report["handoff"]["vehicle_render_hierarchy_owner_ready"] is True
    assert report["handoff"]["selected_BMW_vehicle_render_model_value_ready"] is False
    assert report["handoff"]["canonical_BMW_VHF_resource_join_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_rejects_vehicle_render_model_reflection_offset_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(_db(tmp_path), _source(tmp_path / "SHIFT.exe.c", property_offset="0x58"))


def test_rejects_materialize_vslot_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(_db(tmp_path), _source(tmp_path / "SHIFT.exe.c", materialize_slot="0x28"))


def test_rejects_runtime_render_object_store_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(_db(tmp_path), _source(tmp_path / "SHIFT.exe.c", runtime_store_offset="0x17c"))


def test_rejects_missing_explicit_vhf_same_loader_witness(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(_db(tmp_path), _source(tmp_path / "SHIFT.exe.c", vhf_extension=".lod"))


def test_rejects_vehicle_shader_domain_drift(tmp_path):
    with pytest.raises(ValueError, match="required source fact drift"):
        m.analyze(
            _db(tmp_path),
            _source(tmp_path / "SHIFT.exe.c", vehicle_shader=r"render\\shaders\\terrain.fx"),
        )


def test_rejects_retail_identity_drift(tmp_path):
    root = _db(tmp_path)
    binary = json.loads((root / "binary.json").read_text(encoding="utf-8"))
    binary["executable_md5"] = "0" * 32
    (root / "binary.json").write_text(json.dumps(binary) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity drift"):
        m.analyze(root, _source(tmp_path / "SHIFT.exe.c"))
