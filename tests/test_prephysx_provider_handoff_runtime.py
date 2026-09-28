import prephysx_provider_handoff_runtime as runtime


def _report_for_scalars(widths):
    records = [
        {
            "section": "BODY",
            "entries": [{"name": "name", "value": "body"}],
        },
        {
            "section": "BODY",
            "entries": [{"name": "name", "value": "wheel"}],
        },
    ]
    for index, section in enumerate(widths):
        records.append({
            "section": section,
            "entries": [
                {"name": "name", "value": f"constraint_{index}"},
                {"name": "posbody", "value": "body"},
                {"name": "negbody", "value": "wheel"},
                {"name": "pos", "value": [0.0, 0.0, 0.0]},
                {"name": "neg", "value": [1.0, 0.0, 0.0]},
                {"name": "axis", "value": [1.0, 0.0, 0.0]},
            ],
        })
    return {"records": records}


def test_phase502_identifies_provider1_for_34_scalar_shape():
    report = _report_for_scalars(["JOINT"] * 4 + ["HINGE"] * 5 + ["BAR"] * 12)
    contract = runtime.build_prephysx_provider_handoff_contract(report)

    assert contract["ready"] is True
    assert contract["selection"]["solver_scalar_count"] == 34
    assert contract["selection"]["same_dimension_candidates"] == [1]
    assert contract["selection"]["runtime_acceptance_required"] is True


def test_phase502_identifies_provider0_for_40_scalar_shape():
    report = _report_for_scalars(["JOINT&HINGE"] * 4 + ["BAR"] * 20)
    contract = runtime.build_prephysx_provider_handoff_contract(report)

    assert contract["ready"] is True
    assert contract["selection"]["solver_scalar_count"] == 40
    assert contract["selection"]["same_dimension_candidates"] == [0]
    assert contract["providers"][0]["workspace_doubles"] == 1190
    assert contract["providers"][1]["workspace_doubles"] == 746


def test_phase502_keeps_generic_fallback_for_non_provider_dimension():
    report = _report_for_scalars(["BAR"] * 7)
    contract = runtime.build_prephysx_provider_handoff_contract(report)

    assert contract["ready"] is True
    assert contract["selection"]["solver_scalar_count"] == 7
    assert contract["selection"]["same_dimension_candidates"] == []
    assert contract["selection"]["generic_fallback_available"] is True


def test_phase502_blocks_cross_contract_scalar_mismatch(monkeypatch):
    report = _report_for_scalars(["BAR"] * 7)
    original = runtime.describe_sdf_pre_physx_build

    def mismatched(value):
        result = original(value)
        result = dict(result)
        result["counts"] = dict(result["counts"])
        result["counts"]["solver_scalar_nodes"] = 8
        return result

    monkeypatch.setattr(runtime, "describe_sdf_pre_physx_build", mismatched)
    contract = runtime.build_prephysx_provider_handoff_contract(report)

    assert contract["ready"] is False
    assert "construction-sdf-scalar-count-mismatch" in contract["errors"]
