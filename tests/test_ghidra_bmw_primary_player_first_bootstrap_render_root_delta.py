from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_primary_player_first_bootstrap_render_root_delta.py"
SPEC = importlib.util.spec_from_file_location("bmw_primary_player_first_bootstrap_delta", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _source(*, writer_in_prefix: bool = False) -> str:
    writer = "FUN_0078ef00(0);" if writer_in_prefix else ""
    return rf"""
void FUN_0074ddc3(void) {{
  FUN_0074d640(param_1);
  iVar1 = *(int *)(unaff_EBP + 8);
  FUN_00797fd0((void *)(*unaff_ESI + 0x340),*(int *)(iVar1 + 0x10),'\0',1);
  if (*(int *)(iVar1 + 0x10) == 0) {{
    _DAT_00c10b30 = unaff_ESI;
    DAT_00c10b34 = unaff_ESI;
  }}
  {writer}
  FUN_00798df0((void *)(iVar6 + 0x340),(char)*(undefined4 *)(unaff_EBP + 0xc));
}}
void FUN_0074d640(void) {{ int x = 0; }}
void FUN_00797fd0(void) {{ *(int *)((int)this + 0x234) = param_1; }}
void FUN_00798df0(void) {{
  FUN_00a62690((int)this,0,0,0,uVar12,0x4000);
  FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);
}}
void FUN_0079bfd0(void) {{
  param_1[0x67] = 0;
  param_1[0x68] = 0;
  param_1[0x69] = 0;
}}
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
void FUN_0078ef00(void) {{
  FUN_007afd20(a,b,(double *)&DAT_00c16ab0,c);
}}
void FUN_00a62690(void) {{ *(undefined4 *)(param_1 + 8) = param_6; }}
"""


def test_committed_handoff_is_narrow_positive_stage():
    value = json.loads(
        (ROOT / "evidence" / "bmw_primary_player_first_bootstrap_render_root_delta.json").read_text(
            encoding="utf-8"
        )
    )
    assert value["format"] == MODULE.FORMAT
    assert value["ready"] is True
    assert value["status"] == "bmw-primary-player-first-bootstrap-render-root-delta-proven"
    assert value["semantic_authority"] == "single process"
    assert value["selected_numeric"]["delta_local"] == [0.0, 0.0, 0.0]
    assert value["handoff"]["BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready"] is True
    assert value["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is True
    assert value["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert value["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert value["handoff"]["vehicle_world_transform_ready"] is False
    assert value["limits"]["first_primary_player_bootstrap_only"] is True
    assert value["limits"]["delta_zero_claimed_for_restart_or_mode_switch"] is False
    assert value["limits"]["native_role_policy_is_retail_live_session_observation"] is False


def test_zero_fill_fact_distinguishes_raw_and_virtual_tail():
    sections = [
        {
            "name": ".data",
            "virtual_address": 0x781000,
            "virtual_size": 0x167040,
            "raw_size": 0x3B600,
            "raw_pointer": 0x77F600,
        }
    ]
    row = MODULE.zero_fill_fact(0x400000, sections, 0x00C16AB0)
    assert row["section"] == ".data"
    assert row["section_offset"] == "0x95ab0"
    assert row["image_loader_zero_fill"] is True

    row = MODULE.zero_fill_fact(0x400000, sections, 0x00B82000)
    assert row["image_loader_zero_fill"] is False


def test_source_validator_binds_primary_role_constructor_zero_and_prefix_continuity():
    proof = MODULE.validate_source(_source(), require_hash=False)
    assert proof["restart_zero_role_designates_primary_participant"] is True
    assert proof["vehicle_role_code_field"] == "+0x234"
    assert proof["vehicle_constructor_delta_zero_offsets"] == ["+0x19c", "+0x1a0", "+0x1a4"]
    assert proof["origin_writer_in_restart_to_initvehicle_prefix"] is False


def test_source_validator_rejects_origin_writer_in_restart_prefix():
    with pytest.raises(ValueError, match="origin writer entered Restart->InitVehicle prefix"):
        MODULE.validate_source(_source(writer_in_prefix=True), require_hash=False)


def test_upstream_numeric_preclaim_is_rejected():
    relation = {
        "format": MODULE.RELATION_FORMAT,
        "ready": True,
        "semantic_authority": "Process 1",
        "subject": {"vehicle": MODULE.VEHICLE, "canonical_vhf": MODULE.CANONICAL_VHF},
        "relation": {"kind": "fixed_affine", "relation_matrix_numeric_ready": True},
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": True,
        },
    }
    session = {
        "format": MODULE.SESSION_FORMAT,
        "ready": True,
        "vehicle": MODULE.VEHICLE,
        "session_target": MODULE.SESSION_TARGET,
        "selector": {
            "source": "explicit-native-vertical-slice-policy",
            "validated_against_retail_selector_domain": True,
        },
    }
    with pytest.raises(ValueError, match="already has a numeric matrix"):
        MODULE.validate_upstream(relation, session)
