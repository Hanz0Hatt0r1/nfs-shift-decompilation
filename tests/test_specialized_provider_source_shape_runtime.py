import specialized_provider_source_shape_runtime as runtime


def test_source_shape_summary_counts_loop_families():
    report = {
        "provider_id": 0,
        "scalar_count": 40,
        "pivot_count": 40,
        "loop_family_counts": [
            {"start": 1, "end": 4, "count": 12},
            {"start": 2, "end": 5, "count": 8},
        ],
        "ready": True,
    }

    summary = runtime.summarize_source_shape(report)

    assert summary == {
        "provider_id": 0,
        "scalar_count": 40,
        "pivot_count": 40,
        "unique_loop_families": 2,
        "loop_headers_total": 20,
        "ready": True,
    }


def test_source_shape_validation_rejects_duplicate_denominators():
    report = {
        "provider_id": 1,
        "scalar_count": 34,
        "pivot_count": 34,
        "pivot_denominators": ["_DAT_A"] * 34,
        "loop_family_counts": [],
        "errors": [],
    }

    result = runtime.validate_source_shape(report)

    assert result["ready"] is False
    assert "pivot-denominators-not-unique" in result["errors"]


def test_build_source_shape_uses_fingerprint_parser(monkeypatch):
    class Pivot:
        def __init__(self, index, denominator, loop_ranges):
            self.index = index
            self.denominator = denominator
            self.loop_ranges = tuple(loop_ranges)

    pivots = tuple(
        Pivot(index, f"_DAT_{index:04X}", ((0, 4),) if index % 2 == 0 else ())
        for index in range(40)
    )

    monkeypatch.setattr(
        runtime,
        "extract_function_body",
        lambda source, function_name, next_function_marker: ("body", 123),
    )
    monkeypatch.setattr(
        runtime,
        "extract_reciprocal_pivots",
        lambda lines, first_source_line: pivots,
    )

    result = runtime.build_source_shape("source", provider_id=0)

    assert result["ready"] is True
    assert result["pivot_count"] == 40
    assert result["scalar_count"] == 40
    assert result["pivot_denominators"][0] == "_DAT_0000"
    assert result["loop_family_counts"] == [
        {"start": 0, "end": 4, "count": 20}
    ]


def test_build_source_shape_rejects_unknown_provider():
    try:
        runtime.build_source_shape("source", provider_id=99)
    except ValueError as exc:
        assert "unsupported provider id" in str(exc)
    else:
        raise AssertionError("unknown provider id must fail closed")
