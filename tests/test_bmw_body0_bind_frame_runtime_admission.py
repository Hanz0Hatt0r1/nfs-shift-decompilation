from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "native_runtime/include/shift_bmw_body0_bind_frame_runtime_admission.hpp"
INJECTION = ROOT / "native_runtime/include/shift_phase648_runtime_injection.hpp"
PACKET_HEADER = ROOT / "native_runtime/include/shift_bmw_body0_bind_frame_proof_packet.hpp"
EVIDENCE = ROOT / "evidence/process2_bmw_body0_bind_frame_runtime_admission.json"


def test_production_fixed_step_admits_optional_positive_packet_before_tick() -> None:
    injection = INJECTION.read_text(encoding="utf-8")
    assert '#include "shift_bmw_body0_bind_frame_runtime_admission.hpp"' in injection
    admission_call = "::shift::runtime::physics::admit_bmw_body0_bind_frame_from_environment_once(),"
    assert "#define fixed_step(phase648_intent_)" in injection
    assert "fixed_step((" in injection
    assert admission_call in injection
    assert "(phase648_intent_)));" in injection
    assert injection.index("fixed_step((") < injection.index(admission_call)
    assert injection.index(admission_call) < injection.index("(phase648_intent_)));" )


def test_runtime_admission_is_fail_closed_and_does_not_claim_scheduler_or_transform() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT_NATIVE_BMW_BODY0_BIND_PROOF_PACKET" in header
    assert "SHIFT.NativeBMWBody0BindFrameRuntimeAdmission/1" in header
    assert "load_bmw_body0_bind_frame_proof_packet(path)" in header
    assert "BODY0 bind proof packet path changed after runtime admission" in header
    assert "BODY0 bind proof packet environment disappeared after admission" in header
    assert r'\"retail_scheduler_claimed\":false' in header
    assert r'\"vehicle_world_transform_committed\":false' in header
    assert "commit_bmw_vehicle_world_transform(" not in header
    assert "publish_persistent_bmw_vehicle_world_transform_for_render(" not in header


def test_runtime_admission_reuses_packet_and_typed_admission_chain() -> None:
    header = HEADER.read_text(encoding="utf-8")
    packet_header = PACKET_HEADER.read_text(encoding="utf-8")
    assert '#include "shift_bmw_body0_bind_frame_proof_packet.hpp"' in header
    assert "LoadedBmwBody0BindFrameProofPacket" in packet_header
    assert "ProvenBmwBody0BindFrame admitted" in packet_header


def test_machine_readable_handoff_keeps_process1_ownership() -> None:
    import json

    value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert value["format"] == "SHIFT.Process2BMWBody0BindFrameRuntimeAdmission/1"
    assert value["status"] == "ready-gate"
    assert value["input"]["current_positive_handoff_present"] is False
    assert value["output"]["production_fixed_step_hook_ready"] is True
    assert value["output"]["admission_runs_before_native_fixed_step"] is True
    assert value["output"]["retail_scheduler_claimed"] is False
    assert value["output"]["vehicle_world_transform_committed"] is False
    assert value["ownership"]["current_blocker_owner"] == "Process 1"
