import pytest

from wheel_contact_response_input_runtime import (
    BODY_BASE_OFFSET,
    BODY_INPUT_VECTOR_OFFSET,
    BODY_TRANSFORM_OFFSET,
    CONSUMER,
    TRANSFORM,
    Vec3,
    build_contract,
    capture_transform_result,
    source_contract,
)


def test_source_contract_matches_fun_00766510_call_site():
    contract = build_contract()
    assert contract["function"] == "FUN_00766510"
    assert contract["transform"] == "FUN_007af0a0"
    assert contract["consumer"] == "FUN_007551e0"
    assert contract["producer_call"]["this_transform"] == "body + 0xd4"
    assert contract["producer_call"]["source_vector"] == "body + 0x18"
    assert contract["producer_call"]["destination"] == "local_200"
    assert TRANSFORM == "FUN_007af0a0"
    assert CONSUMER == "FUN_007551e0"


def test_addressed_offsets_are_relative_to_body_object():
    source = source_contract()
    assert source.body_base == BODY_BASE_OFFSET
    assert source.transform_context == BODY_BASE_OFFSET + BODY_TRANSFORM_OFFSET
    assert source.source_vector_offset == BODY_BASE_OFFSET + BODY_INPUT_VECTOR_OFFSET


def test_source_and_transformed_vectors_are_not_conflated():
    evidence = capture_transform_result((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert evidence.source == Vec3(1.0, 2.0, 3.0)
    assert evidence.transformed == Vec3(4.0, 5.0, 6.0)
    assert evidence.source != evidence.transformed


def test_exactly_three_components_are_required():
    with pytest.raises(ValueError):
        capture_transform_result((1.0, 2.0), (3.0, 4.0, 5.0))
    with pytest.raises(ValueError):
        capture_transform_result((1.0, 2.0, 3.0), (4.0, 5.0))


def test_contract_keeps_transform_semantics_external():
    contract = build_contract()
    assert "FUN_007af0a0 transform semantics" in contract["unresolved"]
    assert "physical meaning and units of body field +0x18" in contract["unresolved"]
