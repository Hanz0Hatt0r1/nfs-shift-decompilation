from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_queue_object_identity.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_controller1_queue_object_identity.py"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_QUEUE_OBJECT_IDENTITY.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_queue_identity", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_queue_object_identity_evidence_keeps_generic_aliases_open() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Controller1QueueObjectIdentity/1"
    assert payload["ready"] is True
    assert payload["generic_enqueue"]["function"] == "FUN_00650350"
    assert payload["generic_enqueue"]["direct_caller_count"] == 8
    assert payload["explicit_controller_queue_identity"]["queue_field"] == "+0x5c"
    assert payload["explicit_controller_queue_identity"]["callers"] == ["FUN_00649b10", "FUN_00662ee0"]
    assert payload["explicit_controller_queue_identity"]["external_wrapper_only_direct_caller"] == "FUN_006499e8"
    assert payload["adjudication"]["thread_entry_self_seed_is_external_wake_source"] is False
    assert payload["adjudication"]["direct_non_teardown_external_controller_enqueue_producer_proven"] is False
    assert payload["adjudication"]["render_or_present_direct_controller_queue_producer_proven"] is False
    assert payload["generic_alias_frontier"]["generic_pointer_alias_to_controller1_ruled_out"] is False


def test_queue_object_analyzer_pins_direct_caller_surface() -> None:
    module = load_analyzer()
    assert module.EXPECTED_DIRECT_CALLERS == [
        "FUN_0057e5b0",
        "FUN_0057e820",
        "FUN_006333f0",
        "FUN_00649b10",
        "FUN_006503d0",
        "FUN_00655220",
        "FUN_00662ee0",
        "FUN_006880c0",
    ]
    assert module.EXPLICIT_CONTROLLER_QUEUE_CALLERS == ["FUN_00649b10", "FUN_00662ee0"]
    assert module.SPANS["controller_enqueue_wrapper"] == (0x00662EE0, 0x00662F16)
    assert module.SPANS["generic_queue_enqueue"] == (0x00650350, 0x00650390)


def test_documentation_rejects_shared_api_name_aliasing() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "cannot be attributed to Controller #1 by API name alone" in text
    assert "lifecycle shutdown" in text
    assert "companion BManager queue-wake proof" in text
    assert "does not establish an APC wake source" in text
