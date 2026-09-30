from tools.audit_imb_material_parity import (
    FORMAT,
    summarize_material_rows,
)


def test_material_reference_parity_requires_unique_same_archive_match():
    report = summarize_material_rows([
        {
            "archive": "A.bff",
            "imb_path": "a.imb",
            "primitive_index": 0,
            "expected_bmt": "tracks/a.bmt",
            "same_archive_match_count": 1,
            "same_archive_match": {"type": 2},
            "ready": True,
            "blocking_reasons": [],
        },
        {
            "archive": "B.bff",
            "imb_path": "b.imb",
            "primitive_index": 0,
            "expected_bmt": "tracks/a.bmt",
            "same_archive_match_count": 1,
            "same_archive_match": {"type": 2},
            "ready": True,
            "blocking_reasons": [],
        },
    ])

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["primitive_reference_count"] == 2
    assert report["matched_primitive_reference_count"] == 2
    assert report["unique_bmt_reference_count"] == 1
    assert report["ready_unique_bmt_reference_count"] == 1
    assert report["same_archive_unique_match_count"] == 2
    assert report["same_archive_match_type_counts"] == {"2": 2}


def test_material_reference_parity_preserves_missing_and_ambiguous_blockers():
    report = summarize_material_rows([
        {
            "expected_bmt": "tracks/missing.bmt",
            "same_archive_match_count": 0,
            "ready": False,
            "blocking_reasons": ["same-archive-bmt-missing"],
        },
        {
            "expected_bmt": "tracks/duplicate.bmt",
            "same_archive_match_count": 2,
            "ready": False,
            "blocking_reasons": ["same-archive-bmt-ambiguous:2"],
        },
    ])

    assert report["ready"] is False
    assert report["status"] == "partial"
    assert report["blocked_primitive_reference_count"] == 2
    assert report["ready_unique_bmt_reference_count"] == 0
    assert report["blocking_reason_counts"] == {
        "same-archive-bmt-ambiguous:2": 1,
        "same-archive-bmt-missing": 1,
    }


def test_empty_material_reference_set_is_explicitly_empty():
    report = summarize_material_rows([])
    assert report["status"] == "empty"
    assert report["ready"] is False
    assert report["primitive_reference_count"] == 0
