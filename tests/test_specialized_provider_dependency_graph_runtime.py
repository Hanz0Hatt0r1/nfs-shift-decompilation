import specialized_provider_dependency_graph_runtime as runtime


def test_classify_workspace_relations():
    destination = {"domain": "workspace", "row": 5, "column": 4}
    assert runtime._classify_relation(3, destination, {"domain": "workspace", "row": 2, "column": 1}) == "prior-pivot"
    assert runtime._classify_relation(3, destination, {"domain": "workspace", "row": 3, "column": 2}) == "current-pivot"
    assert runtime._classify_relation(3, destination, {"domain": "workspace", "row": 5, "column": 2}) == "destination-row"
    assert runtime._classify_relation(3, destination, {"domain": "workspace", "row": 6, "column": 2}) == "future-pivot"


def test_classify_non_workspace_domains():
    destination = {"domain": "workspace", "row": 5, "column": 4}
    assert runtime._classify_relation(3, destination, {"domain": "output_vector", "index": 2}) == "output_vector"
    assert runtime._classify_relation(3, destination, {"domain": "global", "address": "0x1234"}) == "global"


def test_node_key_distinguishes_workspace_output_and_global():
    assert runtime._node_key({"domain": "workspace", "row": 2, "column": 4}) == ("workspace", 2, 4)
    assert runtime._node_key({"domain": "output_vector", "index": 4}) == ("output_vector", 4)
    assert runtime._node_key({"domain": "global", "address": "0x1234"}) == ("global", "0x1234")


def test_summarize_dependency_graph_counts_unique_edges_and_reads():
    report = {
        "provider_id": 0,
        "scalar_count": 3,
        "nodes": [
            {
                "pivot_index": 0,
                "output_reads": [],
                "global_reads": [{"domain": "global"}],
            },
            {
                "pivot_index": 2,
                "output_reads": [{"domain": "output_vector"}, {"domain": "output_vector"}],
                "global_reads": [],
            },
        ],
        "edges": [
            {"relation": "current-pivot"},
            {"relation": "future-pivot"},
            {"relation": "future-pivot"},
        ],
        "pivot_summaries": [{}, {}, {}],
        "ready": True,
    }
    summary = runtime.summarize_dependency_graph(report)

    assert summary["assignment_nodes"] == 2
    assert summary["unique_workspace_edges"] == 3
    assert summary["edges_by_relation"] == {
        "current-pivot": 1,
        "future-pivot": 2,
    }
    assert summary["output_read_occurrences"] == 2
    assert summary["global_read_occurrences"] == 1
    assert summary["pivots"] == 3


def test_validation_rejects_workspace_reference_without_coordinates():
    result = runtime.validate_dependency_graph(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "nodes": [
                {
                    "pivot_index": 0,
                    "destination": {
                        "domain": "workspace",
                        "row": 0,
                        "column": 0,
                    },
                    "workspace_reads": [{"domain": "workspace"}],
                    "output_reads": [],
                    "global_reads": [],
                },
                {
                    "pivot_index": 1,
                    "destination": {"domain": "output_vector", "index": 0},
                    "workspace_reads": [],
                    "output_reads": [],
                    "global_reads": [],
                },
            ],
            "edges": [],
            "pivot_summaries": [{}, {}],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "pivot-0-workspace-read-row-out-of-range" in result["errors"]
