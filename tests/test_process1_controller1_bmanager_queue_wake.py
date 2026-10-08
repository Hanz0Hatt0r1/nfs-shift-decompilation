from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_bmanager_queue_wake.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_controller1_bmanager_queue_wake.py"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_BMANAGER_QUEUE_WAKE.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_bmanager_queue_wake", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bmanager_queue_wake_evidence_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Controller1BManagerQueueWake/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["xbox_recomp_required"] is False
    assert payload["controller1"]["manager_registry"] == "BManager+0x4c8"
    assert payload["controller1"]["queue_pointer"] == "Controller+0x08"
    assert payload["producer"]["messages"] == [3, 4, 5, 6, 7]
    assert payload["producer"]["controller1_target_by_registry_identity"] is True
    assert payload["producer"]["shared_api_name_only_inference_used"] is False
    wake = payload["queue_wakeup"]
    assert wake["queue_init_argument"] == 1
    assert wake["queue_flags_after_init"] == 7
    assert wake["msgqueue_event_bit"] == 8
    assert wake["msgqueue_event_enabled"] is False
    assert wake["normal_enqueue_calls_setevent"] is False
    assert wake["enqueue_contains_apc_primitive"] is False
    adjudication = payload["adjudication"]
    assert adjudication["controller1_generic_queue_producer_join_proven"] is True
    assert adjudication["queue_enqueue_is_apc_source"] is False
    assert adjudication["queue_enqueue_interrupts_sleep_ex_via_msgqueue_event"] is False
    assert adjudication["controller1_alertable_sleep_has_concrete_recovered_apc_wake_source_proven"] is False
    assert adjudication["indirect_or_native_apc_injection_ruled_out"] is False
    assert adjudication["render_or_present_phase_lock_proven"] is False


def test_analyzer_pins_pc_machine_surface() -> None:
    module = load_analyzer()
    assert module.MESSAGES == (3, 4, 5, 6, 7)
    assert module.SOURCE_SHA256 == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert module.EXE_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.SPANS["broadcast_registry_thunk"][:2] == (0x00408D7D, 0x00408D88)
    assert module.SPANS["broadcast_loop"][:2] == (0x0065BD1C, 0x0065BD6A)
    assert module.SPANS["controller_send"][:2] == (0x00655220, 0x00655273)
    assert module.SPANS["queue_enqueue"][:2] == (0x00650350, 0x00650392)


def test_documentation_keeps_queue_wake_distinct_from_apc_wake() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "BManager+0x4c8" in text
    assert "message IDs `3`, `4`, `5`, `6`, and `7`" in text
    assert "final queue flags `7`" in text
    assert "`MsgQueue Event` bit `8` is absent" in text
    assert "does not provide a concrete APC source" in text
    assert "Indirect/native APC injection remains unresolved" in text
