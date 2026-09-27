import pytest

from rigid_body_sdf_runtime import parse_sdf
import bmw_m3_e36_solver_domain_runtime as runtime


def _build_real_shape_sdf() -> str:
    lines = []
    bodies = [
        "body",
        "fl_spindle", "fr_spindle", "fl_wheel", "fr_wheel",
        "rl_spindle", "rr_spindle", "rl_wheel", "rr_wheel",
        "fuel_tank", "driver_head",
    ]
    for name in bodies:
        lines.append(
            f"[BODY]\\nname={name} mass=(1.0) inertia=(1.0,1.0,1.0) "
            "pos=(0,0,0) ori=(0,0,0)"
        )
    wheel_pairs = [
        ("fl_wheel", "fl_spindle", -1.0),
        ("fr_wheel", "fr_spindle", 1.0),
        ("rl_wheel", "rl_spindle", -1.0),
        ("rr_wheel", "rr_spindle", 1.0),
    ]
    for posbody, negbody, axis in wheel_pairs:
        lines.append(
            "[JOINT&HINGE]\\n"
            f"posbody={posbody} negbody={negbody} pos={posbody} "
            f"axis=({axis},0,0)"
        )
    bar_targets = [
        "fl_spindle", "fl_spindle", "fl_spindle", "fl_spindle", "fl_spindle",
        "fr_spindle", "fr_spindle", "fr_spindle", "fr_spindle", "fr_spindle",
        "rl_spindle", "rl_spindle", "rl_spindle", "rl_spindle", "rl_spindle",
        "rr_spindle", "rr_spindle", "rr_spindle", "rr_spindle", "rr_spindle",
    ]
    for index, target in enumerate(bar_targets):
        lines.append(
            "[BAR]\\n"
            f"name=bar_{index} posbody=body negbody={target} "
            "pos=(0,0,0) neg=(1,0,0)"
        )
    return "\\n".join(lines)


def test_real_bmw_shape_maps_to_28_constraint_records_and_40_scalars():
    report = parse_sdf(_build_real_shape_sdf())
    solver = runtime.build_solver_domain(report)
    assert solver["ready"] is True
    assert solver["constraint_record_count"] == 28
    assert solver["solver_scalar_count"] == 40
    assert solver["constraint_width_counts"] == {
        "JOINT": 4,
        "HINGE": 4,
        "BAR": 20,
    }


def test_real_bmw_shape_has_contiguous_scalar_ranges():
    report = parse_sdf(_build_real_shape_sdf())
    solver = runtime.build_solver_domain(report)
    ranges = [(row["scalar_base"], row["scalar_end"]) for row in solver["records"]]
    assert ranges[0] == (0, 3)
    assert ranges[-1][1] == 40
    for current, nxt in zip(ranges, ranges[1:]):
        assert current[1] == nxt[0]


def test_real_bmw_ordering_matches_retail_constraint_heuristic_shape():
    report = parse_sdf(_build_real_shape_sdf())
    solver = runtime.build_solver_domain(report)
    assert solver["ordering"]["initial_cost"] == 17516
    assert solver["ordering"]["final_cost"] == 17296
    assert solver["ordering"]["improvement_count"] == 2
    assert solver["ordering"]["pass_count"] == 2
    assert solver["order"][-4:] == [25, 24, 27, 26]


def test_real_bmw_shape_validation_is_explicit():
    report = parse_sdf(_build_real_shape_sdf())
    solver = runtime.build_solver_domain(report)
    validation = runtime.validate_expected_bmw_shape(
        solver,
        body_count=11,
        joint_hinge_count=4,
        bar_count=20,
    )
    assert validation["ready"] is True
    assert validation["expected_constraint_record_count"] == 28
    assert validation["expected_solver_scalar_count"] == 40
    assert validation["errors"] == []


def test_solver_domain_blocks_when_topology_cannot_resolve_body_reference():
    report = parse_sdf(
        "[BODY]\\nname=body mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\\n"
        "[BAR]\\nname=x posbody=body negbody=missing pos=(0,0,0) neg=(1,0,0)"
    )
    solver = runtime.build_solver_domain(report)
    assert solver["ready"] is False
    assert any("negbody:missing" in reason for reason in solver["unresolved"])
