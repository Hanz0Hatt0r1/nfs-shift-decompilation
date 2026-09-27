import pytest

import sdf_constraint_projection_runtime as runtime


def test_joint_cross_terms_match_recovered_source_expressions():
    result = runtime.evaluate_joint_cross_terms(
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
    )
    assert result == {
        "d2": 3.0 * 5.0 - 2.0 * 6.0,
        "d3": 6.0 * 1.0 - 3.0 * 4.0,
        "d5": 2.0 * 4.0 - 5.0 * 1.0,
    }


def test_joint_scalar_lanes_preserve_source_order_and_sign():
    result = runtime.build_joint_scalar_lanes(
        d2=-1.0,
        d4=2.0,
        d6=3.0,
        sign=-1,
    )
    assert result["function"] == "FUN_007bac60"
    assert result["lanes"] == [-2.0, -3.0, 1.0]
    assert result["lane_mapping"] == {
        "lane0": "sign*d4",
        "lane1": "sign*d6",
        "lane2": "sign*d2",
    }
    assert result["destination"]["status"] == "opaque"


def test_joint_projection_provenance_explicitly_marks_unresolved_terms():
    report = runtime.describe_joint_projection_provenance()
    assert report["sample_stride"] == 0x40
    assert report["side_flag_offset"] == "+0x34"
    assert report["scalar_base_offset"] == "+0x30"
    assert report["unresolved_terms"] == ["d4", "d6"]
    assert "body +0x158 row-pointer table" in report["destination_layout"]["do_not_alias_to"]


def test_hinge_projection_provenance_preserves_known_branch_boundary():
    report = runtime.describe_hinge_projection_provenance()
    assert report["sample_stride"] == 0xA0
    assert report["scalar_base_offset"] == "+0x94"
    assert report["side_flag_offset"] == "+0x98"
    assert report["branch_rule"]["flag_zero"] == "add transformed velocity terms"
    assert report["branch_rule"]["flag_nonzero"] == (
        "transform through body +0xd4 and subtract transformed terms"
    )


def test_joint_scalar_lane_rejects_invalid_sign():
    with pytest.raises(ValueError, match="sign"):
        runtime.build_joint_scalar_lanes(d2=1, d4=2, d6=3, sign=0)
