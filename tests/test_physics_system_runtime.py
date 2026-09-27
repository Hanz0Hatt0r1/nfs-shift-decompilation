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


def test_physics_provider_registry_preserves_two_source_slots_and_vtable_offsets():
    from physics_system_runtime import build_physics_provider_registry

    report = build_physics_provider_registry()
    assert report["selector"]["index_zero"] == "DAT_00c23da8"
    assert report["selector"]["index_one"] == "DAT_00c23dac"
    assert report["selector"]["other_indices"] == "null"
    assert report["lifecycle"]["provider_zero_init"] == "FUN_007d2f70"
    assert report["lifecycle"]["provider_one_init"] == "FUN_007cd980"
    assert report["consumer_vtable"]["presence_probe"] == "+0x14"
    assert report["consumer_vtable"]["replace_primary_storage"] == "+0x04"
    assert report["consumer_vtable"]["finalize"] == "+0x2c"


def test_physics_provider_dispatch_contract_matches_fun_007b3820():
    from physics_system_runtime import build_physics_provider_dispatch_contract

    c = build_physics_provider_dispatch_contract()
    assert c["candidate_order"][0]["slot"] == "DAT_00c23da8"
    assert c["candidate_order"][1]["slot"] == "DAT_00c23dac"
    assert c["candidate_order"][0]["acceptance_argument"] == "physics_system+0x3c"
    assert c["termination"]["after_index_1"] == "selector index 2 returns null"
    assert c["accepted_provider_rewrite"]["release_old_matrix"]["function"] == "FUN_0064f4b0"
    assert c["accepted_provider_rewrite"]["replace_row_table"]["vtable_offset"] == "+0x0c"
    assert c["accepted_provider_rewrite"]["replace_graph_storage"]["vtable_offset"] == "+0x04"
    assert c["accepted_provider_rewrite"]["replace_aux_storage"]["vtable_offset"] == "+0x08"
    assert c["accepted_provider_rewrite"]["finalize"]["vtable_offset"] == "+0x2c"
    assert c["generic_fallback"]["compact_graph_builder"] == "FUN_007b1360"
    assert c["common_post_provider"]["per_body_runtime_base"].endswith("* 0x170")
