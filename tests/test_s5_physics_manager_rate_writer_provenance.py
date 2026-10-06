from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_physics_manager_rate_writer_provenance.json"
OWNER = ROOT / "evidence/physics_manager_scheduler_entry_owner.json"
ANALYZER = ROOT / "tools/ghidra/analyze_s5_physics_manager_rate_writer_pe.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_s5_physics_manager_rate_writer_pe", ANALYZER
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_retail_rate_writer_is_positive_and_joined_to_source_backed_manager():
    report = _load(EVIDENCE)
    owner = _load(OWNER)

    assert report["format"] == "SHIFT.PhysicsManagerRateWriterProvenance/1"
    assert report["ready"] is True
    assert report["status"] == "cPhysicsManager-plus-0x388-writer-and-initial-value-proven"
    assert report["retail_image"]["md5"] == owner["provenance"]["retail_pe_md5"]

    joined = report["source_backed_object_join"]
    assert joined["format"] == owner["format"]
    assert joined["owner"] == owner["owner"] == "MWL::Core::cPhysicsManager"
    assert joined["vtable"] == owner["scheduler_entry"]["vtable_address"] == "0x00b04524"
    assert joined["source_manager_contract"] == owner["provenance"]["source_manager_contract"]
    assert joined["verified"] is True


def test_writer_param1_directly_feeds_integer_plus_0x388_store():
    report = _load(EVIDENCE)
    writer = report["writer"]

    assert writer["function"] == "FUN_0070f170"
    assert writer["address"] == "0x0070f170"
    assert writer["calling_convention"] == "__thiscall"
    assert writer["parameters"] == [
        {"name": "this", "storage": "ECX:4 (auto)", "type": "void *"},
        {"name": "param_1", "storage": "Stack[0x4]:4", "type": "int"},
    ]
    dependency = writer["direct_integer_value_dependency"]
    assert dependency == {
        "displacement": 0x388,
        "displacement_hex": "0x388",
        "proven": True,
        "receiver": "ECX",
        "source": "Stack[0x4]:4 param_1",
        "source_load_instruction": "0x0070f176",
        "store_instruction": "0x0070f179",
    }
    assert report["machine_fragments"]["writer_param_integer_load"]["bytes"] == "8b4508"
    assert report["machine_fragments"]["writer_plus_0x388_store"]["bytes"] == "898188030000"


def test_constructor_proves_manager_receiver_and_initial_rate_180():
    report = _load(EVIDENCE)
    join = report["constructor_receiver_join"]

    assert join["function"] == "FUN_0070fae0"
    assert join["source_backed_vtable_installed_on_ESI"] == "0x0070fb13"
    assert join["vtable"] == "0x00b04524"
    assert join["initial_value_push"] == "0x0070fc3d"
    assert join["initial_value"] == 180
    assert join["writer_receiver_restored_from_ESI"] == "0x0070fc60"
    assert join["writer_call"] == "0x0070fc68"
    assert join["cPhysicsManager_receiver_to_writer_proven"] is True

    machine = report["machine_fragments"]
    assert machine["constructor_install_manager_vtable"]["bytes"] == "c7062445b000"
    assert machine["constructor_push_initial_rate_180"]["bytes"] == "68b4000000"
    assert machine["constructor_restore_receiver_for_writer"]["bytes"] == "8bce"


def test_writer_arithmetic_freezes_reciprocal_and_rate_over_30_relationships():
    report = _load(EVIDENCE)
    derived = report["writer"]["derived_fields"]

    assert derived["constant_30_value"] == 30.0
    assert derived["plus_0x38c"] == "1.0 / float(param_1)"
    assert derived["plus_0x390"] == "float(param_1) / 30.0"
    assert derived["plus_0x394"] == "1.0 / (float(param_1) / 30.0)"
    assert derived["machine_relationships_proven"] is True


def test_accessor_return_is_independently_seen_as_writer_receiver():
    report = _load(EVIDENCE)
    join = report["accessor_receiver_join"]

    assert join["function"] == "FUN_00714560"
    assert join["accessor_call"] == "0x00714571"
    assert join["receiver_transfer"] == "0x00714576 MOV ECX,EAX"
    assert join["writer_call"] == "0x00714578"
    assert join["accessor_return_to_writer_receiver_proven"] is True
    assert report["decompiler_crosscheck"]["accessor_return_flows_to_writer_receiver"] is True


def test_direct_writer_caller_surface_is_exactly_frozen():
    report = _load(EVIDENCE)
    actual = {
        (row["from_function"], row["instruction"])
        for row in report["direct_callers"]
    }
    assert actual == {
        ("0x0070fae0", "0x0070fc68"),
        ("0x00710a70", "0x00710c1c"),
        ("0x007117e0", "0x00711813"),
        ("0x007119c0", "0x00711b37"),
        ("0x00714560", "0x00714578"),
    }


def test_writer_proof_keeps_physical_units_and_final_cadence_fail_closed():
    report = _load(EVIDENCE)
    adjudication = report["adjudication"]

    assert adjudication["FUN_0070f170_is_cPhysicsManager_plus_0x388_writer"] is True
    assert adjudication["plus_0x388_stored_value_is_writer_integer_param1"] is True
    assert adjudication["constructor_initializes_plus_0x388_to_180"] is True
    assert adjudication["plus_0x388_semantic_role_is_integer_step_rate_candidate"] is True
    assert adjudication["plus_0x388_physical_units_proven"] is False
    assert adjudication["normal_outer_quantum_proven"] is False
    assert adjudication["retail_fixed_step_quantum_proven"] is False
    assert adjudication["retail_cadence_admitted"] is False

    limits = report["limits"]
    assert limits["field_named_frequency_from_offset_only"] is False
    assert limits["seconds_unit_assumed"] is False
    assert limits["host_1_60_promoted"] is False
    assert limits["runtime_capture_used"] is False


def _decompiler_fixture(*, constructor_value: str = "0xb4") -> str:
    return f"""
void __thiscall FUN_0070f170(void *this,int param_1)
{{
  float fVar1;
  *(int *)((int)this + 0x388) = param_1;
  *(float *)((int)this + 0x38c) = 1.0 / (float)param_1;
  fVar1 = (float)param_1 / 30.0;
  *(float *)((int)this + 0x390) = fVar1;
  *(float *)((int)this + 0x394) = 1.0 / fVar1;
}}
undefined4 * __fastcall FUN_0070fae0(undefined4 *param_1)
{{
  FUN_0070f170(param_1,{constructor_value});
  return param_1;
}}
undefined4 __thiscall FUN_00714560(void *this,int param_1)
{{
  void *this_00;
  uint uVar1;
  this_00 = (void *)FUN_0070fe90();
  FUN_0070f170(this_00,uVar1);
  return 0;
}}
"""


def test_decompiler_crosscheck_accepts_exact_writer_constructor_and_accessor_join():
    result = MODULE._validate_decompiler(_decompiler_fixture())
    assert result == {
        "writer_contract_verified": True,
        "constructor_calls_writer_with_180": True,
        "accessor_return_flows_to_writer_receiver": True,
    }


def test_decompiler_crosscheck_rejects_constructor_value_drift():
    with pytest.raises(ValueError, match="0xb4"):
        MODULE._validate_decompiler(_decompiler_fixture(constructor_value="0x3c"))
