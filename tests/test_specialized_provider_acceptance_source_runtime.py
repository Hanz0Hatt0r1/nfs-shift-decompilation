import specialized_provider_acceptance_source_runtime as runtime
from specialized_provider_runtime import get_provider


FIXTURE = """
uint FUN_a(int param_1,int param_2)
{
  uint local = 0;
  if (param_2 == 3) {
    local_b[0] = 1;
    local_b[1] = 0;
    local_b[2] = 0;
  }
  return 0;
}
void FUN_b(void)
{
}
"""


def test_extract_rle_array_contiguous_fixture():
    body = FIXTURE
    runs = runtime.extract_rle_array(
        body,
        "local_b",
    )
    assert runs == (1, 0, 0)


def test_validate_rle_shape():
    result = runtime.validate_rle_shape((1, 0, 0), 3, expected_count=3)
    assert result["ready"] is True
    assert result["decoded_cells"] == 3


def test_missing_array_index_is_rejected():
    try:
        runtime.extract_rle_array(
            "local_b[0] = 1; local_b[2] = 0;",
            "local_b",
        )
    except ValueError:
        return
    raise AssertionError("expected missing-index error")


def test_conflicting_duplicate_index_is_rejected():
    try:
        runtime.extract_rle_array(
            "local_b[0] = 1; local_b[0] = 0;",
            "local_b",
        )
    except ValueError:
        return
    raise AssertionError("expected duplicate-index error")


def test_provider_spec_matches_static_signature_lengths():
    assert runtime.ACCEPTANCE_SPECS[0]["expected_rle_count"] == 83
    assert runtime.ACCEPTANCE_SPECS[1]["expected_rle_count"] == 107
    assert len(get_provider(0).rle) == 83
    assert len(get_provider(1).rle) == 107
