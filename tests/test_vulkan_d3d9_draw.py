import json
from pathlib import Path

from vulkan_d3d9_draw import translate_d3d9_indexed_draw


_EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "shift_d3d9_vulkan_draw_parameters_20261021.json"


def _draws():
    return json.loads(_EVIDENCE.read_text(encoding="utf-8"))["draws"]


def test_first_captured_retail_draw_maps_to_vulkan_indexed_draw_parameters():
    row = _draws()[0]
    report = translate_d3d9_indexed_draw(row["draw_event"], row["index_binding"])

    assert report["parameter_translation_ready"] is True
    assert report["vulkan_draw"] == row["expected_vulkan_draw"]
    assert report["submission_ready"] is False
    assert report["submission_blocking_reasons"] == [
        "d3d9-vulkan-draw:buffer-payload-and-render-pipeline-not-supplied"
    ]


def test_captured_race_target_ranges_fit_its_index16_buffer():
    row = _draws()[1]
    report = translate_d3d9_indexed_draw(row["draw_event"], row["index_binding"])

    assert report["parameter_translation_ready"] is True
    assert report["vulkan_draw"] == row["expected_vulkan_draw"]
    assert report["vulkan_draw"]["index_count"] * 2 == row["index_binding"]["descriptor"]["length"]


def test_d3d9_draw_translation_fails_closed_for_unobserved_topology_and_bad_range():
    row = _draws()[0]
    unsupported = dict(row["draw_event"], primitive_type=5)
    report = translate_d3d9_indexed_draw(unsupported, row["index_binding"])
    assert report["parameter_translation_ready"] is False
    assert "d3d9-vulkan-draw:unsupported-primitive-type:5" in report["blocking_reasons"]

    out_of_bounds = dict(row["draw_event"], start_index=1)
    report = translate_d3d9_indexed_draw(out_of_bounds, row["index_binding"])
    assert report["parameter_translation_ready"] is False
    assert "d3d9-vulkan-draw:index-range-out-of-bounds" in report["blocking_reasons"]
