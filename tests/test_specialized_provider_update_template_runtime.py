import specialized_provider_update_template_runtime as runtime


def test_classify_self_subtract_product():
    destination = {
        "domain": "workspace",
        "address": "0x1000",
    }
    rhs = [
        {"domain": "workspace", "address": "0x1000"},
        {"domain": "workspace", "address": "0x1010"},
        {"domain": "workspace", "address": "0x1020"},
    ]

    assert (
        runtime.classify_template(
            destination,
            rhs,
            "subtract-product",
        )
        == "self-subtract-product"
    )


def test_classify_nonself_subtract_product():
    destination = {
        "domain": "workspace",
        "address": "0x1000",
    }
    rhs = [
        {"domain": "workspace", "address": "0x1010"},
        {"domain": "workspace", "address": "0x1020"},
    ]

    assert (
        runtime.classify_template(
            destination,
            rhs,
            "subtract-product",
        )
        == "subtract-product"
    )


def test_classify_self_subtract_product_then_scale():
    destination = {
        "domain": "workspace",
        "address": "0x1000",
    }
    rhs = [
        {"domain": "workspace", "address": "0x1000"},
        {"domain": "workspace", "address": "0x1010"},
        {"domain": "workspace", "address": "0x1020"},
        {"domain": "global", "address": "0x1234"},
    ]

    assert (
        runtime.classify_template(
            destination,
            rhs,
            "subtract-product-then-scale",
        )
        == "self-subtract-product-then-scale"
    )


def test_summarize_update_templates_counts_self_updates():
    report = {
        "provider_id": 0,
        "scalar_count": 2,
        "assignments": [
            {"template": "self-subtract-product"},
            {"template": "subtract-product"},
            {"template": "self-subtract-product-then-scale"},
        ],
        "ready": True,
    }

    summary = runtime.summarize_update_templates(report)

    assert summary["assignments"] == 3
    assert summary["self_update_assignments"] == 2
    assert summary["template_counts"] == {
        "self-subtract-product": 1,
        "self-subtract-product-then-scale": 1,
        "subtract-product": 1,
    }


def test_validate_requires_rhs_for_subtract_templates():
    result = runtime.validate_update_templates(
        {
            "provider_id": 0,
            "scalar_count": 1,
            "assignments": [
                {
                    "pivot_index": 0,
                    "operator": "subtract-product",
                    "template": "subtract-product",
                    "rhs": [],
                    "destination": {},
                }
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "assignment-0-subtract-template-without-rhs" in result["errors"]
