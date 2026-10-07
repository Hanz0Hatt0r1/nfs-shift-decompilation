from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_alertable_pacing.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_ALERTABLE_PACING.md"
OWNER = ROOT / "evidence/process1_physics_manager_controller_owner.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_process1_controller1_alertable_pacing_is_exact_pc_retail() -> None:
    payload = _load(EVIDENCE)
    assert payload["format"] == "SHIFT.Process1Controller1AlertablePacing/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False


def test_controller_thread_create_and_explicit_resume_are_hash_locked() -> None:
    payload = _load(EVIDENCE)
    creation = payload["thread_creation"]
    resume = payload["startup_resume"]

    assert creation["thread_entry"] == "FUN_00649b10"
    assert creation["beginthreadex_initflag"] == 4
    assert creation["later_explicit_resume_proven"] is True
    assert creation["machine_spans"]["beginthreadex_entry_arg_flag_pack"]["sha256"] == (
        "ee6b842fd84765396f45565ce61173ef3c15cb69cd30d6780b138a0077690d1b"
    )

    assert resume["resume_occurs_after_controller1_manager_attachments"] is True
    assert resume["controller_virtual_slot_offset"] == "0x10"
    assert resume["controller_resume_slot_target"] == "FUN_00655040"
    assert resume["os_resume_api"] == "ResumeThread"
    assert resume["machine_spans"]["startup_resume_call"]["sha256"] == (
        "8e2a3549e464cbc4ff75791893f5fd6e913240649fa0c4c072c44300b97f5388"
    )
    assert resume["machine_spans"]["thread_resume_primitive"]["sha256"] == (
        "5f3f84ca7f0b20a20b09245a54ccf5c9a54ace709f47225f6e7dfb388d914007"
    )


def test_worker_pacing_is_sleep_ex_10ms_alertable_without_100hz_promotion() -> None:
    payload = _load(EVIDENCE)
    pacing = payload["worker_pacing"]
    promotion = payload["promotion"]

    assert pacing["worker"] == "FUN_00662880"
    assert pacing["priority_refresh_is_wait"] is False
    assert pacing["flag_probe_is_wait"] is False
    assert pacing["sleep_wrapper"] == "FUN_00649780"
    assert pacing["sleep_api"] == "SleepEx"
    assert pacing["requested_milliseconds"] == 10
    assert pacing["alertable"] is True
    assert pacing["loop_rechecks_stop_byte_after_sleep"] is True
    assert pacing["machine_spans"]["worker_sleep_and_loop_recheck"]["sha256"] == (
        "c125fb1ba1722ebec13faa1709a7f892f003762bd1e5375c4240565bbe804e63"
    )
    assert pacing["machine_spans"]["sleep_wrapper"]["sha256"] == (
        "260451a7ed8644869aebf1085cde645cf66e9be0397021c69457405e77d760a5"
    )

    assert promotion["worker_requested_alertable_sleep_proven"] is True
    assert promotion["requested_sleep_milliseconds"] == 10
    assert promotion["exact_100hz_cadence_proven"] is False
    assert promotion["render_frame_cadence_proven"] is False
    assert promotion["one_worker_iteration_per_render_frame_proven"] is False
    assert promotion["manager_scheduler_cadence_equals_controller_loop_proven"] is False


def test_pacing_contract_joins_controller_owner_without_replacing_manager_scheduler() -> None:
    payload = _load(EVIDENCE)
    owner = _load(OWNER)

    assert payload["joins"]["controller_owner_contract"] == (
        "SHIFT.Process1PhysicsManagerControllerOwner/1"
    )
    assert owner["format"] == "SHIFT.Process1PhysicsManagerControllerOwner/1"
    assert owner["ready"] is True
    assert payload["joins"]["controller_name"] == owner["controller_registration"]["controller_name"]
    assert payload["joins"]["controller_worker"] == owner["controller_worker"]["worker_target"]
    assert owner["manager_scheduler"]["may_dispatch_multiple_updates_per_invocation"] is True


def test_documentation_keeps_requested_sleep_separate_from_physics_frequency() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "SleepEx(10, TRUE)" in text
    assert "does **not** promote the worker to an exact 100 Hz clock" in text
    assert "does **not** prove" in text
    assert "one Physics Manager update per worker iteration" in text
    assert "independent timing and" in text
    assert "Physics Manager timing configuration" in text
