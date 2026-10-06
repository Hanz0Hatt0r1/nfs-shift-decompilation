from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/materialize_s5_selected_physics_tweaker_rate.py"
SPEC = importlib.util.spec_from_file_location(
    "materialize_s5_selected_physics_tweaker_rate", TOOL
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_committed_resource_and_cadence_inputs_match_exact_blocker_identity():
    identity = MODULE._resource_identity(
        ROOT / "evidence/bmw_offset33b_selector_geometry_inputs.json"
    )
    assert identity["archive"] == {
        "filename": "PHYSICSBOOTFLOW.bff",
        "sha256": "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a",
    }
    assert identity["entry"] == {
        "index": 49,
        "path": "vehicles/physics/physicstweaker.xml",
        "compression_type": 2,
        "compressed_size": 2452,
        "uncompressed_size": 21762,
        "decoded_sha256": "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
    }

    cadence = MODULE._validate_cadence(
        ROOT / "evidence/s5_retail_outer_update_cadence.json"
    )
    assert cadence["adjudication"]["outer_scheduler_cadence_admitted"] is True
    assert cadence["adjudication"]["inner_fixed_step_1_over_rate_proven"] is True
    assert cadence["adjudication"][
        "final_inner_rate_requires_loaded_PhysicsTweaker_value"
    ] is True
    assert cadence["physics_rate_field"]["runtime_rate_global"] == "DAT_00c130d2"
    assert cadence["physics_rate_field"]["tick_rate_tweaker_offset"] == "0x492"


def test_tick_rate_parser_accepts_unique_positive_integral_property():
    decoded = b'<root><prop name="tick rate" data="360" /></root>'
    assert MODULE._parse_tick_rate(decoded, _sha(decoded)) == 360


def test_tick_rate_parser_rejects_hash_mismatch_before_semantic_admission():
    decoded = b'<root><prop name="tick rate" data="180" /></root>'
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        MODULE._parse_tick_rate(decoded, "0" * 64)


def test_tick_rate_parser_rejects_duplicate_property():
    decoded = (
        b'<root><prop name="tick rate" data="180" />'
        b'<prop name="tick rate" data="360" /></root>'
    )
    with pytest.raises(ValueError, match="exactly one"):
        MODULE._parse_tick_rate(decoded, _sha(decoded))


@pytest.mark.parametrize("token", ["0", "-1", "180.5", "65536", "nan", "inf"])
def test_tick_rate_parser_rejects_invalid_loaded_rate_domain(token: str):
    decoded = f'<root><prop name="tick rate" data="{token}" /></root>'.encode()
    with pytest.raises(ValueError):
        MODULE._parse_tick_rate(decoded, _sha(decoded))


def test_materializer_rejects_non_exact_decoded_entry(tmp_path: Path):
    decoded = tmp_path / "physicstweaker.xml"
    decoded.write_text(
        '<root><prop name="tick rate" data="180" /></root>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="decoded PhysicsTweaker SHA-256 mismatch"):
        MODULE.materialize(
            ROOT / "evidence/bmw_offset33b_selector_geometry_inputs.json",
            ROOT / "evidence/s5_retail_outer_update_cadence.json",
            decoded_entry_path=decoded,
        )


def test_materializer_source_never_substitutes_constructor_default_for_loaded_value():
    source = TOOL.read_text(encoding="utf-8")
    assert "constructor default" in source
    assert 'PROPERTY_NAME = "tick rate"' in source
    assert "expected exactly one PhysicsTweaker" in source
    assert "decoded_sha256_verified_this_run" in source
    assert "RetailOuterSchedulerContract::admit_loaded_inner_rate(rate_hz)" in source
    assert '"constructor_default_180_used_as_selected_session_value": False' in source
    assert "rate_hz = 180" not in source
    assert "loaded_inner_rate_hz = 180" not in source


def test_frontier_remains_negative_until_exact_payload_is_materialized():
    frontier = json.loads(
        (ROOT / "evidence/s5_selected_physics_tweaker_rate_frontier.json").read_text(
            encoding="utf-8"
        )
    )
    assert frontier["format"] == "SHIFT.SelectedSessionPhysicsTweakerRateFrontier/1"
    assert frontier["ready"] is False
    assert frontier["blocker"] == "selected-session-physics-tweaker-rate-admission"
    assert frontier["required_resource"]["archive_sha256"] == (
        "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a"
    )
    assert frontier["required_resource"]["decoded_sha256"] == (
        "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f"
    )
    assert frontier["handoff"]["loaded_inner_physics_rate_admitted"] is False
    assert frontier["handoff"]["retail_inner_substep_execution_admitted"] is False
    assert frontier["limits"]["constructor_default_180_may_close_blocker"] is False
    assert frontier["limits"]["community_default_value_may_close_blocker"] is False
