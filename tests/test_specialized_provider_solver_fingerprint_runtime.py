import specialized_provider_solver_fingerprint_runtime as runtime


def test_fixture_extracts_unique_reciprocals_and_loop_ranges():
    report = runtime.build_fixture_fingerprint()
    assert report["ready"] is True
    assert report["unique_reciprocal_count"] == 3
    assert report["pivots"][0]["denominator"] == "_DAT_00001000"
    assert report["pivots"][0]["loop_ranges"] == [{"start": 1, "end": 4}]
    assert report["pivots"][1]["loop_ranges"] == [{"start": 2, "end": 5}]
    assert report["pivots"][2]["loop_ranges"] == []


def test_duplicate_denominators_are_counted_once():
    source = """void FUN_example(void)
{
  double dVar1;
  dVar1 = 1.0 / _DAT_00001000;
  dVar1 = 1.0 / _DAT_00001000;
  dVar1 = 1.0 / _DAT_00001008;
}
"""
    body, start = runtime.extract_function_body(source, "FUN_example")
    pivots = runtime.extract_reciprocal_pivots(body.splitlines(), first_source_line=start)
    assert [p.denominator for p in pivots] == ["_DAT_00001000", "_DAT_00001008"]


def test_expected_scalar_count_is_fail_closed():
    report = runtime.build_provider_source_fingerprint(
        "void FUN_example(void){ double d; d = 1.0 / _DAT_1; }",
        provider_id=0,
        function_name="FUN_example",
        expected_scalar_count=40,
    )
    assert report["ready"] is False
    assert report["errors"] == ["reciprocal-count:expected=40:actual=1"]


def test_function_end_marker_is_required_when_supplied():
    source = "void FUN_a(void){}"
    try:
        runtime.extract_function_body(source, "FUN_a", next_function_marker="void FUN_b")
    except ValueError:
        return
    raise AssertionError("expected missing end marker error")


def test_fixture_keeps_source_line_numbers():
    report = runtime.build_fixture_fingerprint()
    assert report["source_start_line"] == 1
    assert report["pivots"][0]["source_line"] == 4
