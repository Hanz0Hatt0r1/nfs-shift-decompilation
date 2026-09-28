import specialized_provider_capture_handoff_runtime as runtime


def _program(provider_id: int):
    return {
        "format": "SHIFT.SpecializedProviderSolverProgramRuntime/1",
        "version": 1,
        "provider_id": provider_id,
        "function": f"FUN_{provider_id}",
        "scalar_count": 40 if provider_id == 0 else 34,
        "summary": {"ready": True, "source_shape_pivots": 40 if provider_id == 0 else 34},
        "validation": {"ready": True, "errors": []},
    }


def test_attach_observed_solver_does_not_attach_without_runtime_observation():
    result = runtime._attach_observed_solver(
        {"provider_id": 0},
        {0: _program(0), 1: _program(1)},
        observed_provider_id=None,
    )
    assert result == {
        "observed_provider_id": None,
        "attached_provider_id": None,
        "status": "not-attached",
        "solver_program": None,
    }


def test_attach_observed_solver_attaches_only_matching_provider():
    programs = {0: _program(0), 1: _program(1)}
    result = runtime._attach_observed_solver(
        {"provider_id": 1},
        programs,
        observed_provider_id=1,
    )
    assert result["status"] == "attached"
    assert result["attached_provider_id"] == 1
    assert result["solver_program"]["provider_id"] == 1


def test_attach_observed_solver_rejects_mismatched_runtime_provider():
    result = runtime._attach_observed_solver(
        {"provider_id": 0},
        {0: _program(0), 1: _program(1)},
        observed_provider_id=1,
    )
    assert result["status"] == "provider-id-mismatch"


def test_build_capture_handoff_contract_keeps_source_and_capture_layers_separate(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime,
        "build_runtime_selection_contract",
        lambda _source: {"format": "selection", "validation": {}, "ready": True},
    )
    monkeypatch.setattr(
        runtime,
        "validate_runtime_selection",
        lambda _report, observed_provider_id=None: {
            "ready": observed_provider_id in (None, 0, 1),
            "errors": [],
            "observed_provider_id": observed_provider_id,
        },
    )
    monkeypatch.setattr(
        runtime,
        "build_capture_bundle_contract",
        lambda *_args, **_kwargs: {
            "format": "capture",
            "version": 1,
            "directory": "capture",
            "bundle_count": 1,
            "summary": {},
            "ready": True,
            "errors": [],
            "bundles": [
                {"provider_id": 1, "hit": 7, "ready": True}
            ],
        },
    )
    monkeypatch.setattr(
        runtime,
        "_solver_by_provider",
        lambda _source: {0: _program(0), 1: _program(1)},
    )

    result = runtime.build_capture_handoff_contract(
        "source",
        "capture",
        observed_provider_id=1,
    )

    assert result["ready"] is True
    assert result["bundles"][0]["source_handoff"]["status"] == "attached"
    assert result["bundles"][0]["source_handoff"]["attached_provider_id"] == 1
