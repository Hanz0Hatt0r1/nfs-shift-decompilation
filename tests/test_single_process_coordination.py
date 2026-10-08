import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md"
PROMPTS = ROOT / "docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md"
EXECUTION = ROOT / "evidence/playable_slice_three_process_execution.json"
V5 = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md"
V5_PROMPT = ROOT / "docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md"
V5_EXECUTION = ROOT / "evidence/playable_slice_single_process_execution.json"
PROCESS = ROOT / "PROCESS_INSTRUCTIONS.md"


def test_three_process_execution_contract_is_active_and_current() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    frontier = payload["main_frontier"]

    assert payload["format"] == "SHIFT.PlayableSliceThreeProcessExecution/1"
    assert payload["status"] == "active"
    assert payload["execution_model"] == "three-process-parallel"
    assert frontier["phase"] == 749
    assert frontier["active_external_provider_count"] == 7
    assert frontier["selected_session_rate_hz"] == 180
    assert frontier["selected_session_normal_outer_substeps"] == 6
    assert frontier["body0_bind_frame_ready"] is True
    assert frontier["vehicle_world_transform_ready"] is True
    assert frontier["retail_inner_substep_execution_admitted"] is True
    assert frontier["fun_00765c40_selected_collision_output_typed"] is True
    assert frontier["fun_00765c40_p1_ownership_complete"] is True
    assert frontier["fun_00765c40_p2_4_handoff_ready"] is True
    assert frontier["fun_00766510_primary_response_application_native"] is True
    assert frontier["fun_00766510_application_point_owner_ready"] is True
    assert frontier["fun_00766510_primary_caller_accumulator_delta_native"] is True
    assert frontier["fun_00766510_shared_reference_owner_ready"] is True
    assert frontier["fun_00713630_reference_source_native"] is True
    assert frontier["fun_00766510_early_branch_owner_ready"] is True
    assert frontier["fun_00766510_optional_branch_owner_ready"] is True
    assert frontier["fun_00766510_later_branch_owner_ready"] is True
    assert frontier["fun_00766510_later_branch_native"] is True
    assert frontier["fun_00766510_direct_caller_accumulator_surface_ready"] is True
    assert frontier["fun_00766510_p1_residual_frontier_ready"] is True
    assert frontier["fun_00766510_p1_complete"] is False
    assert frontier["retail_control_chain_complete"] is False
    assert frontier["retail_camera_follow_ready"] is False


def test_process_queues_are_separate_and_dependency_routed() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    processes = payload["processes"]

    p1 = processes["process_1"]
    p2 = processes["process_2"]
    p3 = processes["process_3"]

    assert p1["branch_prefix"] == "process-1/"
    assert p2["branch_prefix"] == "process-2/"
    assert p3["branch_prefix"] == "process-3/"

    assert [row["id"] for row in p1["queue"]] == ["P1.1", "P1.2", "P1.3", "P1.4"]
    assert [row["id"] for row in p2["queue"]] == ["P2.1", "P2.2", "P2.3", "P2.4", "P2.5", "P2.6"]
    assert [row["id"] for row in p3["queue"]] == ["P3.1", "P3.2", "P3.3", "P3.4", "P3.5", "P3.6"]

    assert p1["queue"][0]["state"] == "current"
    assert p1["queue"][0]["contract"] == "SHIFT.Fun00766510ResidualOwnershipFrontier/1"
    assert "all four direct FUN_00753650" in p1["queue"][0]["task"]
    assert p1["queue"][1]["state"] == "complete"
    assert p1["queue"][1]["contract"] == "SHIFT.Fun00765c40ResidualOwnershipFrontier/1"
    assert "0x00c133ac/vtable+0x1c0" in p1["queue"][1]["task"]
    assert p2["queue"][0]["state"] == "complete"
    assert p2["queue"][1]["state"] == "complete"
    assert p2["queue"][2]["state"] == "current-blocked-on-process-1"
    assert "Phase749" in p2["queue"][2]["task"]
    assert p2["queue"][3]["state"] == "ready-to-consume"
    assert "P1.2" in p2["queue"][3]["depends_on"]
    assert "0x00c133ac/vtable+0x1c0" in p2["queue"][3]["task"]
    assert p3["queue"][0]["state"] == "current"
    assert "P1.1" in p2["queue"][2]["depends_on"]
    assert p1["queue"][0]["consumer"] == "Process 2 P2.3"
    assert p1["queue"][1]["consumer"] == "Process 2 P2.4"


def test_provider_frontier_targets_first_real_boundary_reduction() -> None:
    payload = json.loads(EXECUTION.read_text(encoding="utf-8"))
    frontier = payload["provider_frontier"]

    assert frontier["count"] == 7
    assert frontier["target_after_first_reduction"] == 6
    assert frontier["first_reduction_target"] == "FUN_00766510/contact_response"
    assert len(frontier["boundaries"]) == 7


def test_v6_docs_define_non_overlapping_active_ownership() -> None:
    canonical = V6.read_text(encoding="utf-8")
    prompts = PROMPTS.read_text(encoding="utf-8")
    process = PROCESS.read_text(encoding="utf-8")

    assert "Status: **canonical coordination instructions**" in canonical
    assert "Current merged main frontier is **Phase 749**" in canonical
    assert "Phase748 FUN_00713630" in canonical
    assert "Phase749 native later" in canonical
    assert "direct FUN_00753650 caller-accumulator surface (4/4)" in canonical
    assert "PROCESS 1 — retail proof / ABI / producer / timing" in canonical
    assert "PROCESS 2 — native physics / runtime execution" in canonical
    assert "PROCESS 3 — resources / scene / renderer / playable bootstrap" in canonical
    assert "7 -> 6" in canonical
    assert "PROCESS 1 — retail proof / provenance / timing" in prompts
    assert "Phase748" in prompts and "Phase749" in prompts
    assert "PROCESS 2 — native physics / runtime" in prompts
    assert "PROCESS 3 — resources / scene / render / playable bootstrap" in prompts
    assert "PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md" in process
    assert "Current merged main frontier: **Phase 749**" in process
    assert "playable_slice_three_process_execution.json" in process
    assert "process-1/<blocker>" in process
    assert "NEXT_OWNER:" in process


def test_v5_single_process_coordination_is_retired() -> None:
    v5 = V5.read_text(encoding="utf-8")
    prompt = V5_PROMPT.read_text(encoding="utf-8")
    execution = json.loads(V5_EXECUTION.read_text(encoding="utf-8"))

    assert "Status: **RETIRED**" in v5
    assert "PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md" in v5
    assert "Status: **RETIRED**" in prompt
    assert execution["status"] == "retired"
    assert execution["superseded_by"] == "SHIFT.PlayableSliceThreeProcessExecution/1"
    assert execution["may_select_new_work"] is False
