from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_fun006880c0_queue_provenance.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_fun006880c0_queue_provenance.py"
DOC = ROOT / "docs/PROCESS_1_FUN006880C0_QUEUE_PROVENANCE.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_fun006880c0_provenance", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fun006880c0_queue_pointer_is_caller_supplied() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Fun006880c0QueueProvenance/1"
    assert payload["ready"] is True
    assert payload["dataflow"]["single_source_visible_caller"] == "FUN_0066bab0"
    assert payload["dataflow"]["queue_pointer_expression"] == "embedded_state+0x8"
    assert payload["dataflow"]["initializer"] == "FUN_0066bb50"
    assert payload["dataflow"]["initializer_assignment"] == "embedded_state+0x8 = param_4"
    assert payload["dataflow"]["fixed_global_owner_proven"] is False
    assert payload["dataflow"]["caller_supplied_operation_object"] is True
    assert payload["adjudication"]["fun_006880c0_fixed_queue_owner_claim_rejected"] is True
    assert payload["adjudication"]["fun_006880c0_controller1_alias_ruled_out"] is False
    assert payload["adjudication"]["fun_006333f0_controller1_alias_ruled_out"] is False
    assert payload["adjudication"]["indirect_or_native_apc_injection_ruled_out"] is False
    assert payload["adjudication"]["render_or_present_phase_lock_proven"] is False


def test_fun006880c0_analyzer_locks_machine_spans() -> None:
    module = load_analyzer()
    assert module.SPANS["caller_queue_load_and_call"][:2] == (0x0066BAE7, 0x0066BAF5)
    assert module.SPANS["initializer_param4_store"][:2] == (0x0066BB59, 0x0066BB6A)
    assert module.SPANS["thin_wrapper"][:2] == (0x006880C0, 0x006880DB)


def test_fun006880c0_documentation_rejects_fixed_owner_shortcut() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "does **not** give it one fixed queue owner" in text
    assert "operation-specific producer chain" in text
    assert "does **not** rule `FUN_006880c0` out" in text
    assert "`FUN_006333f0` remains separately unresolved" in text
    assert "all claims in this artifact are PC-backed" in text
