from animation_track_runtime import (
    base_transform_defaults,
    build_track_contract,
    duration_compatibility,
    float_from_hex_word,
    hex_word_from_float,
    summarize_track_forms,
    usage_name,
    validate_animation_node_tree,
    validate_track_binding,
)


def test_usage_mapping_matches_recovered_track_parser():
    assert usage_name("translation") == "translation"
    assert usage_name(1) == "rotation"
    assert usage_name("2") == "scale"
    assert usage_name(3) == "weight"


def test_vec3_tracks_accept_translation_and_scale_only():
    assert validate_track_binding(0, "SampledVec3f")["accepted"] is True
    assert validate_track_binding(2, "KeyedVec3f")["accepted"] is True
    assert validate_track_binding(1, "FixedVec3f")["accepted"] is False


def test_quaternion_tracks_require_rotation():
    assert validate_track_binding(1, "SampledQuatf")["accepted"] is True
    assert validate_track_binding(0, "KeyedQuatf")["accepted"] is False
    assert validate_track_binding(2, "FixedQuatf")["accepted"] is False


def test_f32_tracks_require_weight():
    assert validate_track_binding(3, "Sampledf32")["accepted"] is True
    assert validate_track_binding(0, "Fixedf32")["accepted"] is False


def test_duplicate_transform_slot_is_rejected():
    result = validate_track_binding(0, "KeyedVec3f", existing_slots={"translation": True})
    assert result["accepted"] is False
    assert "already exists" in result["blocking_reasons"][0]


def test_source_xml_float_words_round_trip():
    assert float_from_hex_word("3F800000") == 1.0
    assert hex_word_from_float(1.0) == "3F800000"


def test_base_transform_defaults():
    result = base_transform_defaults()
    assert result["translation"] == [0.0, 0.0, 0.0]
    assert result["rotation"] == [1.0, 0.0, 0.0, 0.0]
    assert result["scale"] == [1.0, 1.0, 1.0]


def test_node_tree_requires_exact_unique_count():
    result = validate_animation_node_tree(["Root", "Spine", "Spine"], expected_count=2)
    assert result["ready"] is False
    assert result["duplicates"] == ["Spine"]


def test_duration_compatibility_uses_tolerance():
    assert duration_compatibility([1.0, 1.0005])["compatible"] is True
    assert duration_compatibility([1.0, 1.01])["compatible"] is False


def test_track_summary_keeps_binary_ids_separate():
    result = summarize_track_forms([
        {"form": "SampledVec3f", "usage": 0},
        {"form": "KeyedQuatf", "usage": 1},
        {"form": "Fixedf32", "usage": 3},
    ])
    assert result["form_counts"] == {"sampled": 1, "keyed": 1, "fixed": 1}
    assert result["binary_channel_ids_not_assumed_equal"] is True


def test_build_track_contract_keeps_duration_and_form():
    result = build_track_contract(
        name="body_pos",
        usage="translation",
        form="SampledVec3f",
        duration=2.5,
        sample_interval=0.0333333,
        values=[[0.0, 0.0, 0.0]],
    )
    assert result["duration"] == 2.5
    assert result["form"]["name"] == "SampledVec3f"
    assert result["binding"]["accepted"] is True
