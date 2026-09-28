import specialized_provider_operator_signature_runtime as runtime


def test_classify_subtract_product():
    statement = (
        "_DAT_00c21808 = _DAT_00c218d0 - "
        "_DAT_00c218c8 * _DAT_00c21748;"
    )
    assert runtime.classify_assignment(statement) == "subtract-product"


def test_classify_subtract_product_then_scale():
    statement = (
        "_DAT_00c23c70 = "
        "(_DAT_00c23c70 - _DAT_00c21800 * _DAT_00c23c68) * dVar1;"
    )
    assert runtime.classify_assignment(statement) == "subtract-product-then-scale"


def test_classify_scale_by_pivot():
    statement = "_DAT_00c23c68 = _DAT_00c23c68 * dVar1;"
    assert runtime.classify_assignment(statement) == "scale-or-product-by-pivot"


def test_classify_simple_product():
    statement = "_DAT_00c23b88 = _DAT_00c23c58 * (1.0 / _DAT_00c23b80);"
    assert runtime.classify_assignment(statement) == "product"


def test_validate_operator_signature_shape():
    report = {
        "provider_id": 0,
        "scalar_count": 2,
        "pivot_summaries": [
            {"pivot_index": 0, "assignment_count": 2, "operator_counts": {"product": 2}},
            {"pivot_index": 1, "assignment_count": 1, "operator_counts": {"subtraction": 1}},
        ],
        "assignments": [
            {"pivot_index": 0, "operator": "product"},
            {"pivot_index": 0, "operator": "product"},
            {"pivot_index": 1, "operator": "subtraction"},
        ],
        "errors": [],
        "ready": True,
    }
    result = runtime.validate_operator_signatures(report)
    assert result["ready"] is True
    assert result["errors"] == []
