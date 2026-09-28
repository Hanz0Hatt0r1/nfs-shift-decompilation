from __future__ import annotations

import specialized_provider_capture_source_mutation_runtime as runtime
from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout


def _capture(
    provider_id: int,
    *,
    changed_indices: dict[int, float] | None = None,
    include_row_pointers: bool = True,
):
    layout = get_storage_layout(provider_id)
    workspace = [0.0] * layout.factor_workspace_doubles
    post_workspace = list(workspace)
    for index, value in (changed_indices or {}).items():
        post_workspace[index] = float(value)
    return (
        {
            "provider_id": provider_id,
            "stage": "pre-solve-provider",
            "workspace": workspace,
            "output_vector": [0.0] * layout.output_vector_doubles,
            "row_pointers": (
                list(get_row_pointers(provider_id))
                if include_row_pointers
                else []
            ),
            "frame_index": 7,
        },
        {
            "provider_id": provider_id,
            "stage": "post-solve-provider",
            "workspace": post_workspace,
            "output_vector": [0.0] * layout.output_vector_doubles,
            "row_pointers": (
                list(get_row_pointers(provider_id))
                if include_row_pointers
                else []
            ),
            "frame_index": 7,
        },
    )


def _pattern(provider_id: int, edges):
    return {
        "format": "SHIFT.SpecializedProviderSourcePatternExecutorAdapter/1",
        "provider_id": provider_id,
        "scalar_count": get_storage_layout(provider_id).scalar_count,
        "ready": True,
        "edges": [
            {"pivot_index": pivot, "column": column}
            for pivot, column in edges
        ],
        "errors": [],
    }


def test_correlates_source_edge_to_observed_workspace_address():
    pre, post = _capture(0, changed_indices={1: 3.5})
    result = runtime.build_source_mutation_correlation_contract(
        pre,
        post,
        _pattern(0, [(0, 1)]),
    )

    assert result["ready"] is True
    assert result["status"] == "correlated"
    assert result["coverage"]["observed_addresses_covered"] == 1
    assert result["coverage"]["observed_addresses_uncovered"] == 0
    assert result["observations"][0]["source_edges"] == [
        {"pivot_index": 0, "column": 1}
    ]


def test_preserves_aliases_when_multiple_source_edges_map_to_one_address():
    pointers = get_row_pointers(0)
    alias_address = pointers[0] + 8 * 27
    base = get_storage_layout(0).factor_workspace_base
    assert (alias_address - base) % 8 == 0

    pre, post = _capture(
        0,
        changed_indices={(alias_address - base) // 8: 2.0},
    )
    result = runtime.build_source_mutation_correlation_contract(
        pre,
        post,
        _pattern(0, [(0, 27), (1, 2)]),
    )

    assert result["ready"] is True
    assert result["status"] == "correlated"
    assert result["mapping"]["alias_address_count"] == 1
    assert result["observations"][0]["source_edge_match_count"] == 2
    assert result["observations"][0]["source_edges"] == [
        {"pivot_index": 0, "column": 27},
        {"pivot_index": 1, "column": 2},
    ]


def test_reports_uncovered_workspace_mutations_without_blocking():
    pre, post = _capture(0, changed_indices={10: 1.0})
    result = runtime.build_source_mutation_correlation_contract(
        pre,
        post,
        _pattern(0, [(0, 1)]),
    )

    assert result["ready"] is True
    assert result["status"] == "partial"
    assert result["coverage"]["observed_addresses_covered"] == 0
    assert result["coverage"]["observed_addresses_uncovered"] == 1


def test_blocks_without_row_pointer_provenance():
    pre, post = _capture(
        1,
        changed_indices={1: 1.0},
        include_row_pointers=False,
    )
    result = runtime.build_source_mutation_correlation_contract(
        pre,
        post,
        _pattern(1, [(0, 1)]),
    )

    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert "row-pointer-table-missing" in result["errors"]


def test_blocks_when_source_pattern_is_not_ready():
    pre, post = _capture(0, changed_indices={1: 1.0})
    pattern = _pattern(0, [(0, 1)])
    pattern["ready"] = False

    result = runtime.build_source_mutation_correlation_contract(
        pre,
        post,
        pattern,
    )

    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert "source-pattern-not-ready" in result["errors"]
