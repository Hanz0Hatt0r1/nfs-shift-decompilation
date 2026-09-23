import pytest

from color_abi import (
    build_color_abi_evidence,
    compare_color_candidate,
    interpret_color_bytes,
)


def test_color_abi_preserves_rgba_and_bgra_candidates():
    raw = bytes((10, 20, 30, 40, 100, 110, 120, 130))
    result = build_color_abi_evidence("460", raw)
    assert result["format"] == "SHIFT.ColorABIEvidence/1"
    assert result["property_id"] == "460"
    assert result["confidence"] == "ambiguous-channel-order"
    by_order = {x["order"]: x for x in result["candidates"]}
    assert interpret_color_bytes(raw, "RGBA") == raw
    assert interpret_color_bytes(raw, "BGRA") == bytes((30, 20, 10, 40, 120, 110, 100, 130))
    assert by_order["RGBA"]["stats"]["samples"] == 2
    assert by_order["RGBA"]["stats"]["alpha_non_opaque"] == 2


def test_color_abi_known_reference_can_distinguish_candidates_without_selection():
    raw = bytes((10, 20, 30, 255))
    expected = bytes((30, 20, 10, 255))
    result = compare_color_candidate("461", raw, expected)
    assert result["format"] == "SHIFT.ColorABICandidateComparison/1"
    assert result["selection"] == "not-selected"
    matches = {x["order"]: x for x in result["candidate_results"]}
    assert matches["RGBA"]["exact_match"] is False
    assert matches["BGRA"]["exact_match"] is True


def test_color_abi_rejects_unknown_property():
    with pytest.raises(ValueError, match="unsupported color property"):
        build_color_abi_evidence("200", b"\x00\x00\x00\x00")


def test_color_abi_rejects_partial_sample():
    with pytest.raises(ValueError, match="divisible by four"):
        build_color_abi_evidence("460", b"\x01\x02\x03")
