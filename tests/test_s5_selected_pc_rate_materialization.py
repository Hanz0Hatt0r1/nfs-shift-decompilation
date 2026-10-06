import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RATE = ROOT / "evidence/s5_selected_physics_tweaker_rate.json"
FRONTIER = ROOT / "evidence/s5_selected_physics_tweaker_rate_frontier.json"
AUTHORITY = ROOT / "evidence/process2_runtime_scheduler_authority.json"
EXECUTION = ROOT / "evidence/s5_selected_session_retail_vehicle_execution.json"
NATIVE = ROOT / "native_runtime/src/materialized_selected_session_physics_tweaker_rate.hpp"

ARCHIVE_SHA256 = "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a"
DECODED_SHA256 = "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f"


def test_exact_pc_physics_tweaker_rate_is_materialized_from_hash_locked_resource() -> None:
    payload = json.loads(RATE.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.SelectedSessionPhysicsTweakerRate/1"
    assert payload["ready"] is True
    assert payload["status"] == "selected-session-physics-tweaker-rate-ready"
    assert payload["resource_identity"]["archive"]["filename"] == "PHYSICSBOOTFLOW.bff"
    assert payload["resource_identity"]["archive"]["sha256"] == ARCHIVE_SHA256
    assert payload["resource_identity"]["entry"]["index"] == 49
    assert payload["resource_identity"]["entry"]["path"] == "vehicles/physics/physicstweaker.xml"
    assert payload["resource_identity"]["entry"]["decoded_sha256"] == DECODED_SHA256
    assert payload["verification"]["mode"] == "exact-retail-bff"
    assert payload["verification"]["archive_sha256_verified_this_run"] is True
    assert payload["verification"]["decoded_sha256_verified_this_run"] is True
    assert payload["selected_session_rate"]["property"] == "tick rate"
    assert payload["selected_session_rate"]["rate_hz"] == 180
    assert payload["selected_session_rate"]["inner_substep_seconds"] == 1 / 180
    assert payload["handoff"]["loaded_inner_physics_rate_admitted"] is True
    # The resource materializer itself never claims downstream BODY execution.
    assert payload["handoff"]["retail_inner_substep_execution_admitted"] is False
    assert payload["limits"]["constructor_default_180_used_as_selected_session_value"] is False


def test_rate_handoff_stays_narrow_while_downstream_exact_execution_is_admitted() -> None:
    frontier = json.loads(FRONTIER.read_text(encoding="utf-8"))
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))

    # The rate frontier remains the producer-stage contract and therefore keeps
    # execution separate from rate materialization.
    assert frontier["ready"] is True
    assert frontier["status"] == "selected-session-rate-admitted"
    assert frontier["blocker"] == "retail-inner-substep-execution-admission"
    assert frontier["available_evidence"]["selected_session_rate_hz"] == 180
    assert frontier["handoff"]["loaded_inner_physics_rate_admitted"] is True
    assert frontier["handoff"]["retail_inner_substep_execution_admitted"] is False

    # The downstream native consumer is the layer that closes execution.
    assert authority["input"]["loaded_inner_rate_present"] is True
    assert authority["input"]["loaded_inner_rate_hz"] == 180
    assert authority["output"]["loaded_inner_rate_admitted"] is True
    assert authority["output"]["inner_substep_execution_admitted"] is True
    assert authority["output"]["selected_session_normal_outer_substeps"] == 6

    assert execution["format"] == "SHIFT.SelectedSessionRetailVehicleExecution/1"
    assert execution["ready"] is True
    assert execution["selected_session"]["rate_hz"] == 180
    assert execution["selected_session"]["normal_outer_substep_count"] == 6
    assert execution["handoff"]["retail_inner_substep_execution_admitted"] is True
    assert execution["limits"]["provider_semantics_promoted"] is False


def test_native_materialized_handoff_is_exact_pc_rate_not_fixture_substitution() -> None:
    source = NATIVE.read_text(encoding="utf-8")

    assert "kMaterializedSelectedSessionPhysicsTweakerRateHandoff" in source
    assert f'"{ARCHIVE_SHA256}"' in source
    assert f'"{DECODED_SHA256}"' in source
    assert '"exact-retail-bff"' in source
    assert '"tick rate"' in source
    assert "180u" in source
    assert "360u" not in source
    assert "static_assert(kMaterializedSelectedSessionPhysicsTweakerRateHandoff.rate_hz == 180u)" in source
