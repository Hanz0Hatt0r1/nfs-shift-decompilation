import specialized_provider_solver_program_runtime as runtime


def test_solver_program_validation_requires_all_readiness_gates():
    result = runtime.validate_solver_program(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "readiness": {
                "pivot_geometry": True,
                "execution_blocks": True,
                "update_relations": True,
                "output_schedule": True,
                "acceptance_factor_separation": True,
                "workspace_alias_map": True,
                "source_context": False,
            },
            "evidence": {
                "execution_schedule": {"blocks": [{}, {}]},
                "output_schedule": {
                    "assignments": [
                        {"destination": {"index": 0}},
                        {"destination": {"index": 1}},
                    ]
                },
                "workspace_alias_map": {"scalar_count": 2},
            },
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "readiness-source_context-false" in result["errors"]


def test_solver_program_validation_checks_output_domain():
    result = runtime.validate_solver_program(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "readiness": {
                "pivot_geometry": True,
                "execution_blocks": True,
                "update_relations": True,
                "output_schedule": True,
                "acceptance_factor_separation": True,
                "workspace_alias_map": True,
                "source_context": True,
            },
            "evidence": {
                "execution_schedule": {"blocks": [{}, {}]},
                "output_schedule": {
                    "assignments": [
                        {"destination": {"index": 3}},
                    ]
                },
                "workspace_alias_map": {"scalar_count": 2},
            },
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "output-destination-out-of-domain" in result["errors"]


def test_solver_program_summary_aggregates_nested_summaries():
    report = {
        "provider_id": 1,
        "scalar_count": 34,
        "evidence": {
            "update_relations": {
                "summary": {
                    "relations": 100,
                    "self_update_relations": 20,
                }
            },
            "output_schedule": {
                "summary": {
                    "output_assignment_count": 73,
                    "output_dependency_edge_count": 50,
                }
            },
            "workspace_alias_map": {
                "summary": {
                    "unique_storage_addresses": 746,
                    "collision_address_count": 401,
                }
            },
        },
        "ready": True,
    }

    summary = runtime.summarize_solver_program(report)

    assert summary["update_relations"] == 100
    assert summary["self_update_relations"] == 20
    assert summary["output_assignments"] == 73
    assert summary["output_dependency_edges"] == 50
    assert summary["workspace_alias_addresses"] == 746
    assert summary["workspace_alias_collisions"] == 401


def test_solver_program_validation_rejects_alias_domain_mismatch():
    result = runtime.validate_solver_program(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "readiness": {
                "pivot_geometry": True,
                "execution_blocks": True,
                "update_relations": True,
                "output_schedule": True,
                "acceptance_factor_separation": True,
                "workspace_alias_map": True,
                "source_context": True,
            },
            "evidence": {
                "execution_schedule": {
                    "blocks": [{}] * 40,
                },
                "output_schedule": {
                    "assignments": [],
                },
                "workspace_alias_map": {
                    "scalar_count": 34,
                },
            },
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "alias-map-scalar-count-mismatch" in result["errors"]
