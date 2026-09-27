import pytest

from physics_participant_runtime import build_config_evidence, build_spawn_evidence
from physics_system_runtime import (
    CSM_VERSION,
    PHYSX_SDK_VERSION,
    build_filter_relations,
    build_manager_layout,
    build_physics_paths,
    build_physics_system_contract,
    build_physics_tweaker_contract,
    build_scene_descriptor_defaults,
)


def test_exact_physx_and_csm_versions():
    c = build_physics_system_contract()
    assert c["physx"]["sdk_version"] == 0x02080100
    assert c["assets"]["collision_stream"]["version"] == 0xAFB
    assert PHYSX_SDK_VERSION == 0x02080100
    assert CSM_VERSION == 0xAFB


def test_mission_collision_path():
    p = build_physics_paths("donington")
    assert p["mission_collision_stem"] == "campaign/missions/donington/physics/donington"
    assert p["mission_collision_csm"] == "campaign/missions/donington/physics/donington.csm"
    assert p["aiw"] == "AIW/donington.aiw"
    assert p["sections"] == "Sections/donington.tsl"


def test_filter_loop_cardinality_and_exception():
    rel = build_filter_relations()
    assert sum(r["group_a"] == 0x1E for r in rel) == 0x1F
    assert sum(r["group_a"] == 0x1D for r in rel) == 0x1E
    assert not any(r["group_a"] == 0x1D and r["group_b"] == 4 for r in rel)
    assert {(r["group_a"], r["group_b"], r["flags"]) for r in rel[:3]} == {
        (1, 2, 0), (3, 3, 0), (3, 2, 0)
    }


def test_manager_layout():
    c = build_manager_layout()
    assert c["named_object"] == "Physics Manager"
    assert c["path_fields"][0]["value"] == "Tracks/_Data/"
    assert c["shutdown"]["array_destruct_order"] == [
        "0x384", "0x380", "0x37c", "0x378", "0x374", "0x370"
    ]


def test_scene_descriptor_keeps_unknown_semantics():
    c = build_scene_descriptor_defaults()
    assert c["semantic_status"] == "field-names-unresolved"
    assert c["observed_words"]["offset_0x50"]["u32"] == 4


def test_physics_tweaker_loader_boundary():
    c = build_physics_tweaker_contract()
    assert c["path"] == "PhysicsTweaker.xml"
    assert c["load"]["virtual_load_offset"] == 0x20
    assert c["load"]["virtual_finish_offset"] == 0x24


def test_participant_config_raw_values():
    c = build_config_evidence()
    assert c["defaults"]["0x18_raw"] == 0x3F570A3D
    assert c["defaults"]["0x1c_raw"] == 0xBE4CCCCD
    assert c["paths"]["cdf"]["suffix"] == ".cdf"


def test_participant_modes_are_exactly_zero_to_four():
    c = build_spawn_evidence()
    assert sorted(c["modes"]) == [0, 1, 2, 3, 4]
    assert c["modes"][3]["apply"] == "FUN_00793a80"
    assert c["modes"][4]["source"] == "config +0x28..+0x3c"


def test_empty_mission_rejected():
    with pytest.raises(ValueError):
        build_physics_paths("")
