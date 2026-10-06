from __future__ import annotations
import importlib.util, json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_primary_player_first_bootstrap_render_root_delta.py"
SPEC = importlib.util.spec_from_file_location("delta", TOOL); assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

def _source(writer_in_prefix: bool = False) -> str:
    writer = "FUN_0078ef00(0);" if writer_in_prefix else ""
    return rf'''
void FUN_0074ddc3(void) {{
 FUN_00797fd0((void *)(*unaff_ESI + 0x340),*(int *)(iVar1 + 0x10),'\0',1);
 if (*(int *)(iVar1 + 0x10) == 0) {{ DAT_00c10b34 = unaff_ESI; }}
 {writer}
 FUN_00798df0((void *)(iVar6 + 0x340),(char)*(undefined4 *)(unaff_EBP + 0xc));
}}
void FUN_00797fd0(void) {{ *(int *)((int)this + 0x234) = param_1; }}
void FUN_00798df0(void) {{ FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1); }}
void FUN_0079bfd0(void) {{ param_1[0x67] = 0; param_1[0x68] = 0; param_1[0x69] = 0; }}
void FUN_00795d60(void) {{
 if (*(int *)((int)param_1 + 0x234) == 0) {{
  local_3c = local_28 - (float)_DAT_00c16ab0;
  local_38 = *(float *)((int)param_1 + 0x1a0) - (float)_DAT_00c16ab8;
  local_34 = *(float *)((int)param_1 + 0x1a4) - (float)_DAT_00c16ac0;
 }}
 *(float *)((int)param_1 + 0x19c) = local_3c;
 *(float *)((int)param_1 + 0x1a0) = local_38;
 *(float *)((int)param_1 + 0x1a4) = local_34;
}}
void FUN_0074e760(void) {{ *(undefined4 *)(param_1 + 0x10) = 0; }}
void FUN_0078ef00(void) {{ FUN_007afd20(a,b,(double *)&DAT_00c16ab0,c); }}
'''

def test_committed_contract_closes_only_s1():
    value=json.loads((ROOT/"evidence"/"bmw_primary_player_first_bootstrap_render_root_delta.json").read_text())
    assert value["format"] == MODULE.FORMAT and value["ready"] is True
    assert value["semantic_authority"] == "single process"
    assert value["selected_numeric"]["delta_local"] == [0.0,0.0,0.0]
    assert value["handoff"]["BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready"] is True
    assert value["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert value["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert value["handoff"]["vehicle_world_transform_ready"] is False

def test_source_markers_prove_role_zero_constructor_zero_and_formula():
    proof=MODULE.validate_source(_source(), require_hash=False)
    assert proof["role_field"] == "+0x234"
    assert proof["constructor_delta_zero"] == ["+0x19c","+0x1a0","+0x1a4"]
    assert proof["formula"] == "new_delta = old_delta - origin"

def test_source_rejects_origin_writer_in_selected_prefix():
    with pytest.raises(ValueError, match="origin writer entered Restart->InitVehicle prefix"):
        MODULE.validate_source(_source(True), require_hash=False)

def test_upstream_numeric_preclaim_fails_closed():
    relation={"format":MODULE.RELATION_FORMAT,"ready":True,"semantic_authority":"Process 1","subject":{"vehicle":MODULE.VEHICLE,"canonical_vhf":MODULE.CANONICAL_VHF},"relation":{"kind":"fixed_affine","relation_matrix_numeric_ready":True},"handoff":{"outer_vehicle_root_to_VHF_fixed_affine_delta_ready":True,"outer_vehicle_root_to_VHF_relation_numeric_matrix_ready":True}}
    session={"format":MODULE.SESSION_FORMAT,"ready":True,"vehicle":MODULE.VEHICLE,"session_target":MODULE.SESSION_TARGET,"selector":{"source":"explicit-native-vertical-slice-policy","validated_against_retail_selector_domain":True}}
    with pytest.raises(ValueError, match="already has a numeric matrix"):
        MODULE.validate_upstream(relation,session)
