from camera_named_target_index_runtime import (
    bootstrap_named_target_indices,
    resolve_named_indices,
)


def test_named_resolution_requires_tracking_rtti():
    result = resolve_named_indices(
        desired_names=["A"],
        candidate_names=["A", "A"],
        candidate_has_tracking_rtti=[False, True],
    )
    assert result["outputs"] == [1]


def test_named_resolution_keeps_previous_index_when_not_found():
    result = resolve_named_indices(
        desired_names=["A", "Missing", "B"],
        candidate_names=["A", "B"],
        candidate_has_tracking_rtti=[True, True],
    )
    assert result["outputs"] == [0, 0, 1]


def test_named_resolution_treats_null_name_as_empty_string():
    result = resolve_named_indices(
        desired_names=[""],
        candidate_names=[None],
        candidate_has_tracking_rtti=[True],
    )
    assert result["outputs"] == [0]


def test_bootstrap_requires_exact_nine_and_twelve_name_slots():
    first_names = [f"f{i}" for i in range(9)]
    second_names = [f"s{i}" for i in range(12)]
    result = bootstrap_named_target_indices(
        first_names=first_names,
        second_names=second_names,
        candidate_names_first=first_names,
        candidate_rtti_first=[True] * 9,
        candidate_names_second=second_names,
        candidate_rtti_second=[True] * 12,
    )
    assert len(result["first_block"]["outputs"]) == 9
    assert len(result["second_block"]["outputs"]) == 12


def test_bootstrap_records_source_function_and_rtti_marker():
    result = bootstrap_named_target_indices(
        first_names=[str(i) for i in range(9)],
        second_names=[str(i) for i in range(12)],
        candidate_names_first=[str(i) for i in range(9)],
        candidate_rtti_first=[True] * 9,
        candidate_names_second=[str(i) for i in range(12)],
        candidate_rtti_second=[True] * 12,
    )
    assert result["evidence"]["function"] == "FUN_00816f50"
    assert result["evidence"]["rtti_type"] == "DAT_00c25fb8"
