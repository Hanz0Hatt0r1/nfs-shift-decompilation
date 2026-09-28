import specialized_provider_contextual_dependency_runtime as runtime


def test_destination_loop_pointer_uses_source_row_context():
    statement = (
        "*(double *)(&DAT_00C21800 + local_10 * 8) = "
        "DAT_00C21900;"
    )
    result = runtime._resolve_destination(
        statement,
        provider_id=0,
        loop_index=3,
    )

    assert result["domain"] == "workspace"
    assert result["form"] == "loop-pointer"
    assert result["row"] == 1
    assert result["column"] == 3
    assert result["unique"] is True
    assert result["resolution_basis"] == "explicit-row-pointer-plus-local-index"


def test_destination_direct_address_preserves_aliases():
    result = runtime._resolve_destination(
        "_DAT_00C21800 = 0.0;",
        provider_id=0,
        loop_index=None,
    )

    assert result["domain"] == "workspace"
    assert result["unique"] is False
    assert result["candidate_count"] == 2


def test_destination_unknown_loop_base_falls_back_to_alias_map():
    result = runtime._resolve_destination(
        "*(double *)(&DAT_00DEAD00 + local_10 * 8) = 0.0;",
        provider_id=0,
        loop_index=0,
    )

    assert result["form"] == "loop-pointer"
    assert result["resolution_basis"] == "absolute-address-fallback"
    assert result["domain"] == "global"


def test_contextual_rhs_keeps_explicit_row_pointer_semantics():
    reference = {
        "domain": "workspace",
        "form": "row-pointer-offset",
        "address": "0x00C21818",
        "row": 1,
        "column": 3,
    }
    result = runtime._contextualize_rhs_reference(
        reference,
        provider_id=0,
    )

    assert result["contextual_unique"] is True
    assert result["contextual_cell"] == {"row": 1, "column": 3}


def test_contextual_rhs_direct_workspace_reference_exposes_aliases():
    reference = {
        "domain": "workspace",
        "form": "direct",
        "address": "0x00C21800",
        "row": 0,
        "column": 25,
    }
    result = runtime._contextualize_rhs_reference(
        reference,
        provider_id=0,
    )

    assert result["alias_unique"] is False
    assert result["alias_candidate_count"] == 2
    assert result["alias_candidates"] == [
        {"row": 0, "column": 25},
        {"row": 1, "column": 0},
    ]


def test_validate_contextual_dependencies_requires_aliases_for_ambiguous_refs():
    result = runtime.validate_contextual_dependencies(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "assignments": [
                {
                    "pivot_index": 0,
                    "destination": {
                        "domain": "workspace",
                        "unique": False,
                        "candidates": [],
                    },
                    "rhs": [],
                }
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert (
        "assignment-0-ambiguous-destination-without-candidates"
        in result["errors"]
    )
