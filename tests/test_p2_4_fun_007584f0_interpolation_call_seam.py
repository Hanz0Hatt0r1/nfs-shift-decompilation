import json
from pathlib import Path

from src.physics import native_vehicle_external_provider_frontier_p2_4_current as p2_4

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_interpolation_call_seam.json"
CURRENT_FRONTIER = ROOT / "evidence/p2_4_fun_00765c40_current_frontier.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_interpolation_call_seam.hpp"


def test_interpolation_seam_pins_retail_call_store_surface() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007584f0InterpolationCallSeam/2"
    surface = payload["retail_surface"]
    assert surface["owner"] == "FUN_007584f0"
    assert surface["helper"] == "0x00783a30"
    assert surface["call_site"] == "0x007587ef"
    assert surface["argument_count"] == 4
    assert surface["argument_width"] == "float"
    assert surface["store_site"] == "0x007587f4"
    assert surface["destination"] == "HDVehicle+0x3420"


def test_interpolation_formula_is_native_but_family_stays_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["interpolation_formula_internalized"] is True
    assert limits["argument_semantic_names_for_FUN_007584f0_call_proven"] is False
    assert limits["positive_load_qword_producers_internalized"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = p2_4.build_current_frontier()
    fun = frontier["fun_00765c40"]
    assert fun["fun_007584f0_interpolation_call_seam_contract"] == (
        p2_4.FUN007584F0_INTERPOLATION_CALL_SEAM_FORMAT
    )
    assert fun["fun_007584f0_interpolation_call_seam_native"] is True
    assert fun["fun_007584f0_interpolation_argument_count"] == 4
    assert fun["fun_007584f0_interpolation_helper_formula_internalized"] is True
    assert fun["fun_007584f0_positive_qword_producers_internalized"] is False
    assert fun["residual_producer_promotion_authorized_family_count"] == 0
    assert "FUN_007584f0_computed_payloads" in fun["remaining_explicit_producers"]
    assert frontier["guards"][
        "fun_007584f0_interpolation_seam_treated_as_family_complete"
    ] is False

    canonical = json.loads(CURRENT_FRONTIER.read_text(encoding="utf-8"))
    assert canonical["fun_00765c40"]["fun_007584f0_interpolation_call_seam_native"] is True
    assert canonical["fun_00765c40"][
        "fun_007584f0_interpolation_helper_formula_internalized"
    ] is True
    assert canonical["fun_00765c40"][
        "fun_007584f0_positive_qword_producers_internalized"
    ] is False
    assert canonical["external_provider_count"] == 7


def test_interpolation_header_reuses_existing_native_formula() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.Fun007584f0InterpolationCallSeam/2"' in text
    assert "kFun007584f0InterpolationHelper = 0x00783a30u" in text
    assert "kFun007584f0InterpolationCallSite = 0x007587efu" in text
    assert "kFun007584f0InterpolationStoreSite = 0x007587f4u" in text
    assert "kFun007584f0InterpolationArgumentCount = 4u" in text
    assert "std::array<float, kFun007584f0InterpolationArgumentCount>" in text
    assert "execute_fun_00783a30_distance_filter(" in text
    assert "std::function<float" not in text
    assert "return {" in text
