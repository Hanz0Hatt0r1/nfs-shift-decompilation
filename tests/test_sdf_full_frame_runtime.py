import sdf_full_frame_runtime as runtime


RECORDS = [
    {"record_index": 0, "scalar_base": 0, "width": 3},
    {"record_index": 1, "scalar_base": 3, "width": 2},
    {"record_index": 2, "scalar_base": 5, "width": 1},
]


def test_full_frame_contract_contains_all_solver_lifecycle_stages():
    report = runtime.describe_full_frame_contract(
        solver_scalar_count=6,
        body_count=3,
        runtime_flags_available=False,
    )
    assert report["format"] == "SHIFT.SDFFullFrameRuntime/1"
    assert report["ready"] is True
    assert [stage for stage in report["lifecycle"]] == [
        "FUN_007b3f40 frame entry",
        "FUN_007b3ed0 constraint refresh",
        "FUN_007bb8d0 per-body reset",
        "FUN_007bc680 contribution build",
        "FUN_007ba570 global vector/matrix export",
        "FUN_007b2210 selected identity rows/columns",
        "provider vtable +0x18 or FUN_007b0f20 solve",
        "FUN_007b4110 solved-vector body application",
    ]
    assert report["static_stages"]["seed"]["function"] == "FUN_007ba2b0"
    assert report["static_stages"]["coupling"]["JOINT"] == "FUN_007bbb80"
    assert report["static_stages"]["coupling"]["HINGE"] == "FUN_007bb250"
    assert report["static_stages"]["coupling"]["BAR"] == "FUN_007bb6c0"


def test_runtime_frame_plan_marks_identity_selector_capture_dependent():
    result = runtime.build_runtime_frame_plan(
        solver_scalar_count=6,
        body_count=3,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record=None,
    )
    assert result["ready"] is True
    assert result["format"] == "SHIFT.SDFRuntimeFramePlan/2"
    assert result["version"] == 2
    assert result["verification"]["ready"] is True
    assert result["scalar_domain_verification"]["ready"] is True
    assert result["runtime_flags_available"] is False
    assert result["identity_selector"]["status"] == "needs-runtime-flags"
    assert result["stages"][3]["runtime_dependent"] is True
    assert result["stages"][3]["ready"] is False


def test_runtime_frame_plan_maps_low_bit_flag_to_exact_scalar_range():
    result = runtime.build_runtime_frame_plan(
        solver_scalar_count=6,
        body_count=3,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record={0: 0, 1: 1, 2: 0},
    )
    assert result["runtime_flags_available"] is True
    assert result["identity_selector"]["scalar_nodes"] == [3, 4]
    assert result["identity_selector"]["selected_records"] == [
        {
            "record_index": 1,
            "base_index": 3,
            "width": 2,
            "nodes": [3, 4],
            "runtime_flag": 1,
        }
    ]
    assert result["stages"][3]["ready"] is True


def test_runtime_frame_plan_requires_record_ranges_for_selector_mapping():
    result = runtime.build_runtime_frame_plan(
        solver_scalar_count=40,
        body_count=11,
        runtime_flags_by_record={0: 1},
    )
    assert result["identity_selector"]["ready"] is False
    assert result["identity_selector"]["status"] == "needs-runtime-record-domains"
