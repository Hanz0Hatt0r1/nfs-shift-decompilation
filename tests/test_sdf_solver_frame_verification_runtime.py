import sdf_full_frame_runtime as frame
import sdf_solver_frame_verification_runtime as verifier


RECORDS = [
    {"record_index": 0, "scalar_base": 0, "width": 3},
    {"record_index": 1, "scalar_base": 3, "width": 2},
    {"record_index": 2, "scalar_base": 5, "width": 1},
]


def test_scalar_domain_verifier_accepts_contiguous_non_overlapping_ranges():
    result = verifier.verify_solver_scalar_domain(
        solver_scalar_count=6,
        runtime_record_domains=RECORDS,
    )
    assert result["ready"] is True
    assert result["covered_scalar_count"] == 6
    assert result["errors"] == []


def test_scalar_domain_verifier_blocks_overlap_and_gap():
    result = verifier.verify_solver_scalar_domain(
        solver_scalar_count=6,
        runtime_record_domains=[
            {"record_index": 0, "scalar_base": 0, "width": 3},
            {"record_index": 1, "scalar_base": 2, "width": 2},
        ],
    )
    assert result["ready"] is False
    assert any(error.startswith("record:1:overlapping-node") for error in result["errors"])
    assert any(error.startswith("coverage:") for error in result["errors"])


def test_identity_reset_verifier_accepts_no_selected_nodes():
    result = verifier.verify_identity_reset_selection(
        solver_scalar_count=6,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record={0: 0, 1: 0, 2: 0},
    )
    assert result["ready"] is True
    assert result["selected_records"] == []
    assert result["selected_scalar_nodes"] == []


def test_identity_reset_verifier_maps_flagged_record_to_full_scalar_width():
    result = verifier.verify_identity_reset_selection(
        solver_scalar_count=6,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record={0: 0, 1: 1, 2: 0},
    )
    assert result["ready"] is True
    assert result["selected_records"] == [1]
    assert result["selected_scalar_nodes"] == [3, 4]


def test_frame_verifier_accepts_static_full_frame_plan():
    plan = frame.build_runtime_frame_plan(
        solver_scalar_count=6,
        body_count=3,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record={0: 0, 1: 1, 2: 0},
    )
    result = verifier.verify_frame_plan(plan)
    assert result["ready"] is True
    assert result["errors"] == []


def test_frame_verifier_blocks_wrong_stage_order():
    plan = frame.build_runtime_frame_plan(
        solver_scalar_count=6,
        body_count=3,
        runtime_record_domains=RECORDS,
        runtime_flags_by_record={0: 0, 1: 1, 2: 0},
    )
    plan["contract"]["lifecycle"] = list(reversed(plan["contract"]["lifecycle"]))
    result = verifier.verify_frame_plan(plan)
    assert result["ready"] is False
    assert "lifecycle-mismatch" in result["errors"]


def test_verifier_contract_is_source_backed_and_structural():
    result = verifier.describe_solver_frame_verification_contract()
    assert result["ready"] is True
    assert result["scope"] == "structural frame verification before numerical execution"
