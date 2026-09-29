from bmw_runtime_register_permutation_filter import (
    BODY_FORMAT,
    FORMAT,
    filter_body_admission_runtime_registers,
    filter_runtime_register_permutations,
)


RESOURCE_SHA = "a" * 64


def _candidate(
    identity,
    *,
    vs=None,
    ps=None,
    pair_status="unique",
    file=None,
):
    return {
        "file": file or f"{identity}.fxo",
        "program_offset": 100,
        "exact": True,
        "score": 2,
        "vertex_pair_valid": True,
        "vertex_pair_score": 1.0,
        "uniform_coverage": 1.0,
        "specialization_score": 1.0,
        "specialization_contradicted": [],
        "specialization_unexpected": [],
        "uniform_matches": ["fresnelFactor", "maxSpecPower"],
        "vertex_pair_selection_status": pair_status,
        "vertex_constant_registers": dict(vs or {}),
        "pixel_constant_registers": dict(ps or {}),
        "pair_sha256": identity.lower() * 64,
        "permutation_identity": {
            "format": "SHIFT.ShaderPermutationIdentity/1",
            "identity_sha256": identity * 64,
        },
    }


def _material(candidates):
    return {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "provenance": {
            "mesh_entry": {"sha256": RESOURCE_SHA},
        },
        "material_binding": {
            "format": "SHIFT.MaterialBinding/1",
            "material": "TEST",
            "fxo_candidates": candidates,
        },
    }


def _witness(register=26):
    return {
        "format": "SHIFT.BMWM3RuntimeMaterialWitness/1",
        "validation": {"ready": True},
        "resource": {"sha256": RESOURCE_SHA},
        "draws": [{
            "material": "TEST",
            "witness_registers": {
                "fresnelFactor": {
                    "stage": "vertex",
                    "register": 8,
                    "value": [0.5, 0.0, 0.0, 0.0],
                },
                "maxSpecPower": {
                    "stage": "pixel",
                    "register": register,
                    "value": [100.0, 0.0, 0.0, 0.0],
                },
            },
        }],
    }


def test_register_witness_selects_one_distinct_permutation():
    result = filter_runtime_register_permutations(
        _material([
            _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
            _candidate("2", vs={"fresnelFactor": 9}, ps={"maxSpecPower": 26}),
        ]),
        _witness(),
    )
    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["top_distinct_permutation_count"] == 2
    assert result["register_match_count"] == 1
    assert result["selected"]["permutation_identity_sha256"] == "1" * 64


def test_register_witness_retains_real_ambiguity():
    result = filter_runtime_register_permutations(
        _material([
            _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
            _candidate("2", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        ]),
        _witness(),
    )
    assert result["ready"] is False
    assert result["status"] == "ambiguous"
    assert result["register_match_count"] == 2
    assert (
        "runtime-registers:multiple-static-permutations"
        in result["blocking_reasons"]
    )


def test_register_witness_collapses_duplicate_cache_locations_by_identity():
    first = _candidate(
        "1",
        vs={"fresnelFactor": 8},
        ps={"maxSpecPower": 26},
        file="cache_a.fxo",
    )
    second = _candidate(
        "1",
        vs={"fresnelFactor": 8},
        ps={"maxSpecPower": 26},
        file="cache_b.fxo",
    )
    result = filter_runtime_register_permutations(
        _material([first, second]),
        _witness(),
    )
    assert result["ready"] is True
    assert result["top_distinct_permutation_count"] == 1
    assert result["register_match_count"] == 1


def test_register_witness_does_not_override_ambiguous_vertex_pair():
    result = filter_runtime_register_permutations(
        _material([
            _candidate(
                "1",
                vs={"fresnelFactor": 8},
                ps={"maxSpecPower": 26},
                pair_status="ambiguous",
            ),
        ]),
        _witness(),
    )
    assert result["ready"] is False
    assert (
        "runtime-registers:vertex-pair-not-unique"
        in result["blocking_reasons"]
    )


def test_register_witness_rejects_same_material_register_conflict():
    witness = _witness()
    witness["draws"].append({
        "material": "TEST",
        "witness_registers": {
            "maxSpecPower": {
                "stage": "pixel",
                "register": 27,
                "value": [100.0, 0.0, 0.0, 0.0],
            },
        },
    })
    result = filter_runtime_register_permutations(
        _material([
            _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        ]),
        witness,
    )
    assert result["ready"] is False
    assert any(
        reason.startswith("runtime-registers:conflict:pixel:maxSpecPower")
        for reason in result["blocking_reasons"]
    )


def test_register_witness_rejects_resource_mismatch():
    witness = _witness()
    witness["resource"]["sha256"] = "b" * 64
    result = filter_runtime_register_permutations(
        _material([
            _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        ]),
        witness,
    )
    assert result["ready"] is False
    assert (
        "runtime-registers:mesh-resource-sha256-mismatch"
        in result["blocking_reasons"]
    )



def _slice(index, candidates):
    value = _material(candidates)
    value.update({
        "format": "SHIFT.BMWMaterialSlice/1",
        "primitive_index": index,
        "golden_identity": {
            "resource": "vehicles/bmw/body.meb",
            "resource_sha256": RESOURCE_SHA,
        },
    })
    return value


def test_body_register_filter_preserves_canonical_primitive_results():
    first = _slice(1, [
        _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        _candidate("2", vs={"fresnelFactor": 9}, ps={"maxSpecPower": 26}),
    ])
    second = _slice(2, [
        _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        _candidate("2", vs={"fresnelFactor": 9}, ps={"maxSpecPower": 26}),
    ])
    admission = {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "selection": {"primitive_indices": [1, 2]},
        "primitive_results": [
            {"primitive_index": 1, "slice": first},
            {"primitive_index": 2, "slice": second},
        ],
    }

    result = filter_body_admission_runtime_registers(
        admission, _witness()
    )

    assert result["format"] == BODY_FORMAT
    assert result["ready"] is True
    assert result["ready_primitive_count"] == 2
    assert result["unique_material_count"] == 1
    assert result["materials"][0]["primitive_indices"] == [1, 2]


def test_body_register_filter_keeps_ambiguous_material_blocked():
    material_slice = _slice(0, [
        _candidate("1", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
        _candidate("2", vs={"fresnelFactor": 8}, ps={"maxSpecPower": 26}),
    ])
    admission = {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "selection": {"primitive_indices": [0]},
        "primitive_results": [
            {"primitive_index": 0, "slice": material_slice},
        ],
    }

    result = filter_body_admission_runtime_registers(
        admission, _witness()
    )

    assert result["ready"] is False
    assert result["status"] == "ambiguous"
    assert result["primitive_results"][0]["register_match_count"] == 2
