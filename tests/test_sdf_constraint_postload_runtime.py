import math

import sdf_constraint_postload_runtime as runtime


def test_copy_contract_covers_all_visible_fun_007b2ae0_fields():
    contract = runtime.build_copy_contract()
    assert contract["function"] == "FUN_007b2ae0"
    fields = {(row["source"], row["destination"]) for row in contract["fields"]}
    assert ("+0x10", "+0x10") in fields
    assert ("+0x14", "+0x14") in fields
    assert ("+0x20", "+0x20") in fields
    assert ("+0x68", "+0x68") in fields
    assert len(contract["fields"]) == 14


def test_hinge_cross_stage_matches_retail_cross_order():
    result = runtime.compute_hinge_cross_stage((1.0, 0.0, 0.0), (0.0, 1.0, 1.0))
    assert result["cross01"] == (0.0, -1.0, 1.0)
    assert result["v1_after"] == (0.0, -1.0, -1.0)


def test_hinge_cross_stage_rejects_non_three_component_input():
    try:
        runtime.compute_hinge_cross_stage((1.0, 0.0), (0.0, 1.0, 0.0))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_bar_direction_normalizes_nonzero_delta():
    result = runtime.compute_bar_direction((0,0,0), (3,0,0), (0,0,0), (0,4,0))
    assert result["delta"] == (3.0, -4.0, 0.0)
    assert math.isclose(result["direction"][0], 0.6)
    assert math.isclose(result["direction"][1], -0.8)
    assert math.isclose(result["direction"][2], 0.0)
    norm = math.sqrt(sum(v*v for v in result["direction"]))
    assert math.isclose(norm, 1.0)


def test_bar_direction_preserves_zero_delta_as_zero():
    result = runtime.compute_bar_direction((1,2,3), (4,5,6), (1,2,3), (4,5,6))
    assert result["delta"] == (0.0,0.0,0.0)
    assert result["direction"] == (0.0,0.0,0.0)


def test_postload_contract_keeps_transform_helpers_opaque():
    contract = runtime.build_postload_contract()
    assert contract["transform_helpers"] == {"forward":"FUN_007aefb0","inverse":"FUN_007af0a0"}
    assert contract["functions"]["BAR"]["function"] == "FUN_007b2f70"
    assert contract["functions"]["HINGE"]["function"] == "FUN_007b2de0"
