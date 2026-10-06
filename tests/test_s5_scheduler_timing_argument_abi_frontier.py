import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "s5_scheduler_timing_argument_abi_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_timing_argument_abi_frontier_is_positive_but_cadence_fail_closed():
    payload = _load()
    assert payload["format"] == "SHIFT.RetailSchedulerTimingArgumentABIFrontier/1"
    assert payload["status"] == "positive"
    assert payload["gates_changed"] == []
    assert payload["adjudication"]["retail_cadence_admitted"] is False


def test_exact_upper_caller_abi_has_no_formal_stack_timing_parameter():
    payload = _load()
    upper = payload["provenance"]["functions_export"]["FUN_007155e9"]
    assert upper["address"] == "0x007155e9"
    assert upper["calling_convention"] == "__fastcall"
    assert upper["signature"] == "uint FUN_007155e9(LONG * param_1)"
    assert upper["parameters"] == [
        {"name": "param_1", "type": "LONG *", "storage": "ECX:4"}
    ]
    assert payload["adjudication"]["FUN_007155e9_has_formal_stack_timing_argument"] is False


def test_exact_callee_abi_and_direct_callsite_are_frozen():
    payload = _load()
    callee = payload["provenance"]["functions_export"]["FUN_00715380"]
    assert callee["address"] == "0x00715380"
    assert callee["calling_convention"] == "__thiscall"
    assert callee["parameters"][1] == {
        "name": "param_1",
        "type": "float",
        "storage": "Stack[0x4]:4",
    }
    assert payload["provenance"]["callgraph_export"]["edge"] == {
        "from": "FUN_007155e9",
        "instruction": "0x00715602",
        "to": "FUN_00715380",
        "indirect": False,
    }


def test_frontier_does_not_promote_machine_value_source_or_units():
    adjudication = _load()["adjudication"]
    assert adjudication["upstream_formal_timing_argument_proven"] is False
    assert adjudication["timing_value_exact_machine_producer_proven"] is False
    assert adjudication["timing_units_proven"] is False
