from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_fun006333f0_layout_exclusion.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_fun006333f0_layout_exclusion.py"
DOC = ROOT / "docs/PROCESS_1_FUN006333F0_LAYOUT_EXCLUSION.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_fun006333f0_layout", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fun006333f0_cannot_alias_controller1_queue_layout() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Fun006333f0LayoutExclusion/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["upstream_contract"] == "SHIFT.Process1Controller1BManagerQueueWake/1"
    assert payload["source"]["xbox_recomp_required"] is False
    assert payload["controller1_queue"]["allocation_size"] == "0xe0"
    assert payload["controller1_queue"]["thread_state_slot"] == "ThreadState+0x5c"
    assert payload["controller1_queue"]["controller_slot"] == "Controller+0x08"
    assert payload["fun_006333f0"]["required_object_field_offset"] == "+0x250"
    assert payload["layout_exclusion"]["required_offset_exceeds_controller_queue_allocation"] is True
    assert payload["layout_exclusion"]["controller1_queue_alias_ruled_out"] is True
    assert payload["adjudication"]["source_visible_generic_queue_pointer_alias_frontier_closed"] is True
    assert payload["adjudication"]["indirect_or_native_apc_injection_ruled_out"] is False
    assert payload["adjudication"]["render_or_present_phase_lock_proven"] is False


def test_analyzer_pins_layout_size_mismatch() -> None:
    module = load_analyzer()
    assert module.CONTROLLER_QUEUE_ALLOCATION_SIZE == 0xE0
    assert module.FUN006333_REQUIRED_FIELD_OFFSET == 0x250
    assert module.FUN006333_REQUIRED_FIELD_OFFSET >= module.CONTROLLER_QUEUE_ALLOCATION_SIZE
    assert module.UPSTREAM_CONTRACT == "SHIFT.Process1Controller1BManagerQueueWake/1"


def test_documentation_closes_only_source_visible_alias_frontier() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "source-visible generic queue-pointer alias" in text
    assert "standalone allocation of `0xE0` bytes" in text
    assert "`+0x250`" in text
    assert "structurally not the recovered Controller #1 queue object" in text
    assert "does **not** prove" in text
    assert "native APC" in text
    assert "render/presentation phase-lock" in text
    assert "not required for this positive claim" in text
