import sdf_constraint_solver_runtime as solver


def test_sparse_solver_contract_matches_retail_traversal():
    contract = solver.describe_sdf_sparse_solver_contract(constraint_count=5)
    assert contract["ready"] is True
    assert contract["function"] == "FUN_007b0f20"
    assert contract["graph_outer_record"]["forward_count"] == "n+1"
    assert contract["graph_outer_record"]["reverse_count"] == "n"
    assert contract["edge_record"]["size"] == 8
    assert contract["edge_record"]["layout"]["node"] == "+0x00 byte"
    assert contract["forward_pass"]["diagonal_scale"] == "1.0 / row_i[i]"
    assert contract["backward_pass"]["range"] == "i = n-2 .. 0"
    assert contract["backward_pass"]["terminal_reverse_node"] == (
        "n-1 record is allocated but not traversed by the back-substitution loop"
    )


def test_sparse_solver_validation_accepts_phase_386_graph_shape():
    graph = {
        "constraint_count": 2,
        "forward_records": [
            {"count": 1, "items": [{"node": 0, "dependency_count": 0, "dependencies": []}]},
            {"count": 1, "items": [{"node": 1, "dependency_count": 1, "dependencies": [0]}]},
            {"count": 2, "items": [
                {"node": 0, "dependency_count": 0, "dependencies": []},
                {"node": 1, "dependency_count": 1, "dependencies": [0]},
            ]},
        ],
        "reverse_records": [
            {"node": 1, "dependency_count": 0, "dependencies": []},
            {"node": 0, "dependency_count": 1, "dependencies": [1]},
        ],
    }
    report = solver.validate_sdf_solver_contract(graph)
    assert report["ready"] is True
    assert report["errors"] == []


def test_sparse_solver_validation_rejects_wrong_forward_cardinality():
    report = solver.validate_sdf_solver_contract({
        "constraint_count": 2,
        "forward_records": [],
        "reverse_records": [],
    })
    assert report["ready"] is False
    assert "forward-record-count:0:3" in report["errors"]


def test_sparse_solver_public_wrapper_delegates_to_builtin_numeric_kernel():
    import sdf_builtin_sparse_solver_runtime as builtin
    matrix = [[2.0, 1.0], [1.0, 3.0]]
    rhs = [5.0, 7.0]
    forward, reverse = builtin.build_dense_solver_graph(2)
    result = solver.solve_sdf_builtin(matrix, rhs, forward, reverse)
    assert result["solution"] == [1.6, 1.8]
