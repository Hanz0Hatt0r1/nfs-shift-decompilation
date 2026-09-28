import specialized_provider_acceptance_handoff_runtime as runtime


def test_provider0_handoff_uses_expected_preselection_and_static_storage():
    result = runtime.build_provider_handoff(0)

    assert result["acceptance"]["function"] == "0x7c6e50"
    assert result["acceptance"]["input_rows"] == "physics_system+0x3c"
    assert result["rebind"]["row_pointer"]["destination"] == "physics_system+0x3c"
    assert result["rebind"]["row_pointer"]["static_base"] == "0xc21698"
    assert result["rebind"]["output_vector"]["static_base"] == "0xc23c68"
    assert result["rebind"]["factor_workspace"]["static_base"] == "0xc21738"
    assert result["scalar_count"] == 40


def test_provider1_handoff_uses_expected_static_storage():
    result = runtime.build_provider_handoff(1)

    assert result["acceptance"]["function"] == "0x7cdb40"
    assert result["rebind"]["row_pointer"]["static_base"] == "0xc1fdb0"
    assert result["rebind"]["output_vector"]["static_base"] == "0xc21588"
    assert result["rebind"]["factor_workspace"]["static_base"] == "0xc1fe38"
    assert result["scalar_count"] == 34


def test_handoff_contract_separates_preselection_and_provider_domains():
    result = runtime.build_handoff_boundary_contract()

    assert result["domain_separation"]["acceptance_input"] == (
        "pre-selection physics-system matrix row table"
    )
    assert result["domain_separation"]["provider_factor_workspace"] == (
        "post-selection provider static packed workspace"
    )
    assert result["domain_separation"]["logical_identity"] == (
        "not assumed equal across the two domains"
    )


def test_handoff_sequence_contains_rebind_and_late_provider_solve():
    result = runtime.build_handoff_boundary_contract()

    assert "accepted provider replaces physics-system +0x3c/+0x40/+0x44 bindings through +0x0c/+0x04/+0x08" in result["sequence"]
    assert "later FUN_007b3f40 provider cleanup +0x20 and solve +0x18 operate on fixed provider global storage" in result["sequence"]


def test_validate_handoff_boundary():
    result = runtime.validate_handoff_boundary()

    assert result["ready"] is True
    assert result["errors"] == []
