from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_body_motion_ownership.json"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
PROVIDER_HEADER = ROOT / "native_runtime/include/shift_fun_00770e80_contact_outer_provider_chain.hpp"
PROVIDER_SOURCE = ROOT / "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"
COMPOSED_HEADER = ROOT / "native_runtime/include/shift_fun_00770e80_composed_anchor_chain.hpp"
COMPOSED_SOURCE = ROOT / "native_runtime/src/fun_00770e80_composed_anchor_chain.cpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"


def test_body_motion_ownership_evidence_is_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0BodyMotionOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["consumer"] == "FUN_007675f0"
    assert payload["source"]["consumer_source_line"] == 759784
    assert payload["source"]["persistent_writer_contract"] == "SHIFT.BodyFrameIntegrationStatic/1"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["body_motion"]["speed_x_offset"] == "0x78"
    assert payload["body_motion"]["speed_z_offset"] == "0x88"
    assert payload["body_motion"]["external_provider_fields_required"] is False
    assert payload["pass_refresh"]["stale_outer_snapshot_allowed"] is False
    assert payload["scope"]["external_provider_count_after"] == 7
    assert payload["scope"]["provider_count_reduced"] is False


def test_external_contact_outer_contract_excludes_body_motion() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    external_struct = header.split("struct ContactOuterExternalInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "double speed_x" not in external_struct
    assert "double speed_z" not in external_struct
    assert "ContactOuterExternalInput(const ContactOuterKernelInput& legacy)" in external_struct
    assert "speed_x(legacy.speed_x)" not in external_struct
    assert "speed_z(legacy.speed_z)" not in external_struct
    assert "kFun007675f0Body0SpeedXOffset = 0x78u" in header
    assert "kFun007675f0Body0SpeedZOffset = 0x88u" in header
    assert "derive_fun_007675f0_body0_motion" in header
    assert "compose_fun_007675f0_input" in header

    provider_header = PROVIDER_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    assert "std::function<ContactOuterExternalInput()>" in provider_header
    assert "std::function<physics::ContactOuterExternalInput(std::size_t pass_index)>" in session_header


def test_each_pass_reads_current_persistent_body_before_contact_outer() -> None:
    provider_source = PROVIDER_SOURCE.read_text(encoding="utf-8")
    composed_header = COMPOSED_HEADER.read_text(encoding="utf-8")
    composed_source = COMPOSED_SOURCE.read_text(encoding="utf-8")

    assert "Fun0076d100CurrentBodyObserver" in composed_header
    assert "current_body_observer" in composed_header
    assert "derive_fun_007675f0_body0_motion(current_body_bytes)" in provider_source
    assert "compose_fun_007675f0_input(external, state->body_motion)" in provider_source
    assert "FUN_007675f0 executed before current BODY0 motion ownership bridge" in provider_source

    observer = composed_source.index("callbacks.current_body_observer(result.final_body_bytes)")
    anchors = composed_source.index("execute_fun_0076d100_required_anchor_sequence")
    assert observer < anchors
    assert "result.current_body_observer_call_count" in composed_source
