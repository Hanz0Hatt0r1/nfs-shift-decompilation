import pytest

from vehicle_physics_asset_runtime import (
    build_vehicle_physics_contract,
    build_vehicle_physics_roots,
)


def test_exact_vehicle_physics_roots():
    roots = build_vehicle_physics_roots()
    assert roots == {
        "chassis": "vehicles/Physics/Chassis/",
        "collision": "vehicles/Physics/Collision/",
        "engines": "vehicles/Physics/Engines/",
        "gearbox": "vehicles/Physics/GearBox/",
        "suspension": "vehicles/Physics/Suspension/",
        "upgrades": "vehicles/Physics/Upgrades/",
        "vehicles": "vehicles/Physics/Vehicles/",
    }


def test_chassis_root_is_linked_to_participant_cdf():
    c = build_vehicle_physics_contract()
    assert c["consumers"]["chassis"]["function"] == "FUN_0074d640"
    assert c["consumers"]["chassis"]["suffix"] == ".cdf"
    assert c["consumers"]["chassis"]["field_offset"] == 0x04


def test_base_path_is_not_optional_in_empty_form():
    with pytest.raises(ValueError):
        build_vehicle_physics_roots("")


def test_unknowns_are_explicit():
    c = build_vehicle_physics_contract()
    assert c["status"] == "path-registry-reconstructed"
    assert "filename/key schema below each root" in c["unknowns"][1]
