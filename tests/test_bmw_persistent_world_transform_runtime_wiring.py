from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INJECTION = ROOT / "native_runtime/include/shift_phase648_runtime_injection.hpp"
WIRING = ROOT / "native_runtime/include/shift_bmw_persistent_world_transform_runtime_wiring.hpp"


def test_s4_runs_after_tick_and_before_phase715_upload() -> None:
    text = INJECTION.read_text(encoding="utf-8")
    admission = text.index("admit_bmw_body0_bind_frame_from_environment_once")
    tick = text.index("fixed_step((")
    commit = text.index("commit_and_publish_admitted_bmw_world_transform_after_fixed_step")
    phase715 = text.index("phase715_after_fixed_step")
    phase648 = text.index("phase648_after_fixed_step")

    # Admission is embedded in fixed_step argument evaluation, S4 executes only
    # after the member call returns, then the current transform reaches Phase715.
    assert tick < admission < commit < phase715 < phase648


def test_s4_consumes_positive_proof_and_current_body_without_scheduler_promotion() -> None:
    text = WIRING.read_text(encoding="utf-8")
    assert "current_bmw_body0_bind_frame_runtime_admission" in text
    assert "commit_retail_bmw_vehicle_world_transform" in text
    assert "publish_persistent_bmw_vehicle_world_transform_for_render" in text
    assert "source_pose_snapshot_generation" in text
    assert "source_explicit_update_count" in text
    assert "retail_scheduler_claimed" in text
    assert "test_motion_script_used" in text


def test_s4_vhf_bind_is_scene_backed_and_requires_multi_draw_consensus() -> None:
    text = WIRING.read_text(encoding="utf-8")
    assert '"bundle_set.groups"' in text
    assert "load_native_scene_draw_groups" in text
    assert "vehicle_draw_indices" in text
    assert '"world_transform.svwt"' in text
    assert "validate_vehicle_world_matrix" in text
    assert "exact_same_matrix" in text
    assert "vehicle draws disagree on canonical BMW VHF bind matrix" in text
    assert "arbitrary" not in text.lower()
