import specialized_provider_runtime_selection_runtime as runtime


def test_validate_runtime_selection_rejects_out_of_domain_observation():
    report = {
        "validation": {
            "dispatch": {"ready": True},
            "execution": {"ready": True},
            "selector": {"ready": True},
            "source_shape": {"ready": True},
        }
    }

    result = runtime.validate_runtime_selection(
        report,
        observed_provider_id=2,
    )

    assert result["ready"] is False
    assert "observed-provider-out-of-domain:2" in result["errors"]


def test_validate_runtime_selection_accepts_observed_provider():
    report = {
        "validation": {
            "dispatch": {"ready": True},
            "execution": {"ready": True},
            "selector": {"ready": True},
            "source_shape": {"ready": True},
        }
    }

    result = runtime.validate_runtime_selection(
        report,
        observed_provider_id=1,
    )

    assert result["ready"] is True
    assert result["observed_provider_id"] == 1


def test_validate_runtime_selection_propagates_unready_layers():
    report = {
        "validation": {
            "dispatch": {"ready": True},
            "execution": {"ready": False},
            "selector": {"ready": True},
            "source_shape": {"ready": True},
        }
    }

    result = runtime.validate_runtime_selection(report)

    assert result["ready"] is False
    assert "execution-validation-not-ready" in result["errors"]
