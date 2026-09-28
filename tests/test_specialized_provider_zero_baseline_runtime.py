import specialized_provider_zero_baseline_runtime as runtime


FIXTURE = """
void FUN_test(void)
{
  DAT_00001000 = 0;
  FUN_0040cec0(&DAT_00001010,0,0x18);
  FUN_0040cec0(&DAT_00001028,0,0x08);
  DAT_00001030 = 0;
}
"""


def test_interval_coverage_merges_overlaps():
    merged, covered = runtime._interval_coverage(
        [
            (0x1000, 0x20),
            (0x1010, 0x10),
        ],
        start=0x1000,
        end=0x1040,
    )

    assert merged == [(0x1000, 0x1030)]
    assert covered == 0x30


def test_coverage_for_region_adds_aligned_direct_zero_slots():
    result = runtime._coverage_for_region(
        [(0x1000, 0x08)],
        [0x1010],
        start=0x1000,
        end=0x1020,
    )

    assert result["bulk_covered_doubles"] == 1
    assert result["direct_zero_slot_count"] == 1
    assert result["covered_doubles"] == 2
    assert result["uncovered_doubles"] == 2


def test_validate_zero_baseline_requires_complete_output_vector():
    result = runtime.validate_zero_baseline(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "workspace": {
                "doubles": 4,
                "covered_doubles": 2,
                "uncovered_doubles": 2,
            },
            "output_vector": {
                "doubles": 2,
                "covered_doubles": 1,
                "uncovered_doubles": 1,
            },
            "row_coverage": [{}, {}],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "output-vector-baseline-incomplete" in result["errors"]


def test_validate_zero_baseline_accepts_complete_output_vector():
    result = runtime.validate_zero_baseline(
        {
            "provider_id": 1,
            "scalar_count": 2,
            "workspace": {
                "doubles": 4,
                "covered_doubles": 2,
                "uncovered_doubles": 2,
            },
            "output_vector": {
                "doubles": 2,
                "covered_doubles": 2,
                "uncovered_doubles": 0,
            },
            "row_coverage": [{}, {}],
            "errors": [],
        }
    )

    assert result["ready"] is True


def test_summarize_zero_baseline():
    result = runtime.summarize_zero_baseline(
        {
            "provider_id": 0,
            "cleanup_function": "FUN_007d43c0",
            "scalar_count": 40,
            "bulk_clear_count": 51,
            "direct_zero_assignment_count": 57,
            "workspace": {
                "covered_doubles": 370,
                "doubles": 1190,
                "uncovered_doubles": 820,
                "coverage_ratio": 370 / 1190,
            },
            "output_vector": {
                "covered_doubles": 40,
                "doubles": 40,
                "coverage_ratio": 1.0,
            },
            "ready": True,
        }
    )

    assert result["workspace_covered_doubles"] == 370
    assert result["workspace_uncovered_doubles"] == 820
    assert result["output_covered_doubles"] == 40
    assert result["output_coverage_ratio"] == 1.0
