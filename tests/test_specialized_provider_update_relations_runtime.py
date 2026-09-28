import specialized_provider_update_relations_runtime as runtime


def test_relation_kind_self_update():
    destination = {"domain": "workspace", "address": "0x1000"}
    rhs = [
        {"domain": "workspace", "address": "0x1000"},
        {"domain": "workspace", "address": "0x1010"},
        {"domain": "workspace", "address": "0x1020"},
    ]

    assert runtime._relation_kind(
        destination,
        rhs,
        "subtract-product",
    ) == "self-update"


def test_relation_kind_normalized_factor():
    destination = {"domain": "workspace", "address": "0x1008"}
    rhs = [{"domain": "workspace", "address": "0x1020"}]

    assert runtime._relation_kind(
        destination,
        rhs,
        "scale-or-product-by-pivot",
    ) == "normalized-factor"


def test_build_relation_exposes_factor_source():
    assignment = {
        "pivot_index": 2,
        "source_line": 123,
        "loop_index": 7,
        "destination": {"domain": "workspace", "address": "0x1000"},
        "rhs": [{"domain": "workspace", "address": "0x1010"}],
    }

    relation = runtime._build_relation(
        assignment,
        "scale-or-product-by-pivot",
    )

    assert relation["kind"] == "normalized-factor"
    assert relation["factor_source"]["address"] == "0x1010"
    assert relation["factor_source_count"] == 1


def test_build_relation_exposes_self_update_terms():
    assignment = {
        "pivot_index": 1,
        "source_line": 50,
        "loop_index": None,
        "destination": {"domain": "workspace", "address": "0x2000"},
        "rhs": [
            {"domain": "workspace", "address": "0x2000"},
            {"domain": "workspace", "address": "0x2010"},
            {"domain": "workspace", "address": "0x2020"},
        ],
    }

    relation = runtime._build_relation(
        assignment,
        "subtract-product",
    )

    assert relation["kind"] == "self-update"
    assert relation["self_reference"]["address"] == "0x2000"
    assert [item["address"] for item in relation["update_terms"]] == [
        "0x2010",
        "0x2020",
    ]


def test_validate_rejects_factor_without_workspace_source():
    result = runtime.validate_update_relations(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "relations": [
                {
                    "pivot_index": 0,
                    "kind": "normalized-factor",
                    "factor_source_count": 0,
                    "destination": {},
                }
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "relation-0-factor-without-workspace-source" in result["errors"]


def test_summarize_relation_counts():
    result = runtime.summarize_update_relations(
        {
            "provider_id": 0,
            "scalar_count": 3,
            "relations": [
                {"kind": "normalized-factor", "factor_source_count": 1},
                {"kind": "self-update"},
                {"kind": "subtractive-update"},
                {"kind": "self-update-then-scale"},
            ],
            "ready": True,
        }
    )

    assert result["relations"] == 4
    assert result["relation_counts"] == {
        "normalized-factor": 1,
        "self-update": 1,
        "self-update-then-scale": 1,
        "subtractive-update": 1,
    }
    assert result["single-source-factor_relations"] == 1
    assert result["self_update_relations"] == 2
