import specialized_provider_input_footprint_runtime as runtime


def test_summarize_input_footprint():
    result = runtime.summarize_input_footprint(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "first_read_count": 100,
            "workspace_first_reads": [{}] * 70,
            "reset_workspace_first_reads": [{}] * 40,
            "caller_input_candidates": [{}] * 30,
            "output_first_reads": [{}] * 2,
            "global_first_reads": [{}] * 28,
            "malformed_first_reads": [],
            "ready": True,
        }
    )

    assert result["first_read_count"] == 100
    assert result["workspace_first_reads"] == 70
    assert result["reset_workspace_first_reads"] == 40
    assert result["caller_input_candidates"] == 30
    assert result["output_first_reads"] == 2
    assert result["global_first_reads"] == 28


def test_validate_input_footprint_accepts_well_classified_candidates():
    result = runtime.validate_input_footprint(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "caller_input_candidates": [
                {
                    "domain": "workspace",
                    "initialization": "outside-reset-domain",
                    "address": "0x00c21748",
                }
            ],
            "reset_workspace_first_reads": [
                {
                    "domain": "workspace",
                    "initialization": "reset-zero",
                    "address": "0x00c21738",
                },
                {
                    "domain": "workspace",
                    "initialization": "reset-unit",
                    "address": "0x00c21738",
                },
            ],
            "output_first_reads": [
                {
                    "initialization": "reset-zero",
                    "address": "0x00c23c68",
                }
            ],
            "malformed_first_reads": [],
            "reset_unit_diagonal_slots": 40,
            "errors": [],
        }
    )

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_input_footprint_rejects_malformed_first_reads():
    result = runtime.validate_input_footprint(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "caller_input_candidates": [],
            "reset_workspace_first_reads": [],
            "output_first_reads": [],
            "malformed_first_reads": [
                {"domain": "workspace"},
            ],
            "reset_unit_diagonal_slots": 34,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "malformed-first-read-present" in result["errors"]


def test_validate_input_footprint_rejects_wrong_caller_candidate_domain():
    result = runtime.validate_input_footprint(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "caller_input_candidates": [
                {
                    "domain": "global",
                    "initialization": "outside-reset-domain",
                    "address": "0x00c21748",
                }
            ],
            "reset_workspace_first_reads": [],
            "output_first_reads": [],
            "malformed_first_reads": [],
            "reset_unit_diagonal_slots": 40,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert (
        "caller-candidate-0-classification-invalid"
        in result["errors"]
    )


def test_validate_input_footprint_accepts_reset_unit_in_reset_domain():
    result = runtime.validate_input_footprint(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "caller_input_candidates": [],
            "reset_workspace_first_reads": [
                {
                    "domain": "workspace",
                    "initialization": "reset-unit",
                    "address": "0x00c1fe38",
                }
            ],
            "output_first_reads": [],
            "malformed_first_reads": [],
            "reset_unit_diagonal_slots": 34,
            "errors": [],
        }
    )

    assert result["ready"] is True
