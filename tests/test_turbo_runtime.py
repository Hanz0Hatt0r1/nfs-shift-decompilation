import pytest

from upgrade_modifier_runtime import ModifierNode
from turbo_runtime import parse_turbo_bbf, parse_turbo_tbf


def test_bbf_parses_source_fields_and_clamps_active_timing_values():
    report = parse_turbo_bbf(
        """
Boost=0.75
Max Boost=1.25
Boost Time=2.0
Fill Time=-1.0
Max Boost Time=12.0
Ramp Down Time=4.0
Min Level To Fire=9.0
GlobalUpgrades=0x8
""",
        max_value=5.0,
    )
    assert report["ready"] is True
    assert report["resource_type"] == "BBF"
    assert report["values"]["Boost"] == pytest.approx(0.75)
    assert report["postload"]["active"] is True
    assert report["values"]["Fill Time"] == 0.0
    assert report["values"]["Max Boost Time"] == 5.0
    assert report["values"]["Ramp Down Time"] == 4.0
    assert report["values"]["Min Level To Fire"] == 5.0
    assert report["evidence"]["active_flag_offset"] == "0x50"


def test_bbf_applies_upgrade_chain_before_active_check():
    nodes = (
        ModifierNode(0.0, 0.0, 0, 0, additive=False),
        ModifierNode(0.0, 2.0, 0, 1, additive=True),
    )
    report = parse_turbo_bbf(
        "Boost=0\nBoost Time=0\n",
        boost_upgrade_nodes=nodes,
        boost_time_upgrade_nodes=nodes,
    )
    assert report["postload"]["boost_after_upgrade"] == 0.0
    assert report["postload"]["boost_time_after_upgrade"] == 0.0
    assert report["postload"]["active"] is False


def test_tbf_applies_exact_size_rpm_and_fuel_conversions():
    report = parse_turbo_tbf(
        """
Twin Turbo=true
Sequential Turbo=false
WasteGate Opening=0.25
WasteGate Closing=0.75
Turbo1 Size=100
Turbo1 Engine RPM=6000
Turbo1 Inertia=0.02
Turbo1 Friction=0.03
Turbo1 Turbine Optimum RPM=4500
Turbo1 Fuel Percentage=10
Turbo2 Size=50
Turbo2 Engine RPM=5000
Turbo2 Inertia=0.04
Turbo2 Friction=0.05
Turbo2 Turbine Optimum RPM=4000
Turbo2 Fuel Percentage=5
GlobalUpgrades=0x8
"""
    )
    assert report["ready"] is True
    assert report["values"]["Twin Turbo"] is True
    first = report["turbos"][0]["fields"]
    second = report["turbos"][1]["fields"]
    assert first["Size"]["value"] == pytest.approx(1.0)
    assert first["Engine RPM"]["value"] == pytest.approx(6000 * 0.10471976)
    assert first["Turbine Optimum RPM"]["value"] == pytest.approx(4500 * 0.10471976)
    assert first["Fuel Percentage"]["value"] == pytest.approx(0.10)
    assert second["Size"]["value"] == pytest.approx(0.50)
    assert second["Fuel Percentage"]["value"] == pytest.approx(0.05)
    assert report["evidence"]["twin_turbo_offset"] == "0x05"


def test_tbf_size_modifiers_apply_after_source_conversion():
    nodes = (ModifierNode(0.0, 2.0, 0, 0, additive=True),)
    report = parse_turbo_tbf(
        "Turbo1 Size=100\nTurbo2 Size=50\n",
        turbo1_size_upgrade_nodes=nodes,
        turbo2_size_upgrade_nodes=nodes,
    )
    assert report["postload"]["turbo1_size_after_upgrade"] == pytest.approx(3.0)
    assert report["postload"]["turbo2_size_after_upgrade"] == pytest.approx(2.5)
    assert report["postload"]["return_scalar"] == pytest.approx(6.5)


def test_tbf_return_scalar_matches_source_postload_expression():
    report = parse_turbo_tbf("Turbo1 Size=200\nTurbo2 Size=300\n")
    assert report["postload"]["turbo1_size_after_upgrade"] == pytest.approx(2.0)
    assert report["postload"]["turbo2_size_after_upgrade"] == pytest.approx(3.0)
    assert report["postload"]["return_scalar"] == pytest.approx(6.0)
