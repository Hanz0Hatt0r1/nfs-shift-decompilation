from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/materialize_s5_selected_physics_tweaker_rate.py"
NATIVE_HEADER = (
    ROOT / "native_runtime/src/selected_session_physics_tweaker_rate_handoff.hpp"
)
SPEC = importlib.util.spec_from_file_location(
    "materialize_s5_selected_physics_tweaker_rate_native_handoff", TOOL
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture_report(tmp_path: Path, monkeypatch) -> dict:
    decoded_bytes = b'<root><prop name="tick rate" data="360" /></root>'
    decoded = tmp_path / "physicstweaker.xml"
    decoded.write_bytes(decoded_bytes)
    identity = {
        "archive": {
            "filename": "PHYSICSBOOTFLOW.bff",
            "sha256": "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a",
        },
        "entry": {
            "index": 49,
            "path": "vehicles/physics/physicstweaker.xml",
            "compression_type": 2,
            "compressed_size": 2452,
            "uncompressed_size": 21762,
            "decoded_sha256": _sha(decoded_bytes),
        },
    }
    cadence = {
        "fixed_step_accumulator": {
            "normal_outer_increment_seconds": 0.03333333507180214,
        }
    }
    monkeypatch.setattr(MODULE, "_resource_identity", lambda _path: identity)
    monkeypatch.setattr(MODULE, "_validate_cadence", lambda _path: cadence)
    return MODULE.materialize(
        tmp_path / "geometry.json",
        tmp_path / "cadence.json",
        decoded_entry_path=decoded,
    )


def test_materializer_renders_typed_native_handoff_without_manual_rate_copy(
    tmp_path: Path, monkeypatch
):
    report = _fixture_report(tmp_path, monkeypatch)
    rendered = MODULE.render_native_handoff_header(report)

    assert '#include "selected_session_physics_tweaker_rate_handoff.hpp"' in rendered
    assert "kMaterializedSelectedSessionPhysicsTweakerRateHandoff" in rendered
    assert '"SHIFT.SelectedSessionPhysicsTweakerRate/1"' in rendered
    assert '"PHYSICSBOOTFLOW.bff"' in rendered
    assert '"vehicles/physics/physicstweaker.xml"' in rendered
    assert '"exact-decoded-entry"' in rendered
    assert "360u" in rendered
    assert '"DAT_00c130d2"' in rendered
    assert '"0x388"' in rendered
    assert "false," in rendered


def test_native_admission_locks_exact_pc_resource_identity_and_forbidden_substitutes():
    source = NATIVE_HEADER.read_text(encoding="utf-8")
    assert "SelectedSessionPhysicsTweakerRateHandoff" in source
    assert "admit_selected_session_physics_tweaker_rate" in source
    assert "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a" in source
    assert "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f" in source
    assert '"vehicles/physics/physicstweaker.xml"' in source
    assert "decoded_sha256_verified_this_run" in source
    assert "archive_sha256_verified_this_run" in source
    assert "constructor_default_180_used_as_selected_session_value" in source
    assert "community_or_modded_value_used" in source
    assert "host_1_60_used_as_inner_rate" in source
    assert "worker_poll_10ms_used_as_inner_rate" in source
    assert "scheduler.admit_loaded_inner_rate" in source


def test_generated_handoff_does_not_mark_retail_inner_execution_admitted(
    tmp_path: Path, monkeypatch
):
    report = _fixture_report(tmp_path, monkeypatch)
    assert report["handoff"]["loaded_inner_physics_rate_admitted"] is True
    assert report["handoff"]["retail_inner_substep_execution_admitted"] is False
    rendered = MODULE.render_native_handoff_header(report)
    assert "kMaterializedSelectedSessionPhysicsTweakerRateHandoff" in rendered
