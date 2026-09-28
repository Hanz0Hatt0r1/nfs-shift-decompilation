import specialized_provider_runtime as providers
import bmw_provider_compatibility_runtime as runtime

def test_bmw_seed_has_330_strict_upper_nonzero_cells():
    assert runtime.derive_strict_upper_seed_nonzero(runtime.BMW_SEED) == 330

def test_provider0_seed_is_dimension_compatible_but_mask_incompatible():
    result = runtime.classify_bmw_seed_against_provider(0)
    assert result["status"] == "seed-mask-incompatible"
    assert result["runtime_match_status"] == "requires-capture"
    assert result["seed_upper_nonzero"] == 330
    assert result["provider_expected_upper_nonzero"] == 450
    assert result["additional_upper_nonzero_cells_required_to_match"] == 120

def test_provider1_is_dimension_incompatible():
    result = runtime.classify_bmw_seed_against_provider(1)
    assert result["status"] == "dimension-incompatible"
    assert result["dimension"]["expected"] == 34
    assert result["dimension"]["actual"] == 40

def test_gate_is_strict_and_capture_gated():
    gate = runtime.build_bmw_provider_compatibility_gate()
    validation = runtime.validate_bmw_provider_gate(gate)
    assert validation["ready"] is True
    assert gate["runtime_selection"]["provider_0"] == "unproven-until-final-pre-solve-capture"
    assert providers.provider_signature(0) is not None
