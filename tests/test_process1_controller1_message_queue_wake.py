from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_message_queue_wake.json"
PACING = ROOT / "evidence/process1_controller1_alertable_pacing.json"
CADENCE_JOIN = ROOT / "evidence/process1_controller1_retail_cadence_join.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_MESSAGE_QUEUE_WAKE.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_message_queue_wake_contract_joins_current_process1_chain() -> None:
    evidence = _load(EVIDENCE)
    pacing = _load(PACING)
    join = _load(CADENCE_JOIN)

    assert evidence["format"] == "SHIFT.Process1Controller1MessageQueueWake/1"
    assert evidence["ready"] is True
    assert evidence["source"]["authority"] == "PC retail 1.02"
    assert evidence["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert evidence["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert evidence["joins"]["controller_pacing_contract"] == pacing["format"]
    assert evidence["joins"]["retail_cadence_join_contract"] == join["format"]
    assert evidence["joins"]["controller_name"] == pacing["joins"]["controller_name"]
    assert evidence["joins"]["worker"] == pacing["joins"]["controller_worker"] == "FUN_00662880"


def test_queue_initialization_preserves_mode_uncertainty() -> None:
    payload = _load(EVIDENCE)
    queue = payload["thread_queue_initialization"]

    assert queue["thread_entry"] == "FUN_00649b10"
    assert queue["queue_initializer"] == "FUN_0064ff40"
    assert queue["queue_mode_expression"] == "controller+0x50 ? 3 : 1"
    assert queue["mode_1_event_bit_set"] is False
    assert queue["mode_3_event_bit_set"] is True
    assert queue["event_bit_mask"] == "0x8"
    assert queue["event_create_helper"] == "FUN_0064f570"
    assert queue["event_name"] == "MsgQueue Event"
    assert queue["controller1_exact_queue_mode_proven"] is False
    assert queue["machine_span"]["sha256"] == (
        "9b66d228cfb0b8bf6d19550ce14a2f1bfe3d7863d34a0394c6a27a61fde78cdd"
    )
    assert queue["queue_mode_event_span"]["sha256"] == (
        "c84fb0171f3fbe17c61d04f24dbd98b55703728700c89909efaa010df2943657"
    )


def test_enqueue_event_is_not_promoted_to_worker_wake() -> None:
    payload = _load(EVIDENCE)
    enqueue = payload["message_enqueue"]
    order = payload["message_dequeue_and_worker_order"]
    wake = payload["wake_adjudication"]

    assert enqueue["controller_enqueue"] == "FUN_00662ee0"
    assert enqueue["queue_enqueue"] == "FUN_00650350"
    assert enqueue["conditional_event_signal"] == "FUN_0064f530"
    assert enqueue["event_signal_api"] == "SetEvent"
    assert enqueue["signals_only_when_queue_event_bit_0x8_set"] is True
    assert enqueue["machine_spans"]["controller_enqueue_wrapper"]["sha256"] == (
        "834a112d58d05fe2735c9e81203f83631c8909dcebac7330ba878363b279ebc9"
    )
    assert enqueue["machine_spans"]["queue_enqueue_and_conditional_signal"]["sha256"] == (
        "d39d7703a15729b257e63364d3bee55caec7fbdb4d326143dfae62182ba87725"
    )
    assert enqueue["machine_spans"]["set_event_wrapper"]["sha256"] == (
        "c598b75ecfe1675dea489a36329101a462517bf1fc22661fe1b861b81e40187a"
    )

    assert order["thread_dequeue_wrapper"] == "FUN_006550a0"
    assert order["queue_dequeue"] == "FUN_006500e0"
    assert order["queue_event_wait_helper"] == "FUN_0064f540"
    assert order["worker_calls_queue_event_wait_helper"] is False
    assert order["machine_spans"]["queue_dequeue"]["sha256"] == (
        "ed8e406e5d699e39d9fd4c8d79a41f23ce951800e9fab8cd6d712f02e6f3eb6c"
    )
    assert order["machine_spans"]["worker_poll_dispatch_sleep"]["sha256"] == (
        "2f25250574c39efb47a552b394057ba50f3f9289977527a7e4c7e5303ec69805"
    )

    assert wake["message_queue_is_polled_by_controller1_worker_proven"] is True
    assert wake["queue_event_is_waited_by_controller1_worker_proven"] is False
    assert wake["message_enqueue_wakes_controller1_worker_proven"] is False
    assert wake["message_arrival_interrupts_sleep_ex_proven"] is False
    assert wake["render_or_present_message_producer_join_proven"] is False


def test_apc_surface_stays_fail_closed() -> None:
    payload = _load(EVIDENCE)
    apc = payload["apc_surface"]
    promotion = payload["promotion"]

    assert apc["queue_user_apc_source_token_hits"] == 0
    assert apc["absence_of_queue_user_apc_token_proves_no_apc"] is False
    assert apc["read_file_ex_present"] is True
    assert apc["write_file_ex_present"] is True
    assert apc["controller1_owns_these_async_io_operations_proven"] is False
    assert apc["set_waitable_timer_present"] is True
    assert apc["observed_fmod_waitable_timer_completion_routine_is_null"] is True
    assert apc["controller1_apc_producer_proven"] is False

    assert promotion["controller1_message_queue_polling_proven"] is True
    assert promotion["conditional_message_queue_event_signal_proven"] is True
    assert promotion["controller1_worker_waits_on_message_event_proven"] is False
    assert promotion["message_enqueue_is_controller1_wake_source_proven"] is False
    assert promotion["controller1_apc_wake_source_proven"] is False
    assert promotion["render_phase_lock_proven"] is False


def test_documentation_does_not_collapse_queue_event_into_alertable_wake() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "SetEvent" in text
    assert "does not wait on that event" in text
    assert "SleepEx(10, TRUE)" in text
    assert "does not prove an APC path" in text
    assert "ReadFileEx" in text and "WriteFileEx" in text
    assert "render/presentation" in text
