import specialized_provider_reset_profile_runtime as runtime


def test_case_blocks_parse_hex_and_decimal_cases():
    block = """
void FUN_test(undefined4 param_1)
{
  switch(param_1) {
  case 0:
    DAT_00001000 = 0x3ff0000000000000;
    DAT_00001008 = 0;
    break;
  case 1:
    DAT_00001008 = 0x3ff0000000000000;
  }
  return;
}



"""
    cases = runtime._case_blocks(block)

    assert [case for case, _ in cases] == [0, 1]
    assert "DAT_00001000 = 0x3ff0000000000000;" in cases[0][1]


def test_validate_reset_profile_requires_one_row_per_scalar():
    result = runtime.validate_reset_profile(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "rows": [
                {"pivot_index": 0, "diagonal_address": "0x1000"},
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "row-count:expected=2:actual=1" in result["errors"]
    assert "pivot-case-order-mismatch" in result["errors"]


def test_validate_reset_profile_accepts_sequential_unit_diagonals():
    result = runtime.validate_reset_profile(
        {
            "provider_id": 1,
            "scalar_count": 2,
            "rows": [
                {"pivot_index": 0, "diagonal_address": "0x1000"},
                {"pivot_index": 1, "diagonal_address": "0x1010"},
            ],
            "errors": [],
        }
    )

    assert result["ready"] is True


def test_summarize_reset_profile():
    result = runtime.summarize_reset_profile(
        {
            "provider_id": 0,
            "reset_function": "FUN_007d3150",
            "scalar_count": 3,
            "rows": [
                {
                    "pivot_index": 0,
                    "diagonal_address": "0x1000",
                    "zero_assignment_count": 10,
                    "bulk_clear_count": 0,
                },
                {
                    "pivot_index": 1,
                    "diagonal_address": "0x1010",
                    "zero_assignment_count": 8,
                    "bulk_clear_count": 1,
                },
                {
                    "pivot_index": 2,
                    "diagonal_address": "0x1020",
                    "zero_assignment_count": 7,
                    "bulk_clear_count": 2,
                },
            ],
            "ready": True,
        }
    )

    assert result["cases"] == 3
    assert result["unit_diagonal_cases"] == 3
    assert result["zero_assignment_count"] == 25
    assert result["bulk_clear_count"] == 3
