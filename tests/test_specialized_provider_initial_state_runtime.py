import specialized_provider_initial_state_runtime as runtime


def test_address_converts_to_int():
    assert runtime._address({"address": "0x1000"}) == 0x1000
    assert runtime._address({"domain": "global"}) is None


def test_validate_initial_state_accepts_read_before_write_events():
    result = runtime.validate_initial_state(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "events": [
                {
                    "pivot_index": 0,
                    "source_line": 10,
                    "rhs_reads": [
                        {"domain": "workspace", "address": "0x1000", "availability": "preexisting-or-external"}
                    ],
                },
                {
                    "pivot_index": 1,
                    "source_line": 20,
                    "rhs_reads": [
                        {"domain": "workspace", "address": "0x1000", "availability": "previously-written"}
                    ],
                },
            ],
            "first_read_addresses": [
                {
                    "domain": "workspace",
                    "address": "0x1000",
                    "first_pivot": 0,
                    "first_source_line": 10,
                }
            ],
            "errors": [],
        }
    )

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_initial_state_rejects_unknown_rhs_address():
    result = runtime.validate_initial_state(
        {
            "provider_id": 0,
            "scalar_count": 1,
            "events": [
                {
                    "pivot_index": 0,
                    "source_line": 10,
                    "rhs_reads": [
                        {"domain": "workspace", "availability": "unknown-address"}
                    ],
                }
            ],
            "first_read_addresses": [],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "event-10-unknown-rhs-address" in result["errors"]


def test_summarize_initial_state_counts_domains():
    result = runtime.summarize_initial_state(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "assignment_count": 10,
            "first_read_addresses": [
                {"domain": "workspace", "address": "0x1"},
                {"domain": "output_vector", "address": "0x2"},
                {"domain": "global", "address": "0x3"},
            ],
            "initial_state": {
                "workspace_addresses": [{"address": "0x1"}],
                "output_vector_addresses": [{"address": "0x2"}],
                "global_addresses": [{"address": "0x3"}],
            },
            "ready": True,
        }
    )

    assert result["assignments"] == 10
    assert result["first_read_addresses"] == 3
    assert result["workspace_preexisting_or_external"] == 1
    assert result["output_preexisting_or_external"] == 1
    assert result["global_preexisting_or_external"] == 1
